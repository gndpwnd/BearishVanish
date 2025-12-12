"""
500 Intersection Algorithm Strategy
Detects crossovers between stock and S&P 500 cumulative returns,
then looks for slope changes to generate BUY/SELL signals.
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
        self.last_cross_index = {}
        self.last_cross_was_below = {}
    
    def detect_cross(self, stock_cum, sp500_cum):
        """Check if a crossover occurred at the last index"""
        if len(stock_cum) < 2:
            return False
        
        prev_diff = stock_cum.iloc[-2] - sp500_cum.iloc[-2]
        curr_diff = stock_cum.iloc[-1] - sp500_cum.iloc[-1]
        
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
        
        # Calculate slope
        stock_slope = np.gradient(stock_cum)
        
        current_idx = len(stock_cum) - 1
        
        # Detect crossover
        if self.detect_cross(stock_cum, sp500_cum):
            self.last_cross_index[symbol] = current_idx
            self.last_cross_was_below[symbol] = stock_cum.iloc[-1] < sp500_cum.iloc[-1]
        
        # Need at least 2 slope values
        if current_idx < 2:
            return None
        
        prev_slope = stock_slope[-2]
        curr_slope = stock_slope[-1]
        
        # BUY signal: crossed below SPY, now sloping up from negative
        if (self.last_cross_index[symbol] != -1 and
            self.last_cross_was_below[symbol] and
            prev_slope < 0 and curr_slope > 0 and
            stock_cum.iloc[-1] < sp500_cum.iloc[-1] and
            self.can_generate_signal('BUY', symbol)):
            return self.emit_signal('BUY', symbol)
        
        # SELL signal: crossed above SPY, now sloping down from positive
        elif (self.last_cross_index[symbol] != -1 and
              not self.last_cross_was_below[symbol] and
              prev_slope > 0 and curr_slope < 0 and
              stock_cum.iloc[-1] > sp500_cum.iloc[-1] and
              self.can_generate_signal('SELL', symbol)):
            return self.emit_signal('SELL', symbol)
        
        return None