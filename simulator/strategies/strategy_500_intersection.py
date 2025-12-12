"""
500 Intersection Strategy - PURE LOGIC VERSION
Buy when slope reverses UP after crossing BELOW S&P 500
Sell when slope reverses DOWN after crossing ABOVE S&P 500

NO artificial exits - strategy holds until natural exit signal
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from strategy_base import StrategyBase
import numpy as np

class Strategy(StrategyBase):
    def __init__(self, color="blue"):
        super().__init__(name="500 Intersection", color=color)
        
    def reset(self):
        super().reset()
        self.last_cross_index = {}      # When last crossover occurred
        self.last_cross_was_below = {}  # True if last cross was stock going below S&P
    
    def detect_cross(self, stock_cum, sp500_cum):
        """Check if a crossover occurred at the last index"""
        if len(stock_cum) < 2:
            return False
        
        prev_diff = stock_cum.iloc[-2] - sp500_cum.iloc[-2]
        curr_diff = stock_cum.iloc[-1] - sp500_cum.iloc[-1]
        
        # Cross occurs when signs change (positive to negative or vice versa)
        return prev_diff * curr_diff < 0
    
    def on_data(self, stock_data, spy_data, current_date, symbol):
        if len(stock_data) < 3:
            return None
        
        # Initialize tracking for this symbol
        if symbol not in self.last_cross_index:
            self.last_cross_index[symbol] = -1
            self.last_cross_was_below[symbol] = None
        
        # Calculate cumulative returns
        stock_returns = stock_data['close'].pct_change().fillna(0)
        sp500_returns = spy_data['close'].pct_change().fillna(0)
        
        stock_cum = np.cumsum(stock_returns) * 100
        sp500_cum = np.cumsum(sp500_returns) * 100
        
        # Calculate slope (first derivative of cumulative returns)
        stock_slope = np.gradient(stock_cum)
        
        current_idx = len(stock_cum) - 1
        
        # Detect and record crossover
        if self.detect_cross(stock_cum, sp500_cum):
            self.last_cross_index[symbol] = current_idx
            self.last_cross_was_below[symbol] = stock_cum.iloc[-1] < sp500_cum.iloc[-1]
        
        # Need at least 2 slope values to detect reversal
        if current_idx < 2:
            return None
        
        prev_slope = stock_slope[-2]
        curr_slope = stock_slope[-1]
        
        # Current position relative to S&P
        currently_below_sp500 = stock_cum.iloc[-1] < sp500_cum.iloc[-1]
        
        # ==============================================================
        # SELL LOGIC: Stock crossed ABOVE S&P, slope reverses from + to -
        # ==============================================================
        if self.last_executed_signal.get(symbol) == 'BUY':
            # Conditions:
            # 1. Had a previous crossover
            # 2. Last cross was going ABOVE (not below)
            # 3. Previous slope was positive
            # 4. Current slope turns negative
            # 5. Still above S&P 500 (can't sell while below)
            
            if (self.last_cross_index[symbol] != -1 and
                not self.last_cross_was_below[symbol] and  # Crossed above
                prev_slope > 0 and 
                curr_slope < 0 and
                not currently_below_sp500 and  # Must be above to sell
                self.can_generate_signal('SELL', symbol)):
                
                return self.emit_signal('SELL', symbol)
        
        # ==============================================================
        # BUY LOGIC: Stock crossed BELOW S&P, slope reverses from - to +
        # ==============================================================
        # Conditions:
        # 1. Had a previous crossover
        # 2. Last cross was going BELOW (not above)
        # 3. Previous slope was negative
        # 4. Current slope turns positive
        # 5. Still below S&P 500 (can't buy while above)
        
        if (self.last_cross_index[symbol] != -1 and
            self.last_cross_was_below[symbol] and  # Crossed below
            prev_slope < 0 and 
            curr_slope > 0 and
            currently_below_sp500 and  # Must be below to buy
            self.can_generate_signal('BUY', symbol)):
            
            return self.emit_signal('BUY', symbol)
        
        return None