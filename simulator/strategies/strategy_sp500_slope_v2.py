"""
Strategy #1: Slope Reversal vs S&P 500 - Corrected Version
Buys when stock slope reverses upward after crossing below S&P 500
Sells when stock slope reverses downward after crossing above S&P 500
Enforces one buy per cross below, one sell per cross above
"""

import pandas as pd
import numpy as np
from strategy_base import StrategyBase, StrategyConfig


class Strategy(StrategyBase):
    """
    S&P 500 Slope Reversal Strategy - Improved Version
    """
    
    def __init__(self, config: StrategyConfig = None):
        """Initialize with configuration"""
        if config is None:
            config = StrategyConfig(
                name="Slope Reversal SP500 v2",
                color="#2E86AB",
                initial_capital=100000,
                position_size_pct=0.10,
                max_positions=10
            )
        
        super().__init__(config)
        
        # State tracking (per symbol)
        self._last_cross_index = {}
        self._last_cross_was_below = {}
        self._last_signal_index = {}
        self._signal_count = {}
    
    def generate_signal(self, symbol, data, spy_data, bar_index):
        """
        Generate signal based on slope reversal and S&P 500 crossover
        
        Args:
            symbol: Stock symbol
            data: Historical stock data up to current bar
            spy_data: Historical SPY data up to current bar
            bar_index: Current bar index
            
        Returns:
            'BUY', 'SELL', or 'HOLD'
        """
        # Minimum data requirement
        if len(data) < 3 or spy_data is None or len(spy_data) < 3:
            return 'HOLD'
        
        # Initialize tracking for this symbol
        if symbol not in self._last_cross_index:
            self._last_cross_index[symbol] = -1
            self._last_cross_was_below[symbol] = None
            self._last_signal_index[symbol] = -1
            self._signal_count[symbol] = {'buy': 0, 'sell': 0}
        
        try:
            # Calculate cumulative returns
            stock_returns = data['close'].pct_change().fillna(0)
            spy_returns = spy_data['close'].pct_change().fillna(0)
            
            # Ensure same length
            min_len = min(len(stock_returns), len(spy_returns))
            stock_returns = stock_returns.iloc[-min_len:]
            spy_returns = spy_returns.iloc[-min_len:]
            
            stock_cum = (stock_returns.cumsum() * 100).values
            spy_cum = (spy_returns.cumsum() * 100).values
            
            # Calculate slope
            stock_slope = np.gradient(stock_cum)
            
            current_idx = len(stock_cum) - 1
            
            if current_idx < 2:
                return 'HOLD'
            
            # Detect crossover
            if current_idx >= 1:
                prev_diff = stock_cum[current_idx - 1] - spy_cum[current_idx - 1]
                curr_diff = stock_cum[current_idx] - spy_cum[current_idx]
                
                # Crossover detected (sign change)
                if prev_diff * curr_diff < 0:
                    self._last_cross_index[symbol] = current_idx
                    self._last_cross_was_below[symbol] = (curr_diff < 0)
                    # Reset signal counter on new cross
                    self._last_signal_index[symbol] = -1
            
            # No crossover yet
            if self._last_cross_index[symbol] == -1:
                return 'HOLD'
            
            # Get slope values
            prev_slope = stock_slope[current_idx - 1]
            curr_slope = stock_slope[current_idx]
            
            # Current position relative to S&P
            currently_below = (stock_cum[current_idx] < spy_cum[current_idx])
            currently_above = (stock_cum[current_idx] > spy_cum[current_idx])
            
            # BUY: Stock crossed BELOW S&P, slope reverses from - to +
            if (self._last_cross_was_below[symbol] and
                self._last_signal_index[symbol] <= self._last_cross_index[symbol]):
                
                if (prev_slope < 0 and curr_slope > 0 and currently_below):
                    self._last_signal_index[symbol] = current_idx
                    return 'BUY'
            
            # SELL: Stock crossed ABOVE S&P, slope reverses from + to -
            elif (self._last_cross_was_below[symbol] is not None and
                  not self._last_cross_was_below[symbol] and
                  self._last_signal_index[symbol] <= self._last_cross_index[symbol]):
                
                if (prev_slope > 0 and curr_slope < 0 and currently_above):
                    self._last_signal_index[symbol] = current_idx
                    return 'SELL'
        
        except Exception:
            return 'HOLD'
        
        return 'HOLD'
    
    def get_config(self):
        """Return serializable configuration"""
        return super().get_config()
