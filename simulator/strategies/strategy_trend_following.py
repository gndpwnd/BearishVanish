"""
Trend Following Strategy - Institutional Grade
Rides strong trends using ADX + Supertrend + moving averages

Used by CTAs (Commodity Trading Advisors) like Man Group and Winton:
- Identifies strong trends with ADX
- Uses Supertrend for entry/exit timing
- Confirms with moving average alignment
- Exits on trend reversal or weakening

Entry Signals:
- ADX > 25 (strong trend)
- Supertrend flips to bullish
- EMA(20) > EMA(50) (trend confirmation)
- Price above VWAP

Exit Signals:
- Supertrend flips to bearish
- ADX < 20 (trend weakening)
- Price crosses below EMA(20)

Risk Controls:
- 10% of portfolio per position
- Maximum 8 concurrent positions
- Trailing stop using Supertrend line
"""

import pandas as pd
import numpy as np
from strategy_base import StrategyBase, StrategyConfig


class Strategy(StrategyBase):
    """Trend Following Strategy"""

    def __init__(self, config: StrategyConfig = None):
        if config is None:
            config = StrategyConfig(
                name="Trend Following",
                color="#4ECDC4",
                initial_capital=100000,
                position_size_pct=0.10,  # 10% per position
                max_positions=8
            )

        super().__init__(config)

        # Strategy parameters
        self.adx_period = 14
        self.adx_strong_trend = 25
        self.adx_weak_trend = 20
        self.supertrend_period = 10
        self.supertrend_multiplier = 3.0
        self.ema_fast = 20
        self.ema_slow = 50

        # Required indicators
        self.required_indicators = [
            'adx',
            'supertrend',
            'ema',
            'vwap'
        ]

        # Track position state
        self._in_trend = {}

    def generate_signal(self, symbol, data, spy_data, bar_index):
        """
        Generate trend following signal

        Logic:
        1. BUY: ADX strong + Supertrend bullish + EMAs aligned + above VWAP
        2. SELL: Supertrend bearish OR ADX weak OR price below fast EMA
        """
        # Need enough data
        if len(data) < max(self.adx_period * 2, self.ema_slow, 20):
            return 'HOLD'

        # Initialize tracking
        if symbol not in self._in_trend:
            self._in_trend[symbol] = False

        try:
            current_price = data['close'].iloc[-1]

            # Get indicators
            # ADX returns (adx, +DI, -DI)
            adx = data.get('adx', pd.Series([np.nan] * len(data))).iloc[-1]
            plus_di = data.get('adx_plus_di', pd.Series([np.nan] * len(data))).iloc[-1]
            minus_di = data.get('adx_minus_di', pd.Series([np.nan] * len(data))).iloc[-1]

            # Supertrend returns (supertrend, direction)
            supertrend_value = data.get('supertrend', pd.Series([np.nan] * len(data))).iloc[-1]
            supertrend_direction = data.get('supertrend_direction', pd.Series([np.nan] * len(data))).iloc[-1]

            # EMAs
            ema_fast = data.get(f'ema_{self.ema_fast}', pd.Series([np.nan] * len(data))).iloc[-1]
            ema_slow = data.get(f'ema_{self.ema_slow}', pd.Series([np.nan] * len(data))).iloc[-1]

            # VWAP
            vwap = data.get('vwap', pd.Series([current_price] * len(data))).iloc[-1]

            # Check for NaN values
            if (np.isnan(adx) or np.isnan(supertrend_value) or
                np.isnan(ema_fast) or np.isnan(ema_slow)):
                return 'HOLD'

            # ===================================
            # EXIT LOGIC (check first)
            # ===================================
            if self._in_trend[symbol]:
                # Exit if Supertrend turns bearish
                if not np.isnan(supertrend_direction) and supertrend_direction < 0:
                    self._in_trend[symbol] = False
                    return 'SELL'

                # Exit if trend weakens (ADX drops below threshold)
                if adx < self.adx_weak_trend:
                    self._in_trend[symbol] = False
                    return 'SELL'

                # Exit if price drops below fast EMA (trend break)
                if current_price < ema_fast:
                    self._in_trend[symbol] = False
                    return 'SELL'

            # ===================================
            # ENTRY LOGIC
            # ===================================
            if not self._in_trend[symbol]:
                # Condition 1: Strong trend (ADX > 25)
                strong_trend = adx > self.adx_strong_trend

                # Condition 2: Supertrend bullish
                bullish_supertrend = not np.isnan(supertrend_direction) and supertrend_direction > 0

                # Condition 3: Fast EMA above slow EMA (trend alignment)
                emas_aligned = ema_fast > ema_slow

                # Condition 4: Price above VWAP (institutional support)
                above_vwap = current_price > vwap

                # Condition 5: +DI > -DI (bullish directional movement)
                bullish_di = (not np.isnan(plus_di) and not np.isnan(minus_di) and
                             plus_di > minus_di)

                # ALL conditions must be met
                if (strong_trend and bullish_supertrend and emas_aligned and
                    above_vwap and bullish_di):
                    self._in_trend[symbol] = True
                    return 'BUY'

        except Exception as e:
            return 'HOLD'

        return 'HOLD'

    def get_config(self):
        """Return serializable configuration"""
        base_config = super().get_config()
        base_config.update({
            'adx_period': self.adx_period,
            'adx_strong_trend': self.adx_strong_trend,
            'adx_weak_trend': self.adx_weak_trend,
            'supertrend_period': self.supertrend_period,
            'supertrend_multiplier': self.supertrend_multiplier,
            'ema_fast': self.ema_fast,
            'ema_slow': self.ema_slow
        })
        return base_config
