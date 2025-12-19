"""
Weekly Threshold Strategy - WEEK-BY-WEEK ONLY
Buy on drops, sell on rises over 7-day rolling window

BUY: Stock drops 5%+ over past 7 days
SELL: Stock rises 10%+ over past 7 days

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
        self.window = 7               # Weekly window ONLY

        # No indicators needed - we calculate returns directly
        self.required_indicators = []

        # Track last signal (to prevent repeated signals)
        self._last_signal = {}
    
    def generate_signal(self, symbol, data, spy_data, bar_index):
        """
        Generate signal based on 7-day rolling window returns

        Args:
            symbol: Stock symbol
            data: Historical stock data up to current bar
            spy_data: Historical SPY data (not used)
            bar_index: Current bar index

        Returns:
            'BUY', 'SELL', or 'HOLD'
        """
        # Need at least window bars
        if len(data) < self.window:
            return 'HOLD'

        # Initialize tracking for this symbol
        if symbol not in self._last_signal:
            self._last_signal[symbol] = None
        
        try:
            # Get current price
            current_price = data['close'].iloc[-1]
            
            # ===================================
            # CALCULATE 7-DAY ROLLING RETURN
            # ===================================

            price_7d_ago = data['close'].iloc[-self.window]
            return_7d = (current_price - price_7d_ago) / price_7d_ago

            # ===================================
            # WEEKLY WINDOW SIGNALS (ONLY)
            # ===================================

            # BUY: Dropped 5%+ in past week
            if return_7d <= self.buy_threshold:
                if self._last_signal[symbol] is None or self._last_signal[symbol] == 'SELL':
                    self._last_signal[symbol] = 'BUY'
                    return 'BUY'

            # SELL: Rose 10%+ in past week (if we bought)
            elif return_7d >= self.sell_threshold:
                if self._last_signal[symbol] == 'BUY':
                    self._last_signal[symbol] = 'SELL'
                    return 'SELL'

            # Reset if price recovers to neutral (-2% to +2%)
            elif -0.02 < return_7d < 0.02:
                if self._last_signal[symbol] == 'SELL':
                    self._last_signal[symbol] = None
            
        except Exception as e:
            return 'HOLD'
        
        return 'HOLD'
    
    def get_config(self):
        """Return serializable configuration"""
        base_config = super().get_config()
        base_config.update({
            'buy_threshold': self.buy_threshold,
            'sell_threshold': self.sell_threshold,
            'window': self.window
        })
        return base_config