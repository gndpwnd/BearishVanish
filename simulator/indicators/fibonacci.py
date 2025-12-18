"""
Fibonacci Retracement & Extension Levels Indicator
Calculates Fibonacci retracement levels based on a lookback period
"""

import numpy as np
import pandas as pd


def calculate_fibonacci_levels(data, lookback_period=20):
    """
    Calculate Fibonacci retracement and extension levels
    
    Args:
        data: DataFrame with 'high', 'low', 'close' columns
        lookback_period: Number of bars to look back for high/low
        
    Returns:
        dict with Fibonacci levels
    """
    if len(data) < lookback_period:
        return {
            'high': 0.0,
            'low': 0.0,
            'level_0_0': 0.0,
            'level_0_236': 0.0,
            'level_0_382': 0.0,
            'level_0_5': 0.0,
            'level_0_618': 0.0,
            'level_0_786': 0.0,
            'level_1_0': 0.0,
            'level_1_236': 0.0,
            'level_1_382': 0.0,
        }
    
    # Get the lookback window
    lookback_data = data.iloc[-lookback_period:]
    
    # Find period high and low
    period_high = lookback_data['high'].max()
    period_low = lookback_data['low'].min()
    
    # Calculate difference
    diff = period_high - period_low
    
    if diff == 0:
        return {
            'high': period_high,
            'low': period_low,
            'level_0_0': period_low,
            'level_0_236': period_low,
            'level_0_382': period_low,
            'level_0_5': period_low,
            'level_0_618': period_low,
            'level_0_786': period_low,
            'level_1_0': period_high,
            'level_1_236': period_high,
            'level_1_382': period_high,
        }
    
    # Retracement levels (0.0 = low, 1.0 = high)
    retracement_236 = period_high - (diff * 0.236)
    retracement_382 = period_high - (diff * 0.382)
    retracement_500 = period_high - (diff * 0.500)
    retracement_618 = period_high - (diff * 0.618)
    retracement_786 = period_high - (diff * 0.786)
    
    # Extension levels (beyond the original range)
    extension_236 = period_low - (diff * 0.236)
    extension_382 = period_low - (diff * 0.382)
    
    return {
        'high': period_high,
        'low': period_low,
        # Retracements (0.0 = 100%, 1.0 = 0%)
        'level_0_0': period_low,
        'level_0_236': retracement_236,
        'level_0_382': retracement_382,
        'level_0_5': retracement_500,
        'level_0_618': retracement_618,
        'level_0_786': retracement_786,
        'level_1_0': period_high,
        # Extensions (beyond low)
        'level_1_236': extension_236,
        'level_1_382': extension_382,
    }


class FibonacciLevels:
    """
    Class-based Fibonacci indicator for compatibility with indicator_base
    """
    
    def __init__(self, lookback_period=20):
        """
        Initialize Fibonacci indicator
        
        Args:
            lookback_period: Number of bars to analyze
        """
        self.lookback_period = lookback_period
        self.name = f"Fibonacci_{lookback_period}"
    
    def calculate(self, data):
        """
        Calculate Fibonacci levels
        
        Args:
            data: DataFrame with OHLCV
            
        Returns:
            dict with Fibonacci levels
        """
        return calculate_fibonacci_levels(data, self.lookback_period)
    
    def get_levels_array(self, data):
        """
        Get all Fibonacci levels as array for vectorized operations
        
        Args:
            data: DataFrame
            
        Returns:
            numpy array of shape (len(data), 11) with all levels
        """
        levels = []
        for i in range(len(data)):
            window = data.iloc[:i+1]
            fib_levels = calculate_fibonacci_levels(window, self.lookback_period)
            levels.append([
                fib_levels['level_0_0'],
                fib_levels['level_0_236'],
                fib_levels['level_0_382'],
                fib_levels['level_0_5'],
                fib_levels['level_0_618'],
                fib_levels['level_0_786'],
                fib_levels['level_1_0'],
                fib_levels['level_1_236'],
                fib_levels['level_1_382'],
                fib_levels['high'],
                fib_levels['low'],
            ])
        
        return np.array(levels)
