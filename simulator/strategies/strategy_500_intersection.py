"""
500 Intersection Strategy - REFACTORED FOR OPTIMIZATION
Detects crossovers between stock and S&P 500, then waits for slope reversals

BUY: Stock crosses BELOW S&P 500, then slope reverses from negative to positive
SELL: Stock crosses ABOVE S&P 500, then slope reverses from positive to negative

Uses pre-computed indicators for performance
"""

import pandas as pd
import numpy as np
from strategy_base import StrategyBase, StrategyConfig

class Strategy(StrategyBase):
    """
    S&P 500 Intersection strategy with slope reversal detection
    """
    
    def __init__(self, config: StrategyConfig = None):
        """Initialize with configuration"""
        if config is None:
            config = StrategyConfig(
                name="500 Intersection",
                color="#FF6B6B",
                initial_capital=100000,
                position_size_pct=0.10,
                max_positions=10
            )
        
        super().__init__(config)
        
        # Strategy parameters
        self.min_bars_after_cross = 1  # Minimum bars after crossover before signal
        
        # This strategy uses cumulative returns and slope calculations
        # We don't pre-compute these as they're simple operations
        self.required_indicators = []
        
        # State tracking (per symbol)
        # Note: This is OK because we're tracking historical events
        self._last_cross_index = {}
        self._last_cross_was_below = {}
        self._last_signal_index = {}  # Track when we last emitted a signal
    
    def generate_signal(self, symbol, data, spy_data, bar_index):
        """
        Generate signal based on crossover and slope reversal
        
        Args:
            symbol: Stock symbol
            data: Historical stock data up to current bar
            spy_data: Historical SPY data up to current bar
            bar_index: Current bar index
            
        Returns:
            'BUY', 'SELL', or 'HOLD'
        """
        # Need minimum data
        if len(data) < 3 or spy_data is None or len(spy_data) < 3:
            return 'HOLD'
        
        # Initialize tracking for this symbol
        if symbol not in self._last_cross_index:
            self._last_cross_index[symbol] = -1
            self._last_cross_was_below[symbol] = None
            self._last_signal_index[symbol] = -1
        
        try:
            # Calculate cumulative returns (simple, fast operation)
            stock_returns = data['close'].pct_change().fillna(0)
            spy_returns = spy_data['close'].pct_change().fillna(0)
            
            # Ensure same length
            min_len = min(len(stock_returns), len(spy_returns))
            stock_returns = stock_returns.iloc[-min_len:]
            spy_returns = spy_returns.iloc[-min_len:]
            
            stock_cum = (stock_returns.cumsum() * 100).values
            spy_cum = (spy_returns.cumsum() * 100).values
            
            # Calculate slope (gradient of cumulative returns)
            stock_slope = np.gradient(stock_cum)
            
            # Current position in arrays
            current_idx = len(stock_cum) - 1
            
            # Need at least 2 points for slope comparison
            if current_idx < 2:
                return 'HOLD'
            
            # ===================================
            # DETECT CROSSOVER
            # ===================================
            # Check if crossover occurred at current bar
            if current_idx >= 1:
                prev_diff = stock_cum[current_idx - 1] - spy_cum[current_idx - 1]
                curr_diff = stock_cum[current_idx] - spy_cum[current_idx]
                
                # Crossover: signs change
                if prev_diff * curr_diff < 0:
                    self._last_cross_index[symbol] = current_idx
                    self._last_cross_was_below[symbol] = (curr_diff < 0)
            
            # Check if we've had a crossover
            if self._last_cross_index[symbol] == -1:
                return 'HOLD'
            
            # Get slope values
            prev_slope = stock_slope[current_idx - 1]
            curr_slope = stock_slope[current_idx]
            
            # Current position relative to S&P
            currently_below_sp500 = (stock_cum[current_idx] < spy_cum[current_idx])
            
            # ===================================
            # BUY SIGNAL
            # ===================================
            # Stock crossed BELOW S&P, slope reverses from - to +
            # But only emit signal once per cross (at the signal index or after)
            if (self._last_cross_was_below[symbol] and
                self._last_signal_index[symbol] < self._last_cross_index[symbol]):  # Haven't signaled yet for this cross
                
                if (prev_slope < 0 and curr_slope > 0 and currently_below_sp500):
                    self._last_signal_index[symbol] = current_idx
                    return 'BUY'
            
            # ===================================
            # SELL SIGNAL
            # ===================================
            # Stock crossed ABOVE S&P, slope reverses from + to -
            # But only emit signal once per cross
            elif (self._last_cross_was_below[symbol] is not None and
                  not self._last_cross_was_below[symbol] and
                  self._last_signal_index[symbol] < self._last_cross_index[symbol]):  # Haven't signaled yet for this cross
                
                if (prev_slope > 0 and curr_slope < 0 and not currently_below_sp500):
                    self._last_signal_index[symbol] = current_idx
                    return 'SELL'
            
        except Exception as e:
            # Handle any calculation errors gracefully
            return 'HOLD'
        
        return 'HOLD'
    
    def get_config(self):
        """Return serializable configuration"""
        base_config = super().get_config()
        base_config.update({
            'min_bars_after_cross': self.min_bars_after_cross
        })
        return base_config