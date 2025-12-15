# ============================================================================
# FILE 5: calculators/drawdown_metrics.py
# ============================================================================

"""
Drawdown Metrics Calculator
Analyzes drawdown periods and recovery
"""

from .base_calculator import BaseCalculator
import numpy as np
import pandas as pd


class DrawdownMetricsCalculator(BaseCalculator):
    """Calculate drawdown metrics and identify drawdown periods"""
    
    def calculate(self):
        """
        Calculate drawdown metrics
        
        Returns:
            dict: Drawdown statistics
            list: List of significant drawdown periods
        """
        if self.portfolio.empty:
            return {'metrics': self._empty_metrics(), 'periods': []}
        
        values = self.portfolio['portfolio_value'].values
        dates = self.portfolio['date'].values
        
        # Calculate running maximum
        running_max = np.maximum.accumulate(values)
        
        # Calculate drawdown at each point
        drawdowns = (values - running_max) / running_max * 100
        
        # Find maximum drawdown
        max_dd_idx = np.argmin(drawdowns)
        max_dd_pct = abs(drawdowns[max_dd_idx])
        
        # Find peak before max drawdown
        peak_idx = np.argmax(running_max[:max_dd_idx+1])
        
        # Calculate recovery
        recovery_idx = None
        recovery_days = None
        
        for i in range(max_dd_idx, len(values)):
            if values[i] >= values[peak_idx]:
                recovery_idx = i
                recovery_days = i - max_dd_idx
                break
        
        metrics = {
            'max_drawdown_pct': max_dd_pct,
            'max_drawdown_dollars': values[peak_idx] - values[max_dd_idx],
            'avg_drawdown_pct': abs(drawdowns[drawdowns < 0].mean()) if len(drawdowns[drawdowns < 0]) > 0 else 0,
            'current_drawdown_pct': abs(drawdowns[-1]) if drawdowns[-1] < 0 else 0,
            'currently_in_drawdown': drawdowns[-1] < -1,
            'recovery_days_max_dd': recovery_days,
        }
        
        # Identify significant drawdown periods (>5%)
        periods = self._identify_drawdown_periods(values, dates, drawdowns, running_max)
        
        return {'metrics': metrics, 'periods': periods}
    
    def _identify_drawdown_periods(self, values, dates, drawdowns, running_max):
        """Identify significant drawdown periods"""
        periods = []
        
        in_drawdown = False
        dd_start_idx = None
        peak_idx = None
        
        for i in range(len(drawdowns)):
            if not in_drawdown and drawdowns[i] < -5:
                # Start of drawdown
                in_drawdown = True
                peak_idx = np.argmax(running_max[:i+1])
                dd_start_idx = i
            
            elif in_drawdown and drawdowns[i] >= -1:
                # End of drawdown (recovered)
                trough_idx = dd_start_idx + np.argmin(drawdowns[dd_start_idx:i+1])
                
                period = {
                    'peak_date': str(dates[peak_idx]),
                    'trough_date': str(dates[trough_idx]),
                    'recovery_date': str(dates[i]),
                    'drawdown_pct': abs(drawdowns[trough_idx]),
                    'drawdown_dollars': values[peak_idx] - values[trough_idx],
                    'recovery_days': i - trough_idx,
                    'duration_days': i - peak_idx,
                }
                
                periods.append(period)
                in_drawdown = False
        
        # If still in drawdown at end
        if in_drawdown and dd_start_idx is not None:
            trough_idx = dd_start_idx + np.argmin(drawdowns[dd_start_idx:])
            
            period = {
                'peak_date': str(dates[peak_idx]),
                'trough_date': str(dates[trough_idx]),
                'recovery_date': None,
                'drawdown_pct': abs(drawdowns[trough_idx]),
                'drawdown_dollars': values[peak_idx] - values[trough_idx],
                'recovery_days': None,
                'duration_days': len(dates) - peak_idx,
            }
            
            periods.append(period)
        
        # Sort by drawdown magnitude
        periods = sorted(periods, key=lambda x: x['drawdown_pct'], reverse=True)
        
        return periods[:10]  # Return top 10 drawdowns
    
    def _empty_metrics(self):
        """Return empty metrics structure"""
        return {
            'max_drawdown_pct': 0,
            'max_drawdown_dollars': 0,
            'avg_drawdown_pct': 0,
            'current_drawdown_pct': 0,
            'currently_in_drawdown': False,
            'recovery_days_max_dd': None,
        }