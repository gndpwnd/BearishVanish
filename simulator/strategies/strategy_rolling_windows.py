"""
Strategy #2: Rolling Window Percentage Changes
Buys and sells based on 7-day and 30-day rolling window returns
Uses streaming windows (past N days, not calendar dates)
"""

import pandas as pd
from strategy_base import StrategyBase, StrategyConfig


class Strategy(StrategyBase):
    """
    Rolling Window Threshold Strategy - Weekly and Monthly
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
        self.weekly_window = 7  # 7 trading days
        self.monthly_window = 30  # 30 trading days
        
        # Thresholds
        self.buy_threshold = -0.05  # -5%
        self.sell_threshold = 0.10  # +10%
        
        # State tracking (per symbol, separate for each window)
        self._weekly_state = {}
        self._monthly_state = {}
    
    def generate_signal(self, symbol, data, spy_data, bar_index):
        """
        Generate signals based on rolling window returns
        
        Args:
            symbol: Stock symbol
            data: Historical stock data up to current bar
            spy_data: Historical SPY data (not used)
            bar_index: Current bar index
            
        Returns:
            'BUY', 'SELL', or 'HOLD'
        """
        # Need minimum data
        if len(data) < max(self.weekly_window, self.monthly_window) + 1:
            return 'HOLD'
        
        # Initialize tracking for this symbol
        if symbol not in self._weekly_state:
            self._weekly_state[symbol] = None
            self._monthly_state[symbol] = None
        
        try:
            current_price = data['close'].iloc[-1]
            
            # Calculate rolling returns
            # 7-day return
            if len(data) >= self.weekly_window:
                price_7d_ago = data['close'].iloc[-self.weekly_window]
                return_7d = (current_price - price_7d_ago) / price_7d_ago
            else:
                return_7d = 0
            
            # 30-day return
            if len(data) >= self.monthly_window:
                price_30d_ago = data['close'].iloc[-self.monthly_window]
                return_30d = (current_price - price_30d_ago) / price_30d_ago
            else:
                return_30d = 0
            
            # ==================================
            # WEEKLY WINDOW (7-DAY)
            # ==================================
            
            # BUY: Down 5%+ in past 7 days
            if return_7d <= self.buy_threshold:
                if self._weekly_state[symbol] is None or self._weekly_state[symbol] == 'SELL':
                    self._weekly_state[symbol] = 'BUY'
                    return 'BUY'
            
            # SELL: Up 10%+ in past 7 days (if we bought)
            elif return_7d >= self.sell_threshold:
                if self._weekly_state[symbol] == 'BUY':
                    self._weekly_state[symbol] = 'SELL'
                    return 'SELL'
            
            # Reset if recovered to neutral (-2% to +2%)
            elif -0.02 < return_7d < 0.02:
                if self._weekly_state[symbol] == 'SELL':
                    self._weekly_state[symbol] = None
            
            # ==================================
            # MONTHLY WINDOW (30-DAY)
            # ==================================
            
            # BUY: Down 5%+ in past 30 days
            if return_30d <= self.buy_threshold:
                if self._monthly_state[symbol] is None or self._monthly_state[symbol] == 'SELL':
                    self._monthly_state[symbol] = 'BUY'
                    # Only return if weekly didn't already signal
                    if self._weekly_state[symbol] != 'BUY':
                        return 'BUY'
            
            # SELL: Up 10%+ in past 30 days (if we bought)
            elif return_30d >= self.sell_threshold:
                if self._monthly_state[symbol] == 'BUY':
                    self._monthly_state[symbol] = 'SELL'
                    # Only return if weekly didn't already signal
                    if self._weekly_state[symbol] != 'SELL':
                        return 'SELL'
            
            # Reset if recovered to neutral
            elif -0.02 < return_30d < 0.02:
                if self._monthly_state[symbol] == 'SELL':
                    self._monthly_state[symbol] = None
        
        except Exception:
            return 'HOLD'
        
        return 'HOLD'
    
    def get_config(self):
        """Return serializable configuration"""
        base_config = super().get_config()
        base_config.update({
            'weekly_window': self.weekly_window,
            'monthly_window': self.monthly_window,
            'buy_threshold': self.buy_threshold,
            'sell_threshold': self.sell_threshold,
        })
        return base_config
