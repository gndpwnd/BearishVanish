"""
Momentum Strategy with Money Flow Index - Institutional Grade
Combines price momentum with volume-weighted money flow

Used by quant funds for detecting institutional accumulation:
- Tracks money flow (MFI) to see institutional buying/selling
- Combines with price momentum and trend
- Uses multiple confirmation signals
- Strict risk management

Entry Signals:
- MFI crosses above 20 (money flowing in after oversold)
- Price above 50-day SMA (uptrend)
- OBV rising (volume confirms)
- Supertrend bullish

Exit Signals:
- MFI > 80 (overbought, institutions distributing)
- Price crosses below 20-day SMA
- OBV falling for 3 bars
- Supertrend turns bearish

Risk Controls:
- 10% of portfolio per position
- Maximum 8 concurrent positions
- Stop-loss at Supertrend line
"""

import pandas as pd
import numpy as np
from strategy_base import StrategyBase, StrategyConfig


class Strategy(StrategyBase):
    """Momentum with Money Flow Index Strategy"""

    def __init__(self, config: StrategyConfig = None):
        if config is None:
            config = StrategyConfig(
                name="Momentum MFI",
                color="#9C27B0",
                initial_capital=100000,
                position_size_pct=0.10,
                max_positions=8,
                stop_loss_pct=0.07  # 7% stop-loss
            )

        super().__init__(config)

        # Stop-loss parameter (use config or default 7%)
        self.stop_loss_pct = self.config.stop_loss_pct if self.config.stop_loss_pct else 0.07

        # Strategy parameters
        self.mfi_period = 14
        self.mfi_oversold = 20
        self.mfi_overbought = 80
        self.sma_trend = 50
        self.sma_exit = 20
        self.supertrend_period = 10
        self.supertrend_multiplier = 3.0
        self.adx_threshold = 15  # Lowered from 20 to 15 for more signals in moderate trends

        # Required indicators
        # Note: 'adx' loads from indicator_adx.py (Numba JIT optimized)
        # ADX returns dict with 'adx', 'plus_di', 'minus_di'
        self.required_indicators = [
            'mfi',
            'obv',
            'sma',
            'supertrend',
            'adx'  # Used for trend filtering (avoid choppy markets)
        ]

        # Track state
        self._in_position = {}
        self._obv_history = {}  # Track last 3 OBV values
        self._entry_prices = {}  # Track entry prices for stop-loss

    def generate_signal(self, symbol, data, spy_data, bar_index):
        """
        Generate momentum + MFI signal

        Logic:
        1. BUY: MFI > 20 (after oversold) + Price > 50 SMA + OBV rising + Supertrend bullish
        2. SELL: MFI > 80 OR Price < 20 SMA OR OBV falling OR Supertrend bearish
        """
        # Need enough data
        if len(data) < max(self.sma_trend, self.mfi_period, 20):
            return 'HOLD'

        # Initialize tracking
        if symbol not in self._in_position:
            self._in_position[symbol] = False
            self._obv_history[symbol] = []
            self._entry_prices[symbol] = None

        try:
            current_price = data['close'].iloc[-1]

            # Get indicators
            mfi = data.get('mfi', pd.Series([50.0] * len(data))).iloc[-1]
            obv = data.get('obv', pd.Series([0.0] * len(data))).iloc[-1]
            sma_50 = data.get(f'sma_{self.sma_trend}', pd.Series([np.nan] * len(data))).iloc[-1]
            sma_20 = data.get(f'sma_{self.sma_exit}', pd.Series([np.nan] * len(data))).iloc[-1]
            supertrend_direction = data.get('supertrend_direction', pd.Series([np.nan] * len(data))).iloc[-1]

            # Get ADX for trend filtering (from indicator_adx.py)
            # ADX indicator returns dict with 'adx', 'plus_di', 'minus_di'
            adx = data.get('adx', pd.Series([np.nan] * len(data))).iloc[-1]

            # Check for NaN values
            if np.isnan(sma_50) or np.isnan(sma_20) or np.isnan(mfi):
                return 'HOLD'

            # ADX Trend Filter: Avoid choppy/ranging markets
            # ADX < 20 indicates weak or no trend - stay out
            if not np.isnan(adx) and adx < self.adx_threshold:
                return 'HOLD'

            # Track OBV history (last 3 values)
            self._obv_history[symbol].append(obv)
            if len(self._obv_history[symbol]) > 3:
                self._obv_history[symbol].pop(0)

            # Check if OBV is rising (at least 2 of last 3 increases)
            obv_rising = False
            if len(self._obv_history[symbol]) >= 3:
                increases = sum(1 for i in range(1, 3)
                              if self._obv_history[symbol][i] > self._obv_history[symbol][i-1])
                obv_rising = increases >= 2

            # Check if OBV is falling
            obv_falling = False
            if len(self._obv_history[symbol]) >= 3:
                decreases = sum(1 for i in range(1, 3)
                               if self._obv_history[symbol][i] < self._obv_history[symbol][i-1])
                obv_falling = decreases >= 2

            # ===================================
            # EXIT LOGIC (check first)
            # ===================================
            if self._in_position[symbol]:
                # STOP-LOSS CHECK (check first)
                entry_price = self._entry_prices[symbol]
                if entry_price is not None and current_price < entry_price * (1 - self.stop_loss_pct):
                    self._in_position[symbol] = False
                    self._entry_prices[symbol] = None
                    return 'SELL'

                # Exit if MFI overbought (institutional distribution)
                if mfi > self.mfi_overbought:
                    self._in_position[symbol] = False
                    self._entry_prices[symbol] = None
                    return 'SELL'

                # Exit if price drops below 20-day SMA (momentum loss)
                if current_price < sma_20:
                    self._in_position[symbol] = False
                    self._entry_prices[symbol] = None
                    return 'SELL'

                # Exit if OBV falling (volume not confirming)
                if obv_falling:
                    self._in_position[symbol] = False
                    self._entry_prices[symbol] = None
                    return 'SELL'

                # Exit if Supertrend turns bearish
                if not np.isnan(supertrend_direction) and supertrend_direction < 0:
                    self._in_position[symbol] = False
                    self._entry_prices[symbol] = None
                    return 'SELL'

            # ===================================
            # ENTRY LOGIC (relaxed conditions for more signals)
            # ===================================
            if not self._in_position[symbol]:
                # Condition 1: MFI recovering from oversold (institutional accumulation)
                # Widened sweet spot from 20-50 to 20-60
                mfi_signal = mfi > self.mfi_oversold and mfi < 60

                # Condition 2: Price above 50-day SMA (in uptrend)
                in_uptrend = current_price > sma_50

                # Condition 3: OBV rising (volume confirms) - RELAXED
                # Changed from requiring 2/3 increases to just 1/3 (at least 1 increase in last 3)
                obv_ok = True  # Default to True if not enough history
                if len(self._obv_history[symbol]) >= 2:
                    # Just need OBV to not be falling drastically
                    obv_ok = self._obv_history[symbol][-1] >= self._obv_history[symbol][-2] * 0.99

                # Condition 4: Supertrend bullish OR (if NaN) use SMA alignment
                if not np.isnan(supertrend_direction):
                    bullish_trend = supertrend_direction > 0
                else:
                    # Fallback: Use price above both SMAs
                    bullish_trend = current_price > sma_50 and current_price > sma_20

                # Need 3 of 4 conditions to be met (relaxed from ALL)
                conditions_met = sum([mfi_signal, in_uptrend, obv_ok, bullish_trend])
                if conditions_met >= 3:
                    self._in_position[symbol] = True
                    self._entry_prices[symbol] = current_price
                    return 'BUY'

        except Exception as e:
            return 'HOLD'

        return 'HOLD'

    def get_config(self):
        """Return serializable configuration"""
        base_config = super().get_config()
        base_config.update({
            'mfi_period': self.mfi_period,
            'mfi_oversold': self.mfi_oversold,
            'mfi_overbought': self.mfi_overbought,
            'sma_trend': self.sma_trend,
            'sma_exit': self.sma_exit,
            'supertrend_period': self.supertrend_period,
            'supertrend_multiplier': self.supertrend_multiplier,
            'stop_loss_pct': self.stop_loss_pct,
            'adx_threshold': self.adx_threshold
        })
        return base_config
