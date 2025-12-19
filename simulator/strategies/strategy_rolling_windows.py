"""
Strategy #2: Rolling Window Percentage Changes - WEEK-BY-WEEK ONLY
Buys and sells based on 7-day rolling window returns
Uses streaming windows (past N days, not calendar dates)
"""

import pandas as pd
from strategy_base import StrategyBase, StrategyConfig


class Strategy(StrategyBase):
    """
    Rolling Window Threshold Strategy - Weekly Only
    """

    def __init__(self, config: StrategyConfig = None):
        """Initialize with configuration"""
        if config is None:
            config = StrategyConfig(
                name="Rolling Windows",
                color="#A23B72",
                initial_capital=100000,
                position_size_pct=0.10,
                max_positions=10
            )

        super().__init__(config)

        # Window parameters (in bars - assuming daily bars)
        self.window = 7  # 7 trading days (weekly)

        # Thresholds
        self.buy_threshold = -0.05  # -5%
        self.sell_threshold = 0.10  # +10%

        # State tracking (per symbol)
        self._state = {}
    
    def generate_signal(self, symbol, data, spy_data, bar_index):
        """
        Generate signals based on 7-day rolling window returns

        Args:
            symbol: Stock symbol
            data: Historical stock data up to current bar
            spy_data: Historical SPY data (not used)
            bar_index: Current bar index

        Returns:
            'BUY', 'SELL', or 'HOLD'
        """
        # Need minimum data
        if len(data) < self.window + 1:
            return 'HOLD'

        # Initialize tracking for this symbol
        if symbol not in self._state:
            self._state[symbol] = None

        try:
            current_price = data['close'].iloc[-1]

            # Calculate 7-day rolling return
            price_7d_ago = data['close'].iloc[-self.window]
            return_7d = (current_price - price_7d_ago) / price_7d_ago

            # ==================================
            # WEEKLY WINDOW (7-DAY) - ONLY
            # ==================================

            # BUY: Down 5%+ in past 7 days
            if return_7d <= self.buy_threshold:
                if self._state[symbol] is None or self._state[symbol] == 'SELL':
                    self._state[symbol] = 'BUY'
                    return 'BUY'

            # SELL: Up 10%+ in past 7 days (if we bought)
            elif return_7d >= self.sell_threshold:
                if self._state[symbol] == 'BUY':
                    self._state[symbol] = 'SELL'
                    return 'SELL'

            # Reset if recovered to neutral (-2% to +2%)
            elif -0.02 < return_7d < 0.02:
                if self._state[symbol] == 'SELL':
                    self._state[symbol] = None

        except Exception:
            return 'HOLD'

        return 'HOLD'
    
    def get_config(self):
        """Return serializable configuration"""
        base_config = super().get_config()
        base_config.update({
            'window': self.window,
            'buy_threshold': self.buy_threshold,
            'sell_threshold': self.sell_threshold,
        })
        return base_config
