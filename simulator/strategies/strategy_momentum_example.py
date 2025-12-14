"""
Example Momentum Strategy using pre-computed indicators
Shows how to use the optimized system
"""

import pandas as pd
import numpy as np
from strategy_base import StrategyBase, StrategyConfig

class Strategy(StrategyBase):
    def __init__(self, config: StrategyConfig = None):
        """Initialize with configuration"""
        if config is None:
            config = StrategyConfig(
                name="Momentum Example",
                color="#1f77b4",
                initial_capital=100000,
                position_size_pct=0.10,
                max_positions=10
            )
        
        super().__init__(config)
        
        # Strategy parameters
        self.fast_ma = 20
        self.slow_ma = 50
        self.rsi_period = 14
        
        # Declare required indicators (will be pre-computed)
        self.required_indicators = [
            f'sma_{self.fast_ma}',
            f'sma_{self.slow_ma}',
            f'rsi_{self.rsi_period}'
        ]
    
    def generate_signal(self, symbol, data, spy_data, bar_index):
        """
        Generate signal using pre-computed indicators
        
        Args:
            symbol: Stock symbol
            data: Historical data up to current bar (includes pre-computed indicators!)
            spy_data: SPY data (optional)
            bar_index: Current bar index (0-based)
            
        Returns:
            'BUY', 'SELL', or 'HOLD'
        """
        # Need minimum bars
        if len(data) < self.slow_ma + 1:
            return 'HOLD'
        
        # Current and previous indices (relative to current bar)
        current_idx = -1  # Current bar is always last in historical data
        prev_idx = -2     # Previous bar
        
        try:
            # Access pre-computed indicators (FAST - no calculation!)
            # These were computed once before simulation started
            fast_ma_current = data[f'sma_{self.fast_ma}'].iloc[current_idx]
            fast_ma_prev = data[f'sma_{self.fast_ma}'].iloc[prev_idx]
            
            slow_ma_current = data[f'sma_{self.slow_ma}'].iloc[current_idx]
            slow_ma_prev = data[f'sma_{self.slow_ma}'].iloc[prev_idx]
            
            rsi_current = data[f'rsi_{self.rsi_period}'].iloc[current_idx]
            
            # Check for NaN (shouldn't happen with pre-computation)
            if (pd.isna(fast_ma_current) or pd.isna(slow_ma_current) or 
                pd.isna(rsi_current)):
                return 'HOLD'
            
            # --- BUY SIGNAL ---
            # Golden Cross: Fast MA crosses above Slow MA
            # And RSI is not overbought
            if (fast_ma_current > slow_ma_current and 
                fast_ma_prev <= slow_ma_prev and
                rsi_current < 70):  # Not overbought
                return 'BUY'
            
            # --- SELL SIGNAL ---
            # Death Cross: Fast MA crosses below Slow MA
            # And RSI is not oversold (optional filter)
            elif (fast_ma_current < slow_ma_current and 
                  fast_ma_prev >= slow_ma_prev and
                  rsi_current > 30):  # Not oversold
                return 'SELL'
            
        except KeyError as e:
            # This shouldn't happen if indicators are properly pre-computed
            # But we handle it gracefully
            print(f"⚠️  {self.name}: Missing indicator {e}")
            return 'HOLD'
        except Exception as e:
            print(f"⚠️  {self.name}: Error in signal generation: {e}")
            return 'HOLD'
        
        # Default: hold position
        return 'HOLD'