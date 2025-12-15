"""
Portfolio Risk Analyzer - REFACTORED FOR DATABASE
NO MockTracker dependency - works directly with SimulationReader

Analyze risk across multiple strategies combined as a portfolio
"""

import numpy as np
import pandas as pd
from risk_analysis import RiskAnalyzerDB


class PortfolioRiskAnalyzerDB:
    """
    Analyze risk at portfolio level (multiple strategies combined)
    Works directly with SimulationReader - NO mock objects
    """
    
    def __init__(self, reader, strategy_names, benchmark='SPY', weights=None):
        """
        Initialize portfolio analyzer
        
        Args:
            reader: SimulationReader instance
            strategy_names: List of strategy names to combine
            benchmark: Benchmark strategy name (default: 'SPY')
            weights: Dict of {strategy_name: weight} (default: equal weight)
        """
        self.reader = reader
        self.strategy_names = strategy_names
        self.benchmark = benchmark
        
        # Default to equal weighting
        if weights is None:
            n = len(strategy_names)
            self.weights = {name: 1.0/n for name in strategy_names}
        else:
            # Normalize weights
            total = sum(weights.values())
            self.weights = {k: v/total for k, v in weights.items()}
        
        # Load data
        self._load_data()
    
    def _load_data(self):
        """Load portfolio histories for all strategies"""
        self.portfolios = {}
        self.returns_series = {}
        
        for strategy in self.strategy_names:
            portfolio = self.reader.get_portfolio_history(strategy)
            if not portfolio.empty:
                self.portfolios[strategy] = portfolio
                self.returns_series[strategy] = portfolio['portfolio_value'].pct_change().dropna()
        
        # Calculate combined portfolio
        self._calculate_combined_portfolio()
        
        # Load benchmark
        benchmark_portfolio = self.reader.get_portfolio_history(self.benchmark)
        if not benchmark_portfolio.empty:
            self.benchmark_returns = benchmark_portfolio['portfolio_value'].pct_change().dropna()
        else:
            self.benchmark_returns = None
    
    def _calculate_combined_portfolio(self):
        """Calculate combined portfolio value over time"""
        if not self.portfolios:
            self.combined_portfolio = pd.Series()
            self.combined_returns = pd.Series()
            return
        
        # Get common dates (intersection of all portfolio dates)
        all_dates = None
        for portfolio in self.portfolios.values():
            dates = set(portfolio['date'])
            if all_dates is None:
                all_dates = dates
            else:
                all_dates = all_dates.intersection(dates)
        
        if not all_dates:
            self.combined_portfolio = pd.Series()
            self.combined_returns = pd.Series()
            return
        
        all_dates = sorted(all_dates)
        
        # Calculate weighted portfolio values
        combined_values = []
        
        for date in all_dates:
            weighted_value = 0
            for strategy, weight in self.weights.items():
                if strategy in self.portfolios:
                    portfolio = self.portfolios[strategy]
                    value_at_date = portfolio[portfolio['date'] == date]['portfolio_value'].values
                    if len(value_at_date) > 0:
                        weighted_value += value_at_date[0] * weight
            
            combined_values.append(weighted_value)
        
        self.combined_portfolio = pd.Series(combined_values, index=all_dates)
        self.combined_returns = self.combined_portfolio.pct_change().dropna()
    
    # ============================================================
    # PORTFOLIO-LEVEL METRICS
    # ============================================================
    
    def get_portfolio_return(self):
        """Calculate portfolio-level return"""
        if len(self.combined_portfolio) == 0:
            return 0.0
        
        initial = self.combined_portfolio.iloc[0]
        final = self.combined_portfolio.iloc[-1]
        
        return (final - initial) / initial * 100
    
    def get_portfolio_volatility(self, annualize=True):
        """Calculate portfolio-level volatility"""
        if len(self.combined_returns) == 0:
            return 0.0
        
        vol = self.combined_returns.std()
        
        if annualize:
            vol *= np.sqrt(252 * 6.5)
        
        return vol * 100
    
    def get_portfolio_sharpe(self, risk_free_rate=0.0):
        """Calculate portfolio Sharpe ratio"""
        if len(self.combined_returns) == 0:
            return 0.0
        
        excess_returns = self.combined_returns - (risk_free_rate / 252 / 6.5)
        
        if excess_returns.std() == 0:
            return 0.0
        
        sharpe = excess_returns.mean() / excess_returns.std()
        sharpe *= np.sqrt(252 * 6.5)
        
        return sharpe
    
    def get_portfolio_max_drawdown(self):
        """Calculate portfolio max drawdown"""
        if len(self.combined_portfolio) == 0:
            return 0.0
        
        values = self.combined_portfolio.values
        running_max = np.maximum.accumulate(values)
        drawdowns = (values - running_max) / running_max * 100
        
        return abs(np.min(drawdowns))
    
    # ============================================================
    # DIVERSIFICATION ANALYSIS
    # ============================================================
    
    def get_diversification_benefit(self):
        """
        Calculate diversification benefit
        
        Returns:
            float: Reduction in volatility due to diversification (%)
        """
        # Portfolio volatility
        portfolio_vol = self.get_portfolio_volatility()
        
        # Weighted average of individual volatilities
        weighted_vol = 0
        for strategy, weight in self.weights.items():
            if strategy in self.returns_series:
                returns = self.returns_series[strategy]
                if len(returns) > 0:
                    vol = returns.std() * np.sqrt(252 * 6.5) * 100
                    weighted_vol += vol * weight
        
        # Diversification benefit = reduction in volatility
        if weighted_vol == 0:
            return 0.0
        
        benefit = (weighted_vol - portfolio_vol) / weighted_vol * 100
        
        return benefit
    
    def get_correlation_matrix(self):
        """
        Calculate correlation matrix between strategies
        
        Returns:
            pd.DataFrame: Correlation matrix
        """
        if not self.returns_series:
            return pd.DataFrame()
        
        # Create DataFrame of returns
        returns_dict = {}
        for strategy, returns in self.returns_series.items():
            returns_dict[strategy] = returns
        
        returns_df = pd.DataFrame(returns_dict)
        
        # Calculate correlation
        corr_matrix = returns_df.corr()
        
        return corr_matrix
    
    def get_contribution_to_risk(self):
        """
        Calculate each strategy's contribution to portfolio risk
        
        Returns:
            dict: {strategy_name: risk_contribution_pct}
        """
        if len(self.combined_returns) == 0:
            return {}
        
        portfolio_var = self.combined_returns.var()
        
        contributions = {}
        
        for strategy, weight in self.weights.items():
            if strategy not in self.returns_series:
                contributions[strategy] = 0.0
                continue
            
            strategy_returns = self.returns_series[strategy]
            
            # Align with portfolio returns
            min_len = min(len(strategy_returns), len(self.combined_returns))
            strategy_rets = strategy_returns.iloc[-min_len:]
            portfolio_rets = self.combined_returns.iloc[-min_len:]
            
            # Covariance with portfolio
            cov = strategy_rets.cov(portfolio_rets)
            
            # Marginal contribution to risk
            marginal_contribution = weight * cov / portfolio_var if portfolio_var > 0 else 0
            
            contributions[strategy] = marginal_contribution * 100
        
        return contributions
    
    # ============================================================
    # CORRELATION ANALYSIS
    # ============================================================
    
    def analyze_strategy_correlations(self):
        """
        Analyze correlations and identify redundant strategies
        
        Returns:
            dict: Correlation analysis results
        """
        corr_matrix = self.get_correlation_matrix()
        
        if corr_matrix.empty:
            return {}
        
        # Find highly correlated pairs
        high_corr_pairs = []
        
        strategies = list(corr_matrix.columns)
        for i in range(len(strategies)):
            for j in range(i+1, len(strategies)):
                corr = corr_matrix.iloc[i, j]
                if abs(corr) > 0.8:  # High correlation threshold
                    high_corr_pairs.append({
                        'strategy1': strategies[i],
                        'strategy2': strategies[j],
                        'correlation': corr
                    })
        
        # Calculate average correlation
        upper_triangle = np.triu_indices_from(corr_matrix.values, k=1)
        avg_corr = corr_matrix.values[upper_triangle].mean()
        
        return {
            'correlation_matrix': corr_matrix,
            'average_correlation': avg_corr,
            'high_correlation_pairs': high_corr_pairs,
            'diversification_score': (1 - avg_corr) * 100  # Higher = more diversified
        }
    
    # ============================================================
    # INDIVIDUAL STRATEGY ANALYSIS
    # ============================================================
    
    def get_individual_strategy_metrics(self):
        """Get key metrics for each individual strategy"""
        metrics = {}
        
        for strategy in self.strategy_names:
            perf = self.reader.get_strategy_performance(strategy)
            
            if perf:
                metrics[strategy] = {
                    'return_pct': perf.get('total_return_pct', 0),
                    'sharpe_ratio': perf.get('sharpe_ratio', 0),
                    'max_drawdown_pct': perf.get('max_drawdown_pct', 0),
                    'win_rate_pct': perf.get('win_rate_pct', 0),
                    'profit_factor': perf.get('profit_factor', 0),
                    'weight': self.weights.get(strategy, 0)
                }
        
        return metrics
    
    # ============================================================
    # REPORTING
    # ============================================================
    
    def generate_report(self):
        """Generate comprehensive portfolio risk report"""
        individual_metrics = self.get_individual_strategy_metrics()
        correlation_analysis = self.analyze_strategy_correlations()
        risk_contributions = self.get_contribution_to_risk()
        
        report = {
            'portfolio_metrics': {
                'return_pct': self.get_portfolio_return(),
                'volatility_pct': self.get_portfolio_volatility(),
                'sharpe_ratio': self.get_portfolio_sharpe(),
                'max_drawdown_pct': self.get_portfolio_max_drawdown(),
                'diversification_benefit_pct': self.get_diversification_benefit()
            },
            'strategy_weights': self.weights,
            'individual_strategy_metrics': individual_metrics,
            'correlation_analysis': correlation_analysis,
            'risk_contributions': risk_contributions
        }
        
        return report
    
    def print_report(self):
        """Print comprehensive portfolio-level report"""
        report = self.generate_report()
        
        print("\n" + "="*70)
        print("PORTFOLIO-LEVEL RISK ANALYSIS")
        print("="*70)
        
        # Overall Performance
        portfolio = report['portfolio_metrics']
        print(f"\n📊 PORTFOLIO PERFORMANCE:")
        print(f"   Total Return: {portfolio['return_pct']:+.2f}%")
        print(f"   Portfolio Volatility: {portfolio['volatility_pct']:.2f}%")
        print(f"   Portfolio Sharpe Ratio: {portfolio['sharpe_ratio']:.3f}")
        print(f"   Max Drawdown: {portfolio['max_drawdown_pct']:.2f}%")
        print(f"   Diversification Benefit: {portfolio['diversification_benefit_pct']:.2f}%")
        
        # Strategy Weights
        print(f"\n⚖️ STRATEGY WEIGHTS:")
        for name, weight in report['strategy_weights'].items():
            print(f"   {name}: {weight*100:.1f}%")
        
        # Risk Contributions
        print(f"\n🎯 RISK CONTRIBUTIONS:")
        risk_contrib = report['risk_contributions']
        for name, contrib in sorted(risk_contrib.items(), key=lambda x: x[1], reverse=True):
            print(f"   {name}: {contrib:.1f}%")
        
        # Correlation Analysis
        corr_analysis = report['correlation_analysis']
        print(f"\n🔗 CORRELATION ANALYSIS:")
        print(f"   Average Correlation: {corr_analysis['average_correlation']:.3f}")
        print(f"   Diversification Score: {corr_analysis['diversification_score']:.1f}/100")
        
        if corr_analysis['high_correlation_pairs']:
            print(f"\n   ⚠️ HIGH CORRELATION PAIRS:")
            for pair in corr_analysis['high_correlation_pairs']:
                print(f"      {pair['strategy1']} ↔ {pair['strategy2']}: {pair['correlation']:.3f}")
        
        # Individual Strategy Performance
        print(f"\n📈 INDIVIDUAL STRATEGY PERFORMANCE:")
        print(f"   {'Strategy':<25} {'Return %':<12} {'Sharpe':<10} {'Max DD %':<12} {'Weight':<10}")
        print(f"   {'-'*75}")
        
        individual = report['individual_strategy_metrics']
        for name, metrics in sorted(individual.items(), 
                                   key=lambda x: x[1]['return_pct'], 
                                   reverse=True):
            print(f"   {name:<25} "
                  f"{metrics['return_pct']:>10.2f}% "
                  f"{metrics['sharpe_ratio']:>10.3f} "
                  f"{metrics['max_drawdown_pct']:>10.2f}% "
                  f"{metrics['weight']*100:>8.1f}%")
        
        print("\n" + "="*70 + "\n")


# ============================================================
# CONVENIENCE FUNCTIONS
# ============================================================

def analyze_portfolio_risk(reader, strategy_names, benchmark='SPY', weights=None):
    """
    Convenience function to analyze portfolio risk
    
    Args:
        reader: SimulationReader instance
        strategy_names: List of strategy names OR dict of {name: weight}
        benchmark: Benchmark strategy (default: 'SPY')
        weights: Optional custom weights
    
    Usage:
        # Equal weighted
        analyzer = analyze_portfolio_risk(reader, ['Strat1', 'Strat2', 'Strat3'])
        
        # Custom weighted
        analyzer = analyze_portfolio_risk(reader, ['Strat1', 'Strat2'], 
                                         weights={'Strat1': 0.7, 'Strat2': 0.3})
        
        analyzer.print_report()
    """
    # Handle dict input
    if isinstance(strategy_names, dict):
        weights = strategy_names
        strategy_names = list(weights.keys())
    
    analyzer = PortfolioRiskAnalyzerDB(reader, strategy_names, benchmark, weights)
    return analyzer