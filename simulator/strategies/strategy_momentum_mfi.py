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
                max_positions=8
            )

        super().__init__(config)

        # Strategy parameters
        self.mfi_period = 14
        self.mfi_oversold = 20
        self.mfi_overbought = 80
        self.sma_trend = 50
        self.sma_exit = 20
        self.supertrend_period = 10
        self.supertrend_multiplier = 3.0

        # Required indicators
        self.required_indicators = [
            'mfi',
            'obv',
            'sma',
            'supertrend'
        ]

        # Track state
        self._in_position = {}
        self._obv_history = {}  # Track last 3 OBV values

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

        try:
            current_price = data['close'].iloc[-1]

            # Get indicators
            mfi = data.get('mfi', pd.Series([50.0] * len(data))).iloc[-1]
            obv = data.get('obv', pd.Series([0.0] * len(data))).iloc[-1]
            sma_50 = data.get(f'sma_{self.sma_trend}', pd.Series([np.nan] * len(data))).iloc[-1]
            sma_20 = data.get(f'sma_{self.sma_exit}', pd.Series([np.nan] * len(data))).iloc[-1]
            supertrend_direction = data.get('supertrend_direction', pd.Series([np.nan] * len(data))).iloc[-1]

            # Check for NaN values
            if np.isnan(sma_50) or np.isnan(sma_20) or np.isnan(mfi):
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
                # Exit if MFI overbought (institutional distribution)
                if mfi > self.mfi_overbought:
                    self._in_position[symbol] = False
                    return 'SELL'

                # Exit if price drops below 20-day SMA (momentum loss)
                if current_price < sma_20:
                    self._in_position[symbol] = False
                    return 'SELL'

                # Exit if OBV falling (volume not confirming)
                if obv_falling:
                    self._in_position[symbol] = False
                    return 'SELL'

                # Exit if Supertrend turns bearish
                if not np.isnan(supertrend_direction) and supertrend_direction < 0:
                    self._in_position[symbol] = False
                    return 'SELL'

            # ===================================
            # ENTRY LOGIC
            # ===================================
            if not self._in_position[symbol]:
                # Condition 1: MFI recovering from oversold (institutional accumulation)
                mfi_signal = mfi > self.mfi_oversold and mfi < 50  # Sweet spot

                # Condition 2: Price above 50-day SMA (in uptrend)
                in_uptrend = current_price > sma_50

                # Condition 3: OBV rising (volume confirms)
                volume_confirming = obv_rising

                # Condition 4: Supertrend bullish
                bullish_trend = not np.isnan(supertrend_direction) and supertrend_direction > 0

                # ALL conditions must be met
                if mfi_signal and in_uptrend and volume_confirming and bullish_trend:
                    self._in_position[symbol] = True
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
            'supertrend_multiplier': self.supertrend_multiplier
        })
        return base_config
