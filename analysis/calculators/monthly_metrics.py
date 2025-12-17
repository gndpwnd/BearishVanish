# ============================================================================
# FILE 8: calculators/monthly_metrics.py
# ============================================================================

"""
Monthly Metrics Calculator
Calculate monthly returns and statistics
"""

from .base_calculator import BaseCalculator
import pandas as pd


class MonthlyMetricsCalculator(BaseCalculator):
    """Calculate monthly performance metrics"""
    
    def calculate(self):
        """
        Calculate monthly returns
        
        Returns:
            dict: {year_month: {return_pct, num_trades, win_rate_pct}}
        """
        if self.portfolio.empty:
            return {}
        
        # Set date as index
        portfolio = self.portfolio.set_index('date')
        
        # Calculate daily returns
        returns_series = portfolio['portfolio_value'].pct_change()
        
        # Group by month and calculate monthly returns (pandas version compatible)
        try:
            # Try newer pandas (2.0+) which uses 'ME' for month end
            monthly_returns = returns_series.groupby(pd.Grouper(freq='ME')).apply(
                lambda x: (1 + x).prod() - 1
            ) * 100
        except ValueError:
            # Fallback for older pandas which uses 'M'
            monthly_returns = returns_series.groupby(pd.Grouper(freq='M')).apply(
                lambda x: (1 + x).prod() - 1
            ) * 100
        
        monthly_returns = monthly_returns.dropna()
        
        # Get trade counts per month
        if not self.closed_trades.empty:
            self.closed_trades['entry_date'] = pd.to_datetime(self.closed_trades['entry_date'])
            try:
                trades_by_month = self.closed_trades.set_index('entry_date').groupby(pd.Grouper(freq='ME'))
            except ValueError:
                trades_by_month = self.closed_trades.set_index('entry_date').groupby(pd.Grouper(freq='M'))
        else:
            trades_by_month = None
        
        # Build result dictionary
        result = {}
        
        for date, return_pct in monthly_returns.items():
            year_month = date.strftime('%Y-%m')
            
            # Get trades for this month
            if trades_by_month is not None:
                try:
                    month_trades = trades_by_month.get_group(date)
                    num_trades = len(month_trades)
                    
                    # Calculate win rate for month
                    wins = month_trades[month_trades['profit_loss_dollars'] > 0]
                    win_rate = (len(wins) / num_trades * 100) if num_trades > 0 else 0
                except KeyError:
                    num_trades = 0
                    win_rate = 0
            else:
                num_trades = 0
                win_rate = 0
            
            result[year_month] = {
                'return_pct': return_pct,
                'num_trades': num_trades,
                'win_rate_pct': win_rate
            }
        
        return result