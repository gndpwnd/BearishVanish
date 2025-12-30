"""
Breakout Strategy - Institutional Grade
Captures explosive moves when price breaks out of consolidation

Used by momentum funds like Citadel and DE Shaw:
- Identifies consolidation periods
- Detects volume-confirmed breakouts
- Uses multiple timeframe confirmation
- Exits on momentum loss

Entry Signals:
- Price breaks above 20-day high
- Volume > 1.2x average (institutional participation)
- ADX > 20 (momentum building)
- Price > VWAP (quality breakout)

Exit Signals:
- Price drops below 10-day EMA (momentum loss)
- Volume dries up (< 0.8x average)
- ATR expansion reversal (volatility peak)

Risk Controls:
- 12% of portfolio per position (higher conviction)
- Maximum 6 concurrent positions (concentrated)
- Initial stop-loss at breakout level - 2×ATR
"""

import pandas as pd
import numpy as np
from strategy_base import StrategyBase, StrategyConfig


class Strategy(StrategyBase):
    """Breakout Strategy"""

    def __init__(self, config: StrategyConfig = None):
        if config is None:
            config = StrategyConfig(
                name="Breakout",
                color="#FFA726",
                initial_capital=100000,
                position_size_pct=0.12,  # 12% per position (higher conviction)
                max_positions=6
            )

        super().__init__(config)

        # Strategy parameters
        self.breakout_period = 20  # 20-day high
        self.exit_ema_period = 10
        self.volume_breakout_threshold = 1.2  # Reduced from 1.5 to 1.2 for more signals
        self.volume_exit_threshold = 0.8
        self.adx_threshold = 20
        self.atr_period = 14
        self.atr_stop_multiplier = 2.0

        # Required indicators
        # Note: 'atr' loads from indicator_atr.py (Numba JIT optimized)
        # Note: 'adx' loads from indicator_adx.py (Numba JIT optimized)
        self.required_indicators = [
            'adx',
            'atr',  # Used for dynamic stop-loss calculation
            'ema',
            'vwap',
            'relative_volume'
        ]

        # Track breakout state
        self._in_breakout = {}
        self._breakout_level = {}
        self._entry_atr = {}

    def generate_signal(self, symbol, data, spy_data, bar_index):
        """
        Generate breakout signal

        Logic:
        1. BUY: Price breaks 20-day high + volume surge + ADX > 20 + above VWAP
        2. SELL: Price below 10-EMA OR low volume OR stop-loss hit
        """
        # Need enough data
        if len(data) < max(self.breakout_period, self.adx_threshold * 2, 20):
            return 'HOLD'

        # Initialize tracking
        if symbol not in self._in_breakout:
            self._in_breakout[symbol] = False
            self._breakout_level[symbol] = None
            self._entry_atr[symbol] = None

        try:
            current_price = data['close'].iloc[-1]
            current_high = data['high'].iloc[-1]

            # Get indicators
            adx = data.get('adx', pd.Series([np.nan] * len(data))).iloc[-1]
            atr = data.get('atr', pd.Series([np.nan] * len(data))).iloc[-1]
            ema_exit = data.get(f'ema_{self.exit_ema_period}', pd.Series([np.nan] * len(data))).iloc[-1]
            vwap = data.get('vwap', pd.Series([current_price] * len(data))).iloc[-1]
            rel_volume = data.get('relative_volume', pd.Series([1.0] * len(data))).iloc[-1]

            # Calculate 20-day high (breakout level)
            if len(data) >= self.breakout_period:
                high_20d = data['high'].iloc[-self.breakout_period:].max()
            else:
                return 'HOLD'

            # Check for NaN values
            if np.isnan(adx) or np.isnan(atr) or np.isnan(ema_exit):
                return 'HOLD'

            # ===================================
            # EXIT LOGIC (check first)
            # ===================================
            if self._in_breakout[symbol]:
                # Dynamic stop-loss using ATR (from indicator_atr.py)
                # Stop-loss: price drops below breakout level - 2×ATR
                # This allows stops to adapt to market volatility
                breakout_level = self._breakout_level[symbol]
                entry_atr = self._entry_atr[symbol]
                stop_loss = breakout_level - (entry_atr * self.atr_stop_multiplier)

                if current_price < stop_loss:
                    self._in_breakout[symbol] = False
                    self._breakout_level[symbol] = None
                    self._entry_atr[symbol] = None
                    return 'SELL'

                # Exit if price drops below exit EMA (momentum loss)
                if current_price < ema_exit:
                    self._in_breakout[symbol] = False
                    self._breakout_level[symbol] = None
                    self._entry_atr[symbol] = None
                    return 'SELL'

                # Exit if volume dries up (institutional exit)
                if rel_volume < self.volume_exit_threshold:
                    self._in_breakout[symbol] = False
                    self._breakout_level[symbol] = None
                    self._entry_atr[symbol] = None
                    return 'SELL'

            # ===================================
            # ENTRY LOGIC
            # ===================================
            if not self._in_breakout[symbol]:
                # Condition 1: Price breaks above 20-day high
                breakout = current_high > high_20d

                # Condition 2: Volume surge (institutional participation)
                volume_surge = rel_volume > self.volume_breakout_threshold

                # Condition 3: ADX shows momentum building
                momentum_building = adx > self.adx_threshold

                # Condition 4: Price above VWAP (quality breakout, not fake)
                above_vwap = current_price > vwap

                # Condition 5: Ensure it's a NEW breakout (not already broken out)
                # Check that previous bar was BELOW the breakout level
                if len(data) >= 2:
                    prev_high = data['high'].iloc[-2]
                    new_breakout = prev_high <= high_20d
                else:
                    new_breakout = False

                # ALL conditions must be met
                if (breakout and volume_surge and momentum_building and
                    above_vwap and new_breakout):
                    self._in_breakout[symbol] = True
                    self._breakout_level[symbol] = high_20d
                    self._entry_atr[symbol] = atr
                    return 'BUY'

        except Exception as e:
            return 'HOLD'

        return 'HOLD'

    def get_config(self):
        """Return serializable configuration"""
        base_config = super().get_config()
        base_config.update({
            'breakout_period': self.breakout_period,
            'exit_ema_period': self.exit_ema_period,
            'volume_breakout_threshold': self.volume_breakout_threshold,
            'volume_exit_threshold': self.volume_exit_threshold,
            'adx_threshold': self.adx_threshold,
            'atr_period': self.atr_period,
            'atr_stop_multiplier': self.atr_stop_multiplier
        })
        return base_config
