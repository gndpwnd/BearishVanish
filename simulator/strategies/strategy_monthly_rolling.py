"""
Strategy #3: Monthly Rolling Window Only
Simplified version - uses only 30-day rolling window
"""

import pandas as pd
from strategy_base import StrategyBase, StrategyConfig


class Strategy(StrategyBase):
    """
    Rolling Window Threshold Strategy - Monthly Only
    Simpler version than rolling_windows.py
    """
    
    def __init__(self, config: StrategyConfig = None):
        """Initialize with configuration"""
        if config is None:
            config = StrategyConfig(
                name="Monthly Rolling",
                color="#F18F01",
                initial_capital=100000,
                position_size_pct=0.10,
                max_positions=10
            )
        
        super().__init__(config)
        
        # Window parameters (in bars - assuming daily bars)
        self.window = 30  # 30 trading days
        
        # Thresholds
        self.buy_threshold = -0.05  # -5%
        self.sell_threshold = 0.10  # +10%
        
        # State tracking (per symbol)
        self._state = {}
    
    def generate_signal(self, symbol, data, spy_data, bar_index):
        """
        Generate signals based on 30-day rolling window returns
        
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
            price_30d_ago = data['close'].iloc[-self.window]
            
            # Calculate 30-day return
            return_30d = (current_price - price_30d_ago) / price_30d_ago
            
            # BUY: Down 5%+ in past 30 days
            if return_30d <= self.buy_threshold:
                if self._state[symbol] is None or self._state[symbol] == 'SELL':
                    self._state[symbol] = 'BUY'
                    return 'BUY'
            
            # SELL: Up 10%+ in past 30 days (if we bought)
            elif return_30d >= self.sell_threshold:
                if self._state[symbol] == 'BUY':
                    self._state[symbol] = 'SELL'
                    return 'SELL'
            
            # Reset if recovered to neutral (-2% to +2%)
            elif -0.02 < return_30d < 0.02:
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
