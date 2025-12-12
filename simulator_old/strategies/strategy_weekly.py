"""
Weekly Threshold Strategy
Generates signals based on week-over-week percentage changes on Mondays.
BUY when stock drops >= 5%, SELL when stock rises >= 10%.
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from strategy_base import StrategyBase
import pandas as pd

class Strategy(StrategyBase):
    def __init__(self, color="red", buy_threshold=-0.05, sell_threshold=0.10):
        super().__init__(name="Weekly Threshold", color=color)
        self.buy_threshold = buy_threshold
        self.sell_threshold = sell_threshold
        
    def reset(self):
        super().reset()
        self.last_monday_price = {}
        self.last_monday_date = {}
    
    def on_data(self, stock_data, spy_data, current_date, symbol):
        if len(stock_data) < 2:
            return None
        
        # Initialize tracking for this symbol
        if symbol not in self.last_monday_price:
            self.last_monday_price[symbol] = None
            self.last_monday_date[symbol] = None
        
        current_price = stock_data['close'].iloc[-1]
        
        # Check if current date is a Monday
        if current_date.weekday() == 0:  # Monday
            # If we have a previous Monday, check thresholds
            if self.last_monday_price[symbol] is not None:
                pct_change = (current_price - self.last_monday_price[symbol]) / self.last_monday_price[symbol]
                
                if pct_change <= self.buy_threshold and self.can_generate_signal('BUY', symbol):
                    # Update for next week
                    self.last_monday_price[symbol] = current_price
                    self.last_monday_date[symbol] = current_date
                    return self.emit_signal('BUY', symbol)
                
                elif pct_change >= self.sell_threshold and self.can_generate_signal('SELL', symbol):
                    # Update for next week
                    self.last_monday_price[symbol] = current_price
                    self.last_monday_date[symbol] = current_date
                    return self.emit_signal('SELL', symbol)
            
            # Update last Monday price
            self.last_monday_price[symbol] = current_price
            self.last_monday_date[symbol] = current_date
        
        return None