"""
Conservative Income Strategy
Designed for consistent monthly gains with tight risk controls

REALISTIC GOALS:
- Target: 0.5-1.0% monthly (6-12% annually)
- Max drawdown: <15%
- Win rate: >55%
- Smooth equity curve

APPROACH:
- Small, frequent profits
- Quick exits (3-5 day holds)
- Tight stop-losses (3%)
- Only trade in favorable conditions
- Conservative position sizing (5%)

This is NOT a "get rich quick" strategy.
This is a "don't lose money and grind slowly higher" strategy.
"""

import pandas as pd
import numpy as np
from strategy_base import StrategyBase, StrategyConfig


class Strategy(StrategyBase):
    """Conservative Income Strategy"""

    def __init__(self, config: StrategyConfig = None):
        if config is None:
            config = StrategyConfig(
                name="Conservative Income",
                color="#27AE60",  # Green for conservative/safe
                initial_capital=100000,
                position_size_pct=0.05,  # Only 5% per position (conservative)
                max_positions=12  # More positions = diversification
            )

        super().__init__(config)

        # RELAXED thresholds for more signals
        self.rsi_oversold = 35  # Was 30, now 35 (easier to trigger)
        self.rsi_overbought = 65  # Was 70, now 65 (exit earlier)
        self.rsi_period = 14

        # Bollinger Bands
        self.bb_period = 20
        self.bb_std = 2.0

        # Volume (RELAXED)
        self.volume_threshold = 1.1  # Was 1.5, now 1.1 (easier to meet)

        # TIGHT risk management
        self.stop_loss_pct = 0.03  # 3% stop-loss (TIGHT!)
        self.profit_target_pct = 0.06  # 6% profit target (2:1 risk/reward)
        self.max_hold_days = 5  # Exit after 5 days regardless

        # Required indicators
        self.required_indicators = [
            'rsi',
            'bollinger_bands',
            'sma',  # For trend filter
            'relative_volume'
        ]

        # Track positions
        self._entry_prices = {}
        self._entry_dates = {}
        self._in_position = {}

    def generate_signal(self, symbol, data, spy_data, bar_index):
        """
        Generate conservative income signal

        ENTRY (at least ONE of these):
        1. Price near Bollinger Lower + RSI < 35 (oversold bounce)
        2. Price crosses above 20-SMA + RSI 35-50 (momentum entry)

        EXIT (FIRST to trigger):
        1. 6% profit target hit
        2. 3% stop-loss hit
        3. 5 days elapsed
        4. RSI > 65 (take profit)
        """
        # Need enough data
        if len(data) < max(self.bb_period, self.rsi_period, 50):
            return 'HOLD'

        # Initialize tracking
        if symbol not in self._in_position:
            self._in_position[symbol] = False
            self._entry_prices[symbol] = None
            self._entry_dates[symbol] = None

        try:
            current_date = data.index[-1]
            current_price = data['close'].iloc[-1]

            # Get indicators
            rsi = data.get('rsi', pd.Series([50.0] * len(data))).iloc[-1]
            bb_upper = data.get('bollinger_bands_upper', pd.Series([np.nan] * len(data))).iloc[-1]
            bb_middle = data.get('bollinger_bands_middle', pd.Series([np.nan] * len(data))).iloc[-1]
            bb_lower = data.get('bollinger_bands_lower', pd.Series([np.nan] * len(data))).iloc[-1]
            sma_20 = data.get('sma_20', pd.Series([np.nan] * len(data))).iloc[-1]
            sma_50 = data.get('sma_50', pd.Series([np.nan] * len(data))).iloc[-1]
            rel_volume = data.get('relative_volume', pd.Series([1.0] * len(data))).iloc[-1]

            # Check for NaN
            if np.isnan(bb_lower) or np.isnan(sma_20):
                return 'HOLD'

            # ===================================
            # EXIT LOGIC (tight risk management)
            # ===================================
            if self._in_position[symbol]:
                entry_price = self._entry_prices[symbol]
                entry_date = self._entry_dates[symbol]

                # Calculate P&L
                pnl_pct = (current_price - entry_price) / entry_price

                # EXIT 1: Profit target hit (6%)
                if pnl_pct >= self.profit_target_pct:
                    self._in_position[symbol] = False
                    self._entry_prices[symbol] = None
                    self._entry_dates[symbol] = None
                    return 'SELL'  # Take profit!

                # EXIT 2: Stop-loss hit (3%)
                if pnl_pct <= -self.stop_loss_pct:
                    self._in_position[symbol] = False
                    self._entry_prices[symbol] = None
                    self._entry_dates[symbol] = None
                    return 'SELL'  # Cut loss!

                # EXIT 3: Max hold period (5 days)
                if entry_date is not None:
                    holding_days = (current_date - entry_date).days
                    if holding_days >= self.max_hold_days:
                        self._in_position[symbol] = False
                        self._entry_prices[symbol] = None
                        self._entry_dates[symbol] = None
                        return 'SELL'  # Time exit

                # EXIT 4: RSI overbought (take profit early)
                if rsi > self.rsi_overbought and pnl_pct > 0:
                    self._in_position[symbol] = False
                    self._entry_prices[symbol] = None
                    self._entry_dates[symbol] = None
                    return 'SELL'  # Take quick profit

            # ===================================
            # ENTRY LOGIC (multiple conditions, use OR)
            # ===================================
            if not self._in_position[symbol]:
                # Relaxed trend filter: Check if 20-SMA is rising (uptrend without requiring price > sma_50)
                # The old filter (price > sma_50) was contradicting the oversold bounce pattern
                # because when price is at bb_lower, it's usually BELOW sma_50
                if len(data) >= 3:
                    sma_20_prev = data.get('sma_20', pd.Series([np.nan] * len(data))).iloc[-3]
                    sma_rising = not np.isnan(sma_20_prev) and sma_20 > sma_20_prev
                else:
                    sma_rising = True  # Allow entry if not enough data to check

                # ENTRY PATTERN 1: Oversold bounce
                # - Price near/below BB lower
                # - RSI oversold (<35)
                # - Some volume
                price_near_lower = current_price <= bb_lower * 1.01  # Within 1% of lower band
                rsi_oversold = rsi < self.rsi_oversold
                volume_ok = rel_volume > self.volume_threshold

                pattern_1 = price_near_lower and rsi_oversold and volume_ok

                # ENTRY PATTERN 2: Momentum entry
                # - Price crosses above 20-SMA
                # - RSI in sweet spot (35-50)
                # - Some volume
                prev_price = data['close'].iloc[-2]
                prev_sma = data.get('sma_20', pd.Series([np.nan] * len(data))).iloc[-2]

                crosses_above_sma = (prev_price <= prev_sma and current_price > sma_20)
                rsi_sweet_spot = 35 < rsi < 50
                volume_ok_2 = rel_volume > self.volume_threshold

                pattern_2 = crosses_above_sma and rsi_sweet_spot and volume_ok_2

                # Enter if EITHER pattern matches AND trend is favorable
                if (pattern_1 or pattern_2) and sma_rising:
                    self._in_position[symbol] = True
                    self._entry_prices[symbol] = current_price
                    self._entry_dates[symbol] = current_date
                    return 'BUY'

        except Exception as e:
            return 'HOLD'

        return 'HOLD'

    def get_config(self):
        """Return serializable configuration"""
        base_config = super().get_config()
        base_config.update({
            'rsi_period': self.rsi_period,
            'rsi_oversold': self.rsi_oversold,
            'rsi_overbought': self.rsi_overbought,
            'bb_period': self.bb_period,
            'bb_std': self.bb_std,
            'volume_threshold': self.volume_threshold,
            'stop_loss_pct': self.stop_loss_pct,
            'profit_target_pct': self.profit_target_pct,
            'max_hold_days': self.max_hold_days
        })
        return base_config
