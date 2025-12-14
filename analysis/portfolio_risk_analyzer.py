"""
Portfolio-Level Risk Analysis
Analyze risk across multiple strategies combined
"""

import numpy as np
import pandas as pd
from risk_analysis import RiskAnalyzer

class PortfolioRiskAnalyzer:
    """
    Analyze risk at portfolio level (multiple strategies combined)
    """
    
    def __init__(self, strategy_trackers, spy_tracker=None, weights=None):
        """
        Initialize portfolio analyzer
        
        Args:
            strategy_trackers: Dict of {strategy_name: tracker}
            spy_tracker: Benchmark tracker
            weights: Dict of {strategy_name: weight} (default: equal weight)
        """
        self.strategy_trackers = strategy_trackers
        self.spy_tracker = spy_tracker
        
        # Default to equal weighting
        if weights is None:
            n = len(strategy_trackers)
            self.weights = {name: 1.0/n for name in strategy_trackers.keys()}
        else:
            self.weights = weights
        
        # Calculate combined portfolio values
        self.portfolio_values = self._calculate_combined_portfolio()
    
    def _calculate_combined_portfolio(self):
        """
        Calculate combined portfolio value over time
        
        Returns:
            pd.Series: Combined portfolio values
        """
        # Get all dates (assume all trackers have same dates)
        first_tracker = list(self.strategy_trackers.values())[0]
        dates = first_tracker.dates
        
        # Initialize combined portfolio
        combined = pd.Series(0.0, index=dates)
        
        # Weight each strategy's contribution
        for name, tracker in self.strategy_trackers.items():
            weight = self.weights[name]
            values = pd.Series(tracker.portfolio_value_history, index=tracker.dates)
            combined += values * weight
        
        return combined
    
    def get_portfolio_return(self):
        """Calculate portfolio-level return"""
        if len(self.portfolio_values) == 0:
            return 0.0
        
        initial = self.portfolio_values.iloc[0]
        final = self.portfolio_values.iloc[-1]
        
        return (final - initial) / initial * 100
    
    def get_portfolio_volatility(self, annualize=True):
        """Calculate portfolio-level volatility"""
        returns = self.portfolio_values.pct_change().dropna()
        
        if len(returns) == 0:
            return 0.0
        
        vol = returns.std()
        
        if annualize:
            vol *= np.sqrt(252 * 6.5)
        
        return vol * 100
    
    def get_portfolio_sharpe(self, risk_free_rate=0.0):
        """Calculate portfolio Sharpe ratio"""
        returns = self.portfolio_values.pct_change().dropna()
        
        if len(returns) == 0 or returns.std() == 0:
            return 0.0
        
        excess_returns = returns - (risk_free_rate / 252 / 6.5)
        sharpe = excess_returns.mean() / excess_returns.std()
        sharpe *= np.sqrt(252 * 6.5)
        
        return sharpe
    
    def get_diversification_benefit(self):
        """
        Calculate diversification benefit
        
        Returns:
            float: Reduction in volatility due to diversification
        """
        # Portfolio volatility
        portfolio_vol = self.get_portfolio_volatility()
        
        # Weighted average of individual volatilities
        weighted_vol = 0
        for name, tracker in self.strategy_trackers.items():
            returns = pd.Series(tracker.portfolio_value_history).pct_change().dropna()
            if len(returns) > 0:
                vol = returns.std() * np.sqrt(252 * 6.5) * 100
                weighted_vol += vol * self.weights[name]
        
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
        # Collect returns for each strategy
        returns_dict = {}
        
        for name, tracker in self.strategy_trackers.items():
            returns = pd.Series(tracker.portfolio_value_history, 
                              index=tracker.dates).pct_change().dropna()
            returns_dict[name] = returns
        
        # Create DataFrame
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
        # Get portfolio returns
        portfolio_returns = self.portfolio_values.pct_change().dropna()
        portfolio_var = portfolio_returns.var()
        
        contributions = {}
        
        for name, tracker in self.strategy_trackers.items():
            # Strategy returns
            strategy_returns = pd.Series(tracker.portfolio_value_history,
                                        index=tracker.dates).pct_change().dropna()
            
            # Align with portfolio returns
            min_len = min(len(strategy_returns), len(portfolio_returns))
            strategy_rets = strategy_returns.iloc[-min_len:]
            portfolio_rets = portfolio_returns.iloc[-min_len:]
            
            # Covariance with portfolio
            cov = strategy_rets.cov(portfolio_rets)
            
            # Marginal contribution to risk
            weight = self.weights[name]
            marginal_contribution = weight * cov / portfolio_var if portfolio_var > 0 else 0
            
            contributions[name] = marginal_contribution * 100
        
        return contributions
    
    def analyze_strategy_correlations(self):
        """
        Analyze correlations and identify redundant strategies
        
        Returns:
            dict: Correlation analysis results
        """
        corr_matrix = self.get_correlation_matrix()
        
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
        avg_corr = corr_matrix.values[np.triu_indices_from(corr_matrix.values, k=1)].mean()
        
        return {
            'correlation_matrix': corr_matrix,
            'average_correlation': avg_corr,
            'high_correlation_pairs': high_corr_pairs,
            'diversification_score': (1 - avg_corr) * 100  # Higher = more diversified
        }
    
    def print_portfolio_report(self):
        """Print comprehensive portfolio-level report"""
        print("\n" + "="*70)
        print("PORTFOLIO-LEVEL RISK ANALYSIS")
        print("="*70)
        
        # Overall Performance
        print(f"\n📊 PORTFOLIO PERFORMANCE:")
        print(f"   Total Return: {self.get_portfolio_return():+.2f}%")
        print(f"   Portfolio Volatility: {self.get_portfolio_volatility():.2f}%")
        print(f"   Portfolio Sharpe Ratio: {self.get_portfolio_sharpe():.3f}")
        print(f"   Diversification Benefit: {self.get_diversification_benefit():.2f}%")
        
        # Strategy Weights
        print(f"\n⚖️ STRATEGY WEIGHTS:")
        for name, weight in self.weights.items():
            print(f"   {name}: {weight*100:.1f}%")
        
        # Risk Contributions
        print(f"\n🎯 RISK CONTRIBUTIONS:")
        risk_contrib = self.get_contribution_to_risk()
        for name, contrib in sorted(risk_contrib.items(), key=lambda x: x[1], reverse=True):
            print(f"   {name}: {contrib:.1f}%")
        
        # Correlation Analysis
        print(f"\n🔗 CORRELATION ANALYSIS:")
        corr_analysis = self.analyze_strategy_correlations()
        print(f"   Average Correlation: {corr_analysis['average_correlation']:.3f}")
        print(f"   Diversification Score: {corr_analysis['diversification_score']:.1f}/100")
        
        if corr_analysis['high_correlation_pairs']:
            print(f"\n   ⚠️ HIGH CORRELATION PAIRS:")
            for pair in corr_analysis['high_correlation_pairs']:
                print(f"      {pair['strategy1']} ↔ {pair['strategy2']}: {pair['correlation']:.3f}")
        
        # Individual Strategy Performance
        print(f"\n📈 INDIVIDUAL STRATEGY PERFORMANCE:")
        print(f"   {'Strategy':<25} {'Return %':<12} {'Sharpe':<10} {'Max DD %':<12}")
        print(f"   {'-'*60}")
        
        for name, tracker in sorted(self.strategy_trackers.items(), 
                                   key=lambda x: x[1].get_return_pct(), 
                                   reverse=True):
            ret = tracker.get_return_pct()
            analyzer = RiskAnalyzer(tracker, self.spy_tracker)
            sharpe = analyzer.get_sharpe_ratio()
            max_dd = tracker.get_max_drawdown()
            
            print(f"   {name:<25} {ret:>10.2f}% {sharpe:>10.3f} {max_dd:>10.2f}%")
        
        print("\n" + "="*70 + "\n")


def analyze_portfolio_risk(strategy_trackers, spy_tracker=None, weights=None):
    """
    Convenience function to analyze portfolio risk
    
    Args:
        strategy_trackers: Dict of {strategy_name: tracker} OR a single StrategyTracker
        spy_tracker: Benchmark tracker (optional)
        weights: Strategy weights (default: equal weight)
    
    Returns:
        PortfolioRiskAnalyzer instance
    """
    # Handle single tracker input
    if isinstance(strategy_trackers, StrategyTracker):
        strategy_trackers = {strategy_trackers.name: strategy_trackers}
    
    # Handle list of trackers
    elif isinstance(strategy_trackers, list):
        trackers_dict = {}
        for tracker in strategy_trackers:
            if isinstance(tracker, StrategyTracker):
                trackers_dict[tracker.name] = tracker
        strategy_trackers = trackers_dict
    
    # If no trackers or empty dict, return None
    if not strategy_trackers:
        print("⚠️  No strategy trackers provided for analysis")
        return None
    
    analyzer = PortfolioRiskAnalyzer(strategy_trackers, spy_tracker, weights)
    analyzer.print_portfolio_report()
    return analyzer