"""
Weekly Threshold Strategy - REFACTORED FOR OPTIMIZATION
Buy on drops, sell on rises over rolling windows

BUY: Stock drops 5%+ over past 7 or 30 days
SELL: Stock rises 10%+ over past 7 or 30 days

Uses simple price comparisons for maximum performance
"""

import pandas as pd
import numpy as np
from strategy_base import StrategyBase, StrategyConfig

class Strategy(StrategyBase):
    """
    Rolling window threshold strategy
    """
    
    def __init__(self, config: StrategyConfig = None):
        """Initialize with configuration"""
        if config is None:
            config = StrategyConfig(
                name="Weekly Threshold",
                color="#4ECDC4",
                initial_capital=100000,
                position_size_pct=0.05,
                max_positions=20  # More positions since shorter holds
            )
        
        super().__init__(config)
        
        # Strategy parameters
        self.buy_threshold = -0.05    # -5% drop to buy
        self.sell_threshold = 0.10    # +10% rise to sell
        self.short_window = 7         # Weekly
        self.long_window = 30         # Monthly
        
        # No indicators needed - we calculate returns directly
        self.required_indicators = []
        
        # Track last signal per timeframe (to prevent repeated signals)
        self._last_weekly_signal = {}
        self._last_monthly_signal = {}
    
    def generate_signal(self, symbol, data, spy_data, bar_index):
        """
        Generate signal based on rolling window returns
        
        Args:
            symbol: Stock symbol
            data: Historical stock data up to current bar
            spy_data: Historical SPY data (not used)
            bar_index: Current bar index
            
        Returns:
            'BUY', 'SELL', or 'HOLD'
        """
        # Need at least long_window bars
        if len(data) < self.long_window:
            return 'HOLD'
        
        # Initialize tracking for this symbol
        if symbol not in self._last_weekly_signal:
            self._last_weekly_signal[symbol] = None
            self._last_monthly_signal[symbol] = None
        
        try:
            # Get current price
            current_price = data['close'].iloc[-1]
            
            # ===================================
            # CALCULATE ROLLING RETURNS
            # ===================================
            
            # 7-day return (weekly)
            if len(data) >= self.short_window:
                price_7d_ago = data['close'].iloc[-self.short_window]
                return_7d = (current_price - price_7d_ago) / price_7d_ago
            else:
                return_7d = 0
            
            # 30-day return (monthly)
            price_30d_ago = data['close'].iloc[-self.long_window]
            return_30d = (current_price - price_30d_ago) / price_30d_ago
            
            # ===================================
            # WEEKLY WINDOW SIGNALS
            # ===================================
            
            # BUY: Dropped 5%+ in past week
            if return_7d <= self.buy_threshold:
                if self._last_weekly_signal[symbol] is None or self._last_weekly_signal[symbol] == 'SELL':
                    self._last_weekly_signal[symbol] = 'BUY'
                    return 'BUY'
            
            # SELL: Rose 10%+ in past week (if we bought on weekly)
            elif return_7d >= self.sell_threshold:
                if self._last_weekly_signal[symbol] == 'BUY':
                    self._last_weekly_signal[symbol] = 'SELL'
                    return 'SELL'
            
            # Reset if price recovers to neutral (-2% to +2%)
            elif -0.02 < return_7d < 0.02:
                if self._last_weekly_signal[symbol] == 'SELL':
                    self._last_weekly_signal[symbol] = None
            
            # ===================================
            # MONTHLY WINDOW SIGNALS
            # ===================================
            
            # BUY: Dropped 5%+ in past month
            if return_30d <= self.buy_threshold:
                if self._last_monthly_signal[symbol] is None or self._last_monthly_signal[symbol] == 'SELL':
                    self._last_monthly_signal[symbol] = 'BUY'
                    return 'BUY'
            
            # SELL: Rose 10%+ in past month (if we bought on monthly)
            elif return_30d >= self.sell_threshold:
                if self._last_monthly_signal[symbol] == 'BUY':
                    self._last_monthly_signal[symbol] = 'SELL'
                    return 'SELL'
            
            # Reset if price recovers to neutral
            elif -0.02 < return_30d < 0.02:
                if self._last_monthly_signal[symbol] == 'SELL':
                    self._last_monthly_signal[symbol] = None
            
        except Exception as e:
            return 'HOLD'
        
        return 'HOLD'
    
    def get_config(self):
        """Return serializable configuration"""
        base_config = super().get_config()
        base_config.update({
            'buy_threshold': self.buy_threshold,
            'sell_threshold': self.sell_threshold,
            'short_window': self.short_window,
            'long_window': self.long_window
        })
        return base_config