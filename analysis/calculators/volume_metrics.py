# ============================================================================
# FILE 9: calculators/volume_metrics.py
# ============================================================================

"""
Volume Metrics Calculator
Analyze volume patterns in trades
"""

from .base_calculator import BaseCalculator
import pandas as pd
import numpy as np


class VolumeMetricsCalculator(BaseCalculator):
    """Calculate volume-based metrics"""
    
    def calculate(self):
        """
        Calculate volume metrics
        
        Returns:
            dict: Volume statistics
        """
        if self.closed_trades.empty:
            return self._empty_metrics()
        
        # Check if volume data exists
        if 'entry_relative_volume' not in self.closed_trades.columns:
            return self._empty_metrics()
        
        # Filter trades with volume data
        valid_trades = self.closed_trades[
            self.closed_trades['entry_relative_volume'].notna()
        ]
        
        if valid_trades.empty:
            return self._empty_metrics()
        
        # Categorize by volume
        high_vol = valid_trades[valid_trades['entry_relative_volume'] > 2.0]
        low_vol = valid_trades[valid_trades['entry_relative_volume'] < 1.0]
        
        # Calculate win rates
        high_vol_wins = high_vol[high_vol['profit_loss_dollars'] > 0]
        low_vol_wins = low_vol[low_vol['profit_loss_dollars'] > 0]
        
        high_vol_win_rate = (len(high_vol_wins) / len(high_vol) * 100) if len(high_vol) > 0 else 0
        low_vol_win_rate = (len(low_vol_wins) / len(low_vol) * 100) if len(low_vol) > 0 else 0
        
        metrics = {
            'trades_with_volume_data': len(valid_trades),
            'avg_entry_volume_ratio': valid_trades['entry_relative_volume'].mean(),
            'avg_exit_volume_ratio': valid_trades['exit_relative_volume'].mean() 
                if 'exit_relative_volume' in valid_trades.columns 
                else 0,
            'high_volume_trades': len(high_vol),
            'low_volume_trades': len(low_vol),
            'high_vol_win_rate': high_vol_win_rate,
            'low_vol_win_rate': low_vol_win_rate,
        }
        
        return metrics
    
    def _empty_metrics(self):
        """Return empty metrics structure"""
        return {
            'trades_with_volume_data': 0,
            'avg_entry_volume_ratio': 0,
            'avg_exit_volume_ratio': 0,
            'high_volume_trades': 0,
            'low_volume_trades': 0,
            'high_vol_win_rate': 0,
            'low_vol_win_rate': 0,
        }
