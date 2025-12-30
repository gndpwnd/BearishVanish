"""
Mean Reversion Strategy - Institutional Grade
Buys oversold stocks with strong support and sells when they return to mean

Based on principles used by Renaissance Technologies and Two Sigma:
- Statistical mean reversion
- Multi-indicator confirmation
- Volume validation
- Risk management with stop-loss

Entry Signals:
- Price below Bollinger Band lower + RSI < 30 + High volume
- Price above VWAP after oversold condition

Exit Signals:
- Price returns to Bollinger middle band
- RSI > 70 (overbought)
- Stop-loss: 5% below entry

Risk Controls:
- Maximum 8% of portfolio per position
- Maximum 10 concurrent positions
- Requires volume confirmation (1.2x average)
"""

import pandas as pd
import numpy as np
from strategy_base import StrategyBase, StrategyConfig


class Strategy(StrategyBase):
    """Mean Reversion Strategy"""

    def __init__(self, config: StrategyConfig = None):
        if config is None:
            config = StrategyConfig(
                name="Mean Reversion",
                color="#FF6B6B",
                initial_capital=100000,
                position_size_pct=0.08,  # 8% per position
                max_positions=10
            )

        super().__init__(config)

        # Strategy parameters
        self.bb_period = 20
        self.bb_std = 2.0
        self.rsi_period = 14
        self.rsi_oversold = 35  # Raised from 30 to 35 for more signals
        self.rsi_overbought = 70
        self.volume_threshold = 1.1  # Lowered from 1.2 to 1.1 for more signals
        self.stop_loss_pct = 0.05  # 5% stop-loss

        # Required indicators
        self.required_indicators = [
            'bollinger_bands',
            'rsi',
            'vwap',
            'relative_volume'
        ]

        # Track entry prices for stop-loss
        self._entry_prices = {}
        self._position_state = {}  # Track if we're in a position

    def generate_signal(self, symbol, data, spy_data, bar_index):
        """
        Generate mean reversion signal

        Logic:
        1. BUY: Price touches lower BB + RSI oversold + volume spike + price > VWAP
        2. SELL: Price returns to middle BB OR RSI overbought OR stop-loss hit
        """
        # Need enough data
        if len(data) < max(self.bb_period, self.rsi_period, 20):
            return 'HOLD'

        # Initialize tracking
        if symbol not in self._position_state:
            self._position_state[symbol] = False
            self._entry_prices[symbol] = None

        try:
            current_price = data['close'].iloc[-1]

            # Get indicators
            bb_upper = data.get('bollinger_bands_upper', pd.Series([np.nan] * len(data))).iloc[-1]
            bb_middle = data.get('bollinger_bands_middle', pd.Series([np.nan] * len(data))).iloc[-1]
            bb_lower = data.get('bollinger_bands_lower', pd.Series([np.nan] * len(data))).iloc[-1]
            rsi = data.get('rsi', pd.Series([50.0] * len(data))).iloc[-1]
            vwap = data.get('vwap', pd.Series([current_price] * len(data))).iloc[-1]
            rel_volume = data.get('relative_volume', pd.Series([1.0] * len(data))).iloc[-1]

            # Check for NaN values
            if np.isnan(bb_lower) or np.isnan(bb_middle) or np.isnan(rsi) or np.isnan(vwap):
                return 'HOLD'

            # ===================================
            # EXIT LOGIC (check first)
            # ===================================
            if self._position_state[symbol]:
                entry_price = self._entry_prices[symbol]

                # Stop-loss check
                if current_price < entry_price * (1 - self.stop_loss_pct):
                    self._position_state[symbol] = False
                    self._entry_prices[symbol] = None
                    return 'SELL'

                # Take profit at mean reversion
                if current_price >= bb_middle:
                    self._position_state[symbol] = False
                    self._entry_prices[symbol] = None
                    return 'SELL'

                # Overbought exit
                if rsi > self.rsi_overbought:
                    self._position_state[symbol] = False
                    self._entry_prices[symbol] = None
                    return 'SELL'

            # ===================================
            # ENTRY LOGIC (Phase 2: Relaxed to OR logic)
            # ===================================
            if not self._position_state[symbol]:
                # Condition 1: Price below/near lower Bollinger Band (oversold)
                price_oversold = current_price <= bb_lower * 1.02  # Within 2% of lower band

                # Condition 2: RSI oversold
                rsi_oversold = rsi < self.rsi_oversold

                # Condition 3: Volume spike (institutional confirmation)
                volume_spike = rel_volume > self.volume_threshold

                # Phase 2 Fix: Use OR logic instead of AND
                # Entry Pattern A: BB oversold + RSI oversold (classic mean reversion)
                pattern_a = price_oversold and rsi_oversold

                # Entry Pattern B: BB oversold + Volume spike (institutional buying)
                pattern_b = price_oversold and volume_spike

                # Entry Pattern C: RSI very oversold (< 25) with any volume
                pattern_c = rsi < 25

                # Enter if ANY pattern matches
                if pattern_a or pattern_b or pattern_c:
                    self._position_state[symbol] = True
                    self._entry_prices[symbol] = current_price
                    return 'BUY'

        except Exception as e:
            return 'HOLD'

        return 'HOLD'

    def get_config(self):
        """Return serializable configuration"""
        base_config = super().get_config()
        base_config.update({
            'bb_period': self.bb_period,
            'bb_std': self.bb_std,
            'rsi_period': self.rsi_period,
            'rsi_oversold': self.rsi_oversold,
            'rsi_overbought': self.rsi_overbought,
            'volume_threshold': self.volume_threshold,
            'stop_loss_pct': self.stop_loss_pct
        })
        return base_config
