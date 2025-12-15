# ============================================================================
# FILE 4: calculators/risk_metrics.py
# ============================================================================

"""
Risk Metrics Calculator
Sharpe, Sortino, VaR, CVaR, volatility, etc.
"""

from .base_calculator import BaseCalculator
import numpy as np
import pandas as pd


class RiskMetricsCalculator(BaseCalculator):
    """Calculate comprehensive risk metrics"""
    
    def calculate(self):
        """
        Calculate all risk metrics
        
        Returns:
            dict: Complete risk statistics
        """
        returns = self.get_returns_series()
        
        if returns.empty:
            return self._empty_metrics()
        
        metrics = {
            # Volatility
            'volatility_annual_pct': self._annualized_volatility(returns),
            'downside_deviation_pct': self._downside_deviation(returns),
            
            # Risk-adjusted returns
            'sharpe_ratio': self._sharpe_ratio(returns),
            'sortino_ratio': self._sortino_ratio(returns),
            'calmar_ratio': self._calmar_ratio(),
            'omega_ratio': self._omega_ratio(returns),
            'treynor_ratio': self._treynor_ratio(returns),
            
            # Value at Risk
            'var_95_pct': self._value_at_risk(returns, 0.95),
            'var_99_pct': self._value_at_risk(returns, 0.99),
            'cvar_95_pct': self._conditional_var(returns, 0.95),
            'cvar_99_pct': self._conditional_var(returns, 0.99),
            
            # Market exposure (if benchmark available)
            'beta': self._calculate_beta(),
            'alpha_pct': self._calculate_alpha(),
            'correlation': self._calculate_correlation(),
            'information_ratio': self._information_ratio(),
            
            # Distribution metrics
            'skewness': returns.skew(),
            'kurtosis': returns.kurtosis(),
        }
        
        return metrics
    
    def _annualized_volatility(self, returns):
        """Calculate annualized volatility"""
        return returns.std() * np.sqrt(252 * 6.5) * 100
    
    def _downside_deviation(self, returns, target=0.0):
        """Calculate downside deviation (semi-deviation)"""
        downside = returns[returns < target]
        if len(downside) == 0:
            return 0
        return np.sqrt(np.mean(downside ** 2)) * np.sqrt(252 * 6.5) * 100
    
    def _sharpe_ratio(self, returns, risk_free_rate=0.0):
        """Calculate Sharpe ratio"""
        excess_returns = returns - (risk_free_rate / 252 / 6.5)
        if excess_returns.std() == 0:
            return 0
        sharpe = excess_returns.mean() / excess_returns.std()
        return sharpe * np.sqrt(252 * 6.5)
    
    def _sortino_ratio(self, returns, target_return=0.0):
        """Calculate Sortino ratio"""
        excess_returns = returns - (target_return / 252 / 6.5)
        downside_dev = self._downside_deviation(returns, target_return) / 100
        
        if downside_dev == 0:
            return 0
        
        sortino = excess_returns.mean() / downside_dev
        return sortino * np.sqrt(252 * 6.5)
    
    def _calmar_ratio(self):
        """Calculate Calmar ratio"""
        if not self.performance:
            return 0
        
        total_return = self.performance.get('total_return_pct', 0)
        max_dd = self.performance.get('max_drawdown_pct', 0)
        
        if max_dd == 0:
            return 0
        
        # Annualize return
        days = self.get_trading_days()
        if days == 0:
            return 0
        
        annual_return = (total_return / 100 + 1) ** (252 / days) - 1
        annual_return *= 100
        
        return annual_return / max_dd
    
    def _omega_ratio(self, returns, threshold=0.0):
        """Calculate Omega ratio"""
        gains = returns[returns > threshold]
        losses = returns[returns <= threshold]
        
        if len(losses) == 0:
            return float('inf')
        
        gain_sum = gains.sum() if len(gains) > 0 else 0
        loss_sum = abs(losses.sum())
        
        if loss_sum == 0:
            return float('inf')
        
        return gain_sum / loss_sum
    
    def _value_at_risk(self, returns, confidence=0.95):
        """Calculate Value at Risk"""
        return abs(np.percentile(returns, (1 - confidence) * 100)) * 100
    
    def _conditional_var(self, returns, confidence=0.95):
        """Calculate Conditional VaR (Expected Shortfall)"""
        var_threshold = np.percentile(returns, (1 - confidence) * 100)
        tail_losses = returns[returns <= var_threshold]
        
        if len(tail_losses) == 0:
            return 0
        
        return abs(tail_losses.mean()) * 100
    
    def _calculate_beta(self):
        """Calculate beta vs benchmark"""
        benchmark_portfolio = self.reader.get_portfolio_history('SPY')
        if benchmark_portfolio.empty:
            return None
        
        benchmark_returns = benchmark_portfolio['portfolio_value'].pct_change().dropna()
        
        # Align returns
        returns = self.get_returns_series()
        min_len = min(len(returns), len(benchmark_returns))
        
        if min_len < 2:
            return None
        
        port_rets = returns.iloc[-min_len:]
        bench_rets = benchmark_returns.iloc[-min_len:]
        
        if bench_rets.var() == 0:
            return None
        
        covariance = port_rets.cov(bench_rets)
        bench_variance = bench_rets.var()
        
        return covariance / bench_variance
    
    def _calculate_alpha(self):
        """Calculate Jensen's alpha"""
        beta = self._calculate_beta()
        if beta is None or not self.performance:
            return None
        
        portfolio_return = self.performance.get('total_return_pct', 0)
        
        benchmark_perf = self.reader.get_strategy_performance('SPY')
        if not benchmark_perf:
            return None
        
        bench_return = benchmark_perf.get('total_return_pct', 0)
        risk_free = 0.0
        
        alpha = portfolio_return - (risk_free + beta * (bench_return - risk_free))
        return alpha
    
    def _calculate_correlation(self):
        """Calculate correlation with benchmark"""
        benchmark_portfolio = self.reader.get_portfolio_history('SPY')
        if benchmark_portfolio.empty:
            return None
        
        benchmark_returns = benchmark_portfolio['portfolio_value'].pct_change().dropna()
        returns = self.get_returns_series()
        
        min_len = min(len(returns), len(benchmark_returns))
        if min_len < 2:
            return None
        
        return returns.iloc[-min_len:].corr(benchmark_returns.iloc[-min_len:])
    
    def _information_ratio(self):
        """Calculate information ratio"""
        benchmark_portfolio = self.reader.get_portfolio_history('SPY')
        if benchmark_portfolio.empty:
            return None
        
        benchmark_returns = benchmark_portfolio['portfolio_value'].pct_change().dropna()
        returns = self.get_returns_series()
        
        min_len = min(len(returns), len(benchmark_returns))
        if min_len < 2:
            return None
        
        port_rets = returns.iloc[-min_len:]
        bench_rets = benchmark_returns.iloc[-min_len:]
        
        excess_returns = port_rets - bench_rets
        tracking_error = excess_returns.std()
        
        if tracking_error == 0:
            return None
        
        ir = excess_returns.mean() / tracking_error
        return ir * np.sqrt(252 * 6.5)
    
    def _treynor_ratio(self, returns):
        """Calculate Treynor ratio"""
        beta = self._calculate_beta()
        if beta is None or beta == 0:
            return None
        
        excess_returns = returns - (0.0 / 252 / 6.5)  # risk_free = 0
        treynor = excess_returns.mean() / beta
        return treynor * (252 * 6.5)
    
    def _empty_metrics(self):
        """Return empty metrics structure"""
        return {
            'volatility_annual_pct': 0,
            'downside_deviation_pct': 0,
            'sharpe_ratio': 0,
            'sortino_ratio': 0,
            'calmar_ratio': 0,
            'omega_ratio': 0,
            'treynor_ratio': None,
            'var_95_pct': 0,
            'var_99_pct': 0,
            'cvar_95_pct': 0,
            'cvar_99_pct': 0,
            'beta': None,
            'alpha_pct': None,
            'correlation': None,
            'information_ratio': None,
            'skewness': 0,
            'kurtosis': 0,
        }