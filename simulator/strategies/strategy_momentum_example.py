"""
Example Momentum Strategy using pre-computed indicators
Updated for parallel processing compatibility
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
        self.rsi_oversold = 30
        self.rsi_overbought = 70
        
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
        prev_idx = -2 if len(data) >= 2 else -1  # Previous bar
        
        try:
            # Access pre-computed indicators (FAST - no calculation!)
            fast_ma_col = f'sma_{self.fast_ma}'
            slow_ma_col = f'sma_{self.slow_ma}'
            rsi_col = f'rsi_{self.rsi_period}'
            
            if fast_ma_col not in data.columns or slow_ma_col not in data.columns or rsi_col not in data.columns:
                return 'HOLD'
            
            fast_ma_current = data[fast_ma_col].iloc[current_idx]
            fast_ma_prev = data[fast_ma_col].iloc[prev_idx] if prev_idx >= -len(data) else None
            
            slow_ma_current = data[slow_ma_col].iloc[current_idx]
            slow_ma_prev = data[slow_ma_col].iloc[prev_idx] if prev_idx >= -len(data) else None
            
            rsi_current = data[rsi_col].iloc[current_idx]
            
            # Check for NaN (shouldn't happen with pre-computation)
            if (pd.isna(fast_ma_current) or pd.isna(slow_ma_current) or 
                pd.isna(rsi_current)):
                return 'HOLD'
            
            # Need previous values for crossover detection
            if fast_ma_prev is None or slow_ma_prev is None:
                return 'HOLD'
            
            # --- BUY SIGNAL ---
            # Golden Cross: Fast MA crosses above Slow MA
            # And RSI is not overbought
            if (fast_ma_prev <= slow_ma_prev and  # Was below or equal
                fast_ma_current > slow_ma_current and  # Now above
                rsi_current < self.rsi_overbought):  # Not overbought
                return 'BUY'
            
            # --- SELL SIGNAL ---
            # Death Cross: Fast MA crosses below Slow MA
            # And RSI is not oversold (optional filter)
            elif (fast_ma_prev >= slow_ma_prev and  # Was above or equal
                  fast_ma_current < slow_ma_current and  # Now below
                  rsi_current > self.rsi_oversold):  # Not oversold
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
    
    def get_config(self):
        """Get serializable configuration"""
        base_config = super().get_config()
        base_config.update({
            'fast_ma': self.fast_ma,
            'slow_ma': self.slow_ma,
            'rsi_period': self.rsi_period,
            'rsi_oversold': self.rsi_oversold,
            'rsi_overbought': self.rsi_overbought
        })
        return base_config