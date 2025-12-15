"""
Risk Analysis Module - REFACTORED FOR DATABASE
NO MockTracker dependency - works directly with SimulationReader

Enterprise-grade risk metrics using only database access
"""

import numpy as np
import pandas as pd
from datetime import datetime


class RiskAnalyzerDB:
    """
    Comprehensive risk analysis for trading strategies
    Works directly with SimulationReader - NO mock objects
    """
    
    def __init__(self, reader, strategy_name, benchmark='SPY', risk_free_rate=0.0):
        """
        Initialize risk analyzer
        
        Args:
            reader: SimulationReader instance
            strategy_name: Strategy to analyze
            benchmark: Benchmark strategy name (default: 'SPY')
            risk_free_rate: Annual risk-free rate (default: 0%)
        """
        self.reader = reader
        self.strategy_name = strategy_name
        self.benchmark = benchmark
        self.risk_free_rate = risk_free_rate
        
        # Load data from database
        self._load_data()
    
    def _load_data(self):
        """Load all necessary data from database"""
        # Get portfolio history for returns calculation
        self.portfolio = self.reader.get_portfolio_history(self.strategy_name)
        
        # Calculate returns series
        if not self.portfolio.empty:
            self.returns = self.portfolio['portfolio_value'].pct_change().dropna()
        else:
            self.returns = pd.Series()
        
        # Get benchmark returns if available
        benchmark_portfolio = self.reader.get_portfolio_history(self.benchmark)
        if not benchmark_portfolio.empty:
            self.benchmark_returns = benchmark_portfolio['portfolio_value'].pct_change().dropna()
        else:
            self.benchmark_returns = None
        
        # Get trade data
        self.all_trades = self.reader.get_trade_history(self.strategy_name)
        self.closed_trades = self.reader.get_closed_trades(self.strategy_name)
        self.open_positions = self.reader.get_open_positions(self.strategy_name)
        
        # Get pre-computed performance metrics
        self.performance = self.reader.get_strategy_performance(self.strategy_name)
    
    # ============================================================
    # BASIC RISK METRICS
    # ============================================================
    
    def get_volatility(self, annualize=True):
        """
        Calculate volatility (standard deviation of returns)
        
        Returns:
            float: Annualized volatility (if annualize=True)
        """
        if len(self.returns) == 0:
            return 0.0
        
        vol = self.returns.std()
        
        if annualize:
            # Annualize: sqrt(252 trading days * 6.5 hours)
            vol *= np.sqrt(252 * 6.5)
        
        return vol * 100  # Return as percentage
    
    def get_downside_deviation(self, target_return=0.0, annualize=True):
        """
        Calculate downside deviation (semi-deviation)
        Only considers returns below target
        """
        if len(self.returns) == 0:
            return 0.0
        
        downside_returns = self.returns[self.returns < target_return]
        
        if len(downside_returns) == 0:
            return 0.0
        
        downside_dev = np.sqrt(np.mean(downside_returns ** 2))
        
        if annualize:
            downside_dev *= np.sqrt(252 * 6.5)
        
        return downside_dev * 100
    
    def get_var(self, confidence=0.95):
        """
        Calculate Value at Risk (VaR)
        Estimated maximum loss at given confidence level
        """
        if len(self.returns) == 0:
            return 0.0
        
        var = np.percentile(self.returns, (1 - confidence) * 100)
        return abs(var) * 100
    
    def get_cvar(self, confidence=0.95):
        """
        Calculate Conditional Value at Risk (CVaR / Expected Shortfall)
        Average loss beyond VaR threshold
        """
        if len(self.returns) == 0:
            return 0.0
        
        var_threshold = np.percentile(self.returns, (1 - confidence) * 100)
        tail_losses = self.returns[self.returns <= var_threshold]
        
        if len(tail_losses) == 0:
            return 0.0
        
        return abs(tail_losses.mean()) * 100
    
    # ============================================================
    # DRAWDOWN ANALYSIS
    # ============================================================
    
    def get_max_drawdown_analysis(self):
        """
        Comprehensive drawdown analysis
        
        Returns:
            dict: Detailed drawdown metrics
        """
        if self.portfolio.empty:
            return {}
        
        values = self.portfolio['portfolio_value'].values
        dates = self.portfolio['date'].values
        
        # Calculate running maximum
        running_max = np.maximum.accumulate(values)
        
        # Calculate drawdown at each point
        drawdowns = (values - running_max) / running_max * 100
        
        # Find maximum drawdown
        max_dd_pct = np.min(drawdowns)
        max_dd_idx = np.argmin(drawdowns)
        
        # Find peak before max drawdown
        peak_idx = np.argmax(running_max[:max_dd_idx+1])
        peak_value = values[peak_idx]
        trough_value = values[max_dd_idx]
        
        # Calculate recovery
        recovery_idx = None
        recovery_days = None
        
        for i in range(max_dd_idx, len(values)):
            if values[i] >= peak_value:
                recovery_idx = i
                recovery_days = (dates[i] - dates[max_dd_idx]).astype('timedelta64[D]').astype(int)
                break
        
        # Calculate average drawdown
        avg_dd = np.mean(drawdowns[drawdowns < 0])
        
        # Count drawdown periods (>1% drawdown)
        in_drawdown = drawdowns < -1
        drawdown_changes = np.diff(in_drawdown.astype(int))
        num_drawdowns = np.sum(drawdown_changes == 1)
        
        return {
            'max_drawdown_pct': abs(max_dd_pct),
            'max_drawdown_dollars': peak_value - trough_value,
            'peak_date': dates[peak_idx],
            'trough_date': dates[max_dd_idx],
            'recovery_date': dates[recovery_idx] if recovery_idx else None,
            'recovery_days': recovery_days,
            'avg_drawdown_pct': abs(avg_dd) if not np.isnan(avg_dd) else 0,
            'num_drawdown_periods': num_drawdowns,
            'currently_in_drawdown': drawdowns[-1] < -1,
            'current_drawdown_pct': abs(drawdowns[-1]) if drawdowns[-1] < 0 else 0
        }
    
    # ============================================================
    # PERFORMANCE RATIOS
    # ============================================================
    
    def get_sharpe_ratio(self, annualize=True):
        """Calculate Sharpe Ratio"""
        if len(self.returns) == 0:
            return 0.0
        
        excess_returns = self.returns - (self.risk_free_rate / 252 / 6.5)
        
        if excess_returns.std() == 0:
            return 0.0
        
        sharpe = excess_returns.mean() / excess_returns.std()
        
        if annualize:
            sharpe *= np.sqrt(252 * 6.5)
        
        return sharpe
    
    def get_sortino_ratio(self, target_return=0.0, annualize=True):
        """Calculate Sortino Ratio (only penalizes downside volatility)"""
        if len(self.returns) == 0:
            return 0.0
        
        excess_returns = self.returns - (target_return / 252 / 6.5)
        downside_dev = self.get_downside_deviation(target_return, annualize=False) / 100
        
        if downside_dev == 0:
            return 0.0
        
        sortino = excess_returns.mean() / downside_dev
        
        if annualize:
            sortino *= np.sqrt(252 * 6.5)
        
        return sortino
    
    def get_calmar_ratio(self):
        """Calculate Calmar Ratio (Annual Return / Max Drawdown)"""
        dd_analysis = self.get_max_drawdown_analysis()
        max_dd = dd_analysis.get('max_drawdown_pct', 0)
        
        if max_dd == 0:
            return 0.0
        
        # Get annualized return
        if not self.performance:
            return 0.0
        
        total_return = self.performance.get('total_return_pct', 0)
        
        # Annualize if needed
        dates = self.portfolio['date']
        if len(dates) > 1:
            days = (dates.iloc[-1] - dates.iloc[0]).days
            annual_return = (total_return / 100 + 1) ** (365 / days) - 1
            annual_return *= 100
        else:
            annual_return = total_return
        
        return annual_return / max_dd
    
    def get_omega_ratio(self, threshold=0.0):
        """Calculate Omega Ratio (probability-weighted gains vs losses)"""
        if len(self.returns) == 0:
            return 0.0
        
        gains = self.returns[self.returns > threshold]
        losses = self.returns[self.returns <= threshold]
        
        if len(losses) == 0:
            return float('inf')
        
        gain_sum = gains.sum() if len(gains) > 0 else 0
        loss_sum = abs(losses.sum())
        
        if loss_sum == 0:
            return float('inf')
        
        return gain_sum / loss_sum
    
    # ============================================================
    # MARKET EXPOSURE & CORRELATION
    # ============================================================
    
    def get_beta(self):
        """Calculate portfolio Beta vs benchmark"""
        if self.benchmark_returns is None or len(self.benchmark_returns) == 0:
            return None
        
        # Align returns
        min_len = min(len(self.returns), len(self.benchmark_returns))
        portfolio_rets = self.returns.iloc[-min_len:]
        bench_rets = self.benchmark_returns.iloc[-min_len:]
        
        if bench_rets.var() == 0:
            return None
        
        covariance = portfolio_rets.cov(bench_rets)
        bench_variance = bench_rets.var()
        
        return covariance / bench_variance
    
    def get_alpha(self, annualize=True):
        """Calculate Jensen's Alpha"""
        beta = self.get_beta()
        if beta is None or not self.performance:
            return None
        
        portfolio_return = self.performance.get('total_return_pct', 0)
        
        # Get benchmark return
        benchmark_perf = self.reader.get_strategy_performance(self.benchmark)
        if not benchmark_perf:
            return None
        
        bench_return = benchmark_perf.get('total_return_pct', 0)
        
        # Alpha = Portfolio Return - (Risk-free + Beta × (Market Return - Risk-free))
        alpha = portfolio_return - (self.risk_free_rate + beta * (bench_return - self.risk_free_rate))
        
        if annualize:
            dates = self.portfolio['date']
            if len(dates) > 1:
                days = (dates.iloc[-1] - dates.iloc[0]).days
                alpha *= (365 / days)
        
        return alpha
    
    def get_correlation(self):
        """Calculate correlation with benchmark"""
        if self.benchmark_returns is None or len(self.benchmark_returns) == 0:
            return None
        
        min_len = min(len(self.returns), len(self.benchmark_returns))
        portfolio_rets = self.returns.iloc[-min_len:]
        bench_rets = self.benchmark_returns.iloc[-min_len:]
        
        return portfolio_rets.corr(bench_rets)
    
    def get_information_ratio(self, annualize=True):
        """Calculate Information Ratio (risk-adjusted excess return vs benchmark)"""
        if self.benchmark_returns is None or len(self.benchmark_returns) == 0:
            return None
        
        min_len = min(len(self.returns), len(self.benchmark_returns))
        portfolio_rets = self.returns.iloc[-min_len:]
        bench_rets = self.benchmark_returns.iloc[-min_len:]
        
        # Excess returns (active returns)
        excess_returns = portfolio_rets - bench_rets
        
        # Tracking error (volatility of excess returns)
        tracking_error = excess_returns.std()
        
        if tracking_error == 0:
            return None
        
        ir = excess_returns.mean() / tracking_error
        
        if annualize:
            ir *= np.sqrt(252 * 6.5)
        
        return ir
    
    def get_treynor_ratio(self, annualize=True):
        """Calculate Treynor Ratio (excess return per unit of systematic risk)"""
        beta = self.get_beta()
        if beta is None or beta == 0:
            return None
        
        excess_returns = self.returns - (self.risk_free_rate / 252 / 6.5)
        treynor = excess_returns.mean() / beta
        
        if annualize:
            treynor *= (252 * 6.5)
        
        return treynor
    
    # ============================================================
    # TRADE-LEVEL ANALYSIS
    # ============================================================
    
    def get_trade_metrics(self):
        """Comprehensive trade-level analysis"""
        if self.closed_trades.empty:
            return {}
        
        wins = self.closed_trades[self.closed_trades['profit_loss_dollars'] > 0]
        losses = self.closed_trades[self.closed_trades['profit_loss_dollars'] < 0]
        
        total_trades = len(self.closed_trades)
        
        # Calculate metrics
        win_rate = len(wins) / total_trades * 100 if total_trades > 0 else 0
        
        win_amounts = wins['profit_loss_dollars'].values
        loss_amounts = abs(losses['profit_loss_dollars'].values)
        
        avg_win = win_amounts.mean() if len(win_amounts) > 0 else 0
        avg_loss = loss_amounts.mean() if len(loss_amounts) > 0 else 0
        
        max_win = win_amounts.max() if len(win_amounts) > 0 else 0
        max_loss = loss_amounts.max() if len(loss_amounts) > 0 else 0
        
        # Profit factor
        gross_profit = win_amounts.sum() if len(win_amounts) > 0 else 0
        gross_loss = loss_amounts.sum() if len(loss_amounts) > 0 else 0
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
        
        # Risk/Reward ratio
        risk_reward = avg_win / avg_loss if avg_loss > 0 else 0
        
        # Expectancy
        expectancy = (win_rate / 100 * avg_win) - ((1 - win_rate / 100) * avg_loss)
        
        # Win/Loss streaks
        outcomes = (self.closed_trades['profit_loss_dollars'] > 0).astype(int).values
        max_win_streak = self._calculate_max_streak(outcomes, 1)
        max_loss_streak = self._calculate_max_streak(outcomes, 0)
        
        return {
            'total_trades': total_trades,
            'winning_trades': len(wins),
            'losing_trades': len(losses),
            'win_rate_pct': win_rate,
            'avg_win_dollars': avg_win,
            'avg_loss_dollars': avg_loss,
            'max_win_dollars': max_win,
            'max_loss_dollars': max_loss,
            'profit_factor': profit_factor,
            'risk_reward_ratio': risk_reward,
            'expectancy_dollars': expectancy,
            'max_consecutive_wins': max_win_streak,
            'max_consecutive_losses': max_loss_streak,
            'gross_profit': gross_profit,
            'gross_loss': gross_loss
        }
    
    def _calculate_max_streak(self, outcomes, target):
        """Helper to calculate max consecutive occurrences"""
        max_streak = 0
        current_streak = 0
        
        for outcome in outcomes:
            if outcome == target:
                current_streak += 1
                max_streak = max(max_streak, current_streak)
            else:
                current_streak = 0
        
        return max_streak
    
    # ============================================================
    # RISK WARNINGS & CLASSIFICATION
    # ============================================================
    
    def assess_risk_level(self):
        """
        Assess overall risk level and generate warnings
        
        Returns:
            dict: Risk assessment with severity and warnings
        """
        warnings = []
        severity = "LOW"
        
        # Get metrics
        total_return = self.performance.get('total_return_pct', 0) if self.performance else 0
        dd_analysis = self.get_max_drawdown_analysis()
        max_dd = dd_analysis.get('max_drawdown_pct', 0)
        trade_metrics = self.get_trade_metrics()
        win_rate = trade_metrics.get('win_rate_pct', 0)
        profit_factor = trade_metrics.get('profit_factor', 0)
        risk_reward = trade_metrics.get('risk_reward_ratio', 0)
        
        # Check 1: High win rate but low returns
        if win_rate > 70 and total_return < 5:
            warnings.append({
                'type': 'HIGH_WIN_RATE_LOW_RETURN',
                'severity': 'CRITICAL',
                'message': f'🚨 CRITICAL: {win_rate:.0f}% win rate but only {total_return:+.1f}% return!',
                'explanation': 'Winning trades are too small relative to losing trades',
                'recommendation': 'Implement better position sizing and let winners run'
            })
            severity = "CRITICAL"
        
        # Check 2: Large drawdown
        if max_dd > 20:
            warnings.append({
                'type': 'EXCESSIVE_DRAWDOWN',
                'severity': 'CRITICAL',
                'message': f'🚨 CRITICAL: {max_dd:.1f}% maximum drawdown',
                'explanation': 'Strategy experienced severe capital loss',
                'recommendation': 'Implement stop losses and reduce position sizes'
            })
            severity = "CRITICAL"
        elif max_dd > 10:
            warnings.append({
                'type': 'HIGH_DRAWDOWN',
                'severity': 'HIGH',
                'message': f'⚠️ HIGH RISK: {max_dd:.1f}% maximum drawdown',
                'explanation': 'Strategy has significant downside risk',
                'recommendation': 'Consider tighter risk controls'
            })
            if severity == "LOW":
                severity = "HIGH"
        
        # Check 3: Poor risk/reward ratio
        if risk_reward < 1.0:
            warnings.append({
                'type': 'POOR_RISK_REWARD',
                'severity': 'HIGH',
                'message': f'⚠️ Poor Risk/Reward: {risk_reward:.2f}:1',
                'explanation': 'Average wins are smaller than average losses',
                'recommendation': 'Cut losses faster and let winners run longer'
            })
            if severity == "LOW":
                severity = "HIGH"
        
        # Check 4: Low profit factor
        if profit_factor < 1.0:
            warnings.append({
                'type': 'UNPROFITABLE',
                'severity': 'CRITICAL',
                'message': f'🚨 Strategy is LOSING MONEY (Profit Factor: {profit_factor:.2f})',
                'explanation': 'Gross losses exceed gross profits',
                'recommendation': 'Strategy needs fundamental redesign'
            })
            severity = "CRITICAL"
        elif profit_factor < 1.5:
            warnings.append({
                'type': 'LOW_PROFIT_FACTOR',
                'severity': 'MEDIUM',
                'message': f'⚠️ Low Profit Factor: {profit_factor:.2f}',
                'explanation': 'Strategy has low profitability margin',
                'recommendation': 'Improve win rate or risk/reward ratio'
            })
            if severity == "LOW":
                severity = "MEDIUM"
        
        # Check 5: Negative returns
        if total_return < 0:
            warnings.append({
                'type': 'NEGATIVE_RETURNS',
                'severity': 'CRITICAL',
                'message': f'🚨 LOSING MONEY: {total_return:.1f}% return',
                'explanation': 'Strategy has negative overall performance',
                'recommendation': 'DO NOT trade this strategy live'
            })
            severity = "CRITICAL"
        
        # Check 6: Underperforming benchmark
        benchmark_perf = self.reader.get_strategy_performance(self.benchmark)
        if benchmark_perf:
            bench_return = benchmark_perf.get('total_return_pct', 0)
            if total_return < bench_return:
                warnings.append({
                    'type': 'UNDERPERFORMING_BENCHMARK',
                    'severity': 'HIGH',
                    'message': f'⚠️ Underperforming {self.benchmark}: {total_return:.1f}% vs {bench_return:.1f}%',
                    'explanation': f'Strategy returns worse than buying and holding {self.benchmark}',
                    'recommendation': 'Consider if complexity and risk are justified'
                })
                if severity in ["LOW", "MEDIUM"]:
                    severity = "HIGH"
        
        # Calculate risk score (0-100)
        risk_score = self._calculate_risk_score(max_dd, total_return, win_rate, profit_factor)
        
        return {
            'severity': severity,
            'risk_score': risk_score,
            'warnings': warnings,
            'summary': self._generate_risk_summary(severity, risk_score)
        }
    
    def _calculate_risk_score(self, max_dd, total_return, win_rate, profit_factor):
        """Calculate overall risk score (0-100, higher = riskier)"""
        score = 0
        
        # Drawdown component (0-40 points)
        score += min(max_dd * 2, 40)
        
        # Return/Risk component (0-30 points)
        if total_return < 0:
            score += 30
        elif total_return < 5:
            score += 20
        elif total_return < 10:
            score += 10
        
        # Win rate mismatch (0-30 points)
        if win_rate > 70 and total_return < 10:
            score += 30
        elif win_rate > 60 and total_return < 5:
            score += 20
        
        return min(score, 100)
    
    def _generate_risk_summary(self, severity, risk_score):
        """Generate human-readable risk summary"""
        if severity == "CRITICAL":
            return f"🚨 CRITICAL ISSUES DETECTED (Risk Score: {risk_score}/100) - Strategy is NOT ready for live trading"
        elif severity == "HIGH":
            return f"⚠️ HIGH RISK (Risk Score: {risk_score}/100) - Significant issues need to be addressed"
        elif severity == "MEDIUM":
            return f"⚠️ MEDIUM RISK (Risk Score: {risk_score}/100) - Some improvements recommended"
        else:
            return f"✅ LOW RISK (Risk Score: {risk_score}/100) - Strategy shows reasonable risk profile"
    
    # ============================================================
    # COMPREHENSIVE REPORT GENERATION
    # ============================================================
    
    def generate_report(self):
        """Generate comprehensive risk analysis report"""
        dd_analysis = self.get_max_drawdown_analysis()
        trade_metrics = self.get_trade_metrics()
        risk_assessment = self.assess_risk_level()
        
        report = {
            # Basic metrics
            'total_return_pct': self.performance.get('total_return_pct', 0) if self.performance else 0,
            'total_profit_dollars': self.performance.get('total_profit_dollars', 0) if self.performance else 0,
            
            # Volatility metrics
            'volatility_annual_pct': self.get_volatility(annualize=True),
            'downside_deviation_pct': self.get_downside_deviation(),
            'value_at_risk_95_pct': self.get_var(0.95),
            'conditional_var_95_pct': self.get_cvar(0.95),
            
            # Performance ratios
            'sharpe_ratio': self.get_sharpe_ratio(),
            'sortino_ratio': self.get_sortino_ratio(),
            'calmar_ratio': self.get_calmar_ratio(),
            'omega_ratio': self.get_omega_ratio(),
            
            # Market exposure
            'beta': self.get_beta(),
            'alpha_pct': self.get_alpha(),
            'correlation': self.get_correlation(),
            'information_ratio': self.get_information_ratio(),
            'treynor_ratio': self.get_treynor_ratio(),
            
            # Drawdown analysis
            'drawdown_analysis': dd_analysis,
            
            # Trade metrics
            'trade_metrics': trade_metrics,
            
            # Risk assessment
            'risk_assessment': risk_assessment
        }
        
        return report
    
    def print_report(self):
        """Print formatted risk analysis report"""
        report = self.generate_report()
        
        print("\n" + "="*70)
        print(f"COMPREHENSIVE RISK ANALYSIS: {self.strategy_name}")
        print("="*70)
        
        # Risk Assessment
        assessment = report['risk_assessment']
        print(f"\n{assessment['summary']}")
        
        if assessment['warnings']:
            print(f"\n⚠️ WARNINGS ({len(assessment['warnings'])}):")
            for warning in assessment['warnings']:
                print(f"\n{warning['message']}")
                print(f"   Explanation: {warning['explanation']}")
                print(f"   Recommendation: {warning['recommendation']}")
        
        # Performance Summary
        print(f"\n📊 PERFORMANCE:")
        print(f"   Total Return: {report['total_return_pct']:+.2f}%")
        print(f"   Total Profit: ${report['total_profit_dollars']:+,.0f}")
        
        # Risk Metrics
        print(f"\n📉 RISK METRICS:")
        print(f"   Volatility (Annual): {report['volatility_annual_pct']:.2f}%")
        print(f"   Downside Deviation: {report['downside_deviation_pct']:.2f}%")
        print(f"   VaR (95%): {report['value_at_risk_95_pct']:.2f}%")
        print(f"   CVaR (95%): {report['conditional_var_95_pct']:.2f}%")
        print(f"   Max Drawdown: {report['drawdown_analysis']['max_drawdown_pct']:.2f}%")
        
        # Performance Ratios
        print(f"\n📈 PERFORMANCE RATIOS:")
        print(f"   Sharpe Ratio: {report['sharpe_ratio']:.3f}")
        print(f"   Sortino Ratio: {report['sortino_ratio']:.3f}")
        print(f"   Calmar Ratio: {report['calmar_ratio']:.3f}")
        print(f"   Omega Ratio: {report['omega_ratio']:.3f}")
        
        # Market Exposure
        if report['beta'] is not None:
            print(f"\n🎯 MARKET EXPOSURE:")
            print(f"   Beta: {report['beta']:.3f}")
            print(f"   Alpha: {report['alpha_pct']:+.2f}%")
            print(f"   Correlation: {report['correlation']:.3f}")
            print(f"   Information Ratio: {report['information_ratio']:.3f}")
        
        # Trade Statistics
        trade_metrics = report['trade_metrics']
        if trade_metrics:
            print(f"\n💼 TRADE STATISTICS:")
            print(f"   Total Trades: {trade_metrics['total_trades']}")
            print(f"   Win Rate: {trade_metrics['win_rate_pct']:.1f}%")
            print(f"   Profit Factor: {trade_metrics['profit_factor']:.2f}")
            print(f"   Risk/Reward: {trade_metrics['risk_reward_ratio']:.2f}:1")
            print(f"   Expectancy: ${trade_metrics['expectancy_dollars']:+,.0f}")
        
        print("\n" + "="*70 + "\n")


# ============================================================
# CONVENIENCE FUNCTIONS
# ============================================================

def analyze_strategy_risk(reader, strategy_name, benchmark='SPY'):
    """
    Convenience function to analyze strategy risk
    
    Usage:
        analyzer = analyze_strategy_risk(reader, 'My Strategy')
        analyzer.print_report()
    """
    analyzer = RiskAnalyzerDB(reader, strategy_name, benchmark)
    return analyzer