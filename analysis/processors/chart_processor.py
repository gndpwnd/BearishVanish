# ============================================================================
# FILE 10: processors/chart_processor.py
# ============================================================================

"""
Chart Processor
Pre-compute all chart data for instant visualization
"""

import pandas as pd
import numpy as np
import json


class ChartProcessor:
    """
    Process and cache chart data
    Pre-computes all data needed for visualization
    """
    
    def __init__(self, reader, strategy_name):
        """
        Initialize processor
        
        Args:
            reader: SimulationReader instance
            strategy_name: Strategy to process
        """
        self.reader = reader
        self.strategy_name = strategy_name
        
        # Load data
        self.portfolio = self.reader.get_portfolio_history(strategy_name)
        self.closed_trades = self.reader.get_closed_trades(strategy_name)
    
    def process_all(self):
        """
        Process all chart types
        
        Returns:
            dict: {chart_type: chart_data}
        """
        charts = {}
        
        if not self.portfolio.empty:
            charts['equity_curve'] = self._process_equity_curve()
            charts['drawdown_curve'] = self._process_drawdown_curve()
        
        if not self.closed_trades.empty:
            charts['returns_histogram'] = self._process_returns_histogram()
            charts['returns_scatter'] = self._process_returns_scatter()
            charts['monthly_heatmap'] = self._process_monthly_heatmap()
            charts['cumulative_pnl'] = self._process_cumulative_pnl()
        
        return charts
    
    def _process_equity_curve(self):
        """Pre-compute equity curve data"""
        try:
            dates = self.portfolio['date'].dt.strftime('%Y-%m-%d').tolist()
        except Exception:
            dates = []
        
        return {
            'dates': dates,
            'values': self.portfolio['portfolio_value'].tolist(),
            'initial_cash': self.reader.get_initial_cash(),
            'num_positions': self.portfolio['num_positions'].tolist() if 'num_positions' in self.portfolio else [],
        }
    
    def _process_drawdown_curve(self):
        """Pre-compute drawdown curve"""
        values = self.portfolio['portfolio_value'].values
        running_max = np.maximum.accumulate(values)
        drawdowns = (values - running_max) / running_max * 100
        
        try:
            dates = self.portfolio['date'].dt.strftime('%Y-%m-%d').tolist()
        except Exception:
            dates = []
        
        return {
            'dates': dates,
            'drawdowns': drawdowns.tolist(),
        }
    
    def _process_returns_histogram(self):
        """Pre-compute returns histogram"""
        if 'profit_loss_pct' not in self.closed_trades.columns:
            return {}
        
        returns = self.closed_trades['profit_loss_pct'].dropna()
        
        if len(returns) == 0:
            return {}
        
        # Create bins
        bins = np.arange(-20, 25, 2.5)  # 2.5% bins from -20% to +20%
        counts, bin_edges = np.histogram(returns, bins=bins)
        
        # Create bin centers for plotting
        bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
        
        # Color by positive/negative
        colors = ['#EF5350' if b < 0 else '#66BB6A' for b in bin_centers]
        
        return {
            'bin_centers': bin_centers.tolist(),
            'counts': counts.tolist(),
            'colors': colors,
            'mean': returns.mean(),
            'median': returns.median(),
        }
    
    def _process_returns_scatter(self):
        """Pre-compute returns scatter (each trade as point)"""
        if 'profit_loss_pct' not in self.closed_trades.columns:
            return {}
        
        returns = self.closed_trades['profit_loss_pct'].values
        trade_numbers = list(range(1, len(returns) + 1))
        
        # Color by positive/negative
        colors = ['#66BB6A' if r > 0 else '#EF5350' for r in returns]
        
        # Calculate cumulative sum
        cumulative = np.cumsum(returns)
        
        return {
            'trade_numbers': trade_numbers,
            'returns': returns.tolist(),
            'cumulative': cumulative.tolist(),
            'colors': colors,
        }
    
    def _process_monthly_heatmap(self):
        """Pre-compute monthly returns heatmap data"""
        if self.portfolio.empty:
            return {}
        
        # Calculate monthly returns
        portfolio = self.portfolio.set_index('date')
        returns_series = portfolio['portfolio_value'].pct_change()
        
        monthly = returns_series.groupby(pd.Grouper(freq='ME')).apply(
            lambda x: (1 + x).prod() - 1
        ) * 100
        
        monthly = monthly.dropna()
        
        if len(monthly) == 0:
            return {}
        
        # Create matrix (years x months)
        monthly_df = pd.DataFrame({
            'year': monthly.index.year,
            'month': monthly.index.month,
            'return': monthly.values
        })
        
        # Pivot to matrix format
        matrix = monthly_df.pivot(index='year', columns='month', values='return')
        
        return {
            'years': matrix.index.tolist(),
            'months': matrix.columns.tolist(),
            'returns': matrix.values.tolist(),  # NaN for missing months
        }
    
    def _process_cumulative_pnl(self):
        """Pre-compute cumulative P&L"""
        if 'profit_loss_dollars' not in self.closed_trades.columns:
            return {}
        
        pnl = self.closed_trades['profit_loss_dollars'].values
        cumulative = np.cumsum(pnl)
        
        # Get dates safely
        dates = []
        try:
            dates = self.closed_trades['exit_date'].dt.strftime('%Y-%m-%d').tolist()
        except Exception:
            dates = []
        
        return {
            'dates': dates,
            'cumulative_pnl': cumulative.tolist(),
            'trade_numbers': list(range(1, len(pnl) + 1)),
        }