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
        # For charts, use ALL trades (including open positions) for better visualization
        self.all_trades = self.reader.get_trade_history(strategy_name)
        # Also keep closed trades for backward compatibility
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
            charts['monthly_heatmap'] = self._process_monthly_heatmap()
        
        # Use closed trades for histogram (requires exit prices)
        if not self.closed_trades.empty:
            charts['returns_histogram'] = self._process_returns_histogram()
        
        # Use ALL trades for return scatter and cumulative PnL (including open positions)
        if not self.all_trades.empty:
            charts['returns_scatter'] = self._process_returns_scatter()
            charts['cumulative_pnl'] = self._process_cumulative_pnl()
        
        return charts
    
    def _process_equity_curve(self):
        """Pre-compute aggregated equity curve data with trend line"""
        if self.portfolio.empty:
            return {'dates': [], 'values': [], 'trend': []}
        
        # Resample to weekly data to reduce points
        df = self.portfolio.set_index('date').copy()
        weekly = df['portfolio_value'].resample('W').last()
        
        # Keep first and last point always
        first_date = self.portfolio['date'].iloc[0]
        last_date = self.portfolio['date'].iloc[-1]
        
        dates = [first_date.strftime('%Y-%m-%d')]
        values = [self.portfolio['portfolio_value'].iloc[0]]
        
        # Add weekly points
        for date, value in weekly.items():
            if date > first_date and date < last_date:
                dates.append(date.strftime('%Y-%m-%d'))
                values.append(float(value))
        
        # Add last point
        dates.append(last_date.strftime('%Y-%m-%d'))
        values.append(float(self.portfolio['portfolio_value'].iloc[-1]))
        
        # Calculate simple trend line (polynomial fit for visualization)
        x = np.arange(len(values))
        z = np.polyfit(x, values, 2)  # 2nd degree polynomial
        p = np.poly1d(z)
        trend = p(x).tolist()
        
        return {
            'dates': dates,
            'values': values,
            'trend': trend,
            'initial_cash': float(self.reader.get_initial_cash()),
            'min_value': float(min(values)),
            'max_value': float(max(values)),
        }
    
    def _process_drawdown_curve(self):
        """Pre-compute drawdown curve with heatmap coloring"""
        if self.portfolio.empty:
            return {'dates': [], 'drawdowns': []}
        
        values = self.portfolio['portfolio_value'].values
        running_max = np.maximum.accumulate(values)
        drawdowns = (values - running_max) / running_max * 100
        
        # Resample drawdowns to daily/weekly
        df = self.portfolio.set_index('date').copy()
        df['drawdown'] = drawdowns
        daily_dd = df['drawdown'].resample('D').last()
        
        dates = [d.strftime('%Y-%m-%d') for d in daily_dd.index]
        drawdown_values = daily_dd.values.tolist()
        
        # Generate heatmap data: color intensity based on drawdown severity
        colors = []
        for dd in drawdown_values:
            if dd == 0:
                colors.append('#66BB6A')  # Green
            elif dd > -5:
                colors.append('#FDD835')  # Yellow
            elif dd > -10:
                colors.append('#FB8C00')  # Orange
            else:
                colors.append('#EF5350')  # Red
        
        return {
            'dates': dates,
            'drawdowns': drawdown_values,
            'colors': colors,
            'max_drawdown': float(np.min(drawdown_values)) if len(drawdown_values) > 0 else 0,
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
        """Pre-compute aggregated returns distribution for all trades"""
        if 'profit_loss_pct' not in self.all_trades.columns:
            return {}
        
        returns = self.all_trades['profit_loss_pct'].dropna().values
        
        if len(returns) == 0:
            return {}
        
        # Aggregate returns into bins instead of individual points
        # This dramatically reduces data size
        num_bins = min(50, len(returns) // 10 + 1)  # Max 50 bins
        cumulative = np.cumsum(returns)
        
        # Resample cumulative returns by taking every Nth point
        sample_rate = max(1, len(cumulative) // num_bins)
        sample_indices = list(range(0, len(cumulative), sample_rate)) + [len(cumulative) - 1]
        sample_indices = list(dict.fromkeys(sample_indices))  # Remove duplicates
        
        sampled_trades = [i + 1 for i in sample_indices]
        sampled_cumulative = cumulative[sample_indices].tolist()
        sampled_returns = returns[sample_indices].tolist()
        
        # Color by positive/negative
        colors = ['#66BB6A' if r > 0 else '#EF5350' for r in sampled_returns]
        
        return {
            'trade_numbers': sampled_trades,
            'returns': sampled_returns,
            'cumulative': sampled_cumulative,
            'colors': colors,
            'total_trades': len(returns),
            'total_cumulative_return': float(cumulative[-1]) if len(cumulative) > 0 else 0,
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
        """Pre-compute aggregated cumulative P&L with trend for all trades"""
        if 'profit_loss_dollars' not in self.all_trades.columns:
            return {}
        
        pnl = self.all_trades['profit_loss_dollars'].values
        
        if len(pnl) == 0:
            return {}
        
        cumulative = np.cumsum(pnl)
        
        # Resample to reduce data points - max 100 points
        num_bins = min(100, len(cumulative) // 5 + 1)
        sample_rate = max(1, len(cumulative) // num_bins)
        sample_indices = list(range(0, len(cumulative), sample_rate)) + [len(cumulative) - 1]
        sample_indices = list(dict.fromkeys(sample_indices))
        
        sampled_cumulative = cumulative[sample_indices].tolist()
        sampled_trades = [i + 1 for i in sample_indices]
        
        # Get dates safely (prefer exit_date for closed trades, fall back to entry_date)
        dates = []
        try:
            dates = []
            for i in sample_indices:
                if i < len(self.all_trades):
                    try:
                        exit_date = self.all_trades['exit_date'].iloc[i]
                        if pd.notna(exit_date):
                            dates.append(exit_date.strftime('%Y-%m-%d'))
                        else:
                            entry_date = self.all_trades['entry_date'].iloc[i]
                            dates.append(entry_date.strftime('%Y-%m-%d'))
                    except:
                        dates.append(str(i))
        except Exception:
            dates = [str(i) for i in sampled_trades]
        
        # Calculate trend line
        x = np.arange(len(sampled_cumulative))
        if len(x) > 2:
            try:
                z = np.polyfit(x, sampled_cumulative, 2)
                p = np.poly1d(z)
                trend = p(x).tolist()
                # Replace NaN and Inf with None for JSON serialization
                trend = [v if (not np.isnan(v) and not np.isinf(v)) else None for v in trend]
            except Exception:
                trend = sampled_cumulative
        else:
            trend = sampled_cumulative
        
        return {
            'dates': dates,
            'cumulative_pnl': sampled_cumulative,
            'trend': trend,
            'trade_numbers': sampled_trades,
            'total_pnl': float(cumulative[-1]) if len(cumulative) > 0 else 0,
        }
