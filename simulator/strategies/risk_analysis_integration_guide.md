# Risk Analysis Integration Guide

## 📋 Overview

This guide shows how to integrate enterprise-grade risk analysis into your trading simulation framework.

## 🎯 What You'll Get

✅ **Strategy-Level Risk Metrics**:
- Sharpe, Sortino, Calmar ratios
- VaR, CVaR, drawdown analysis
- Beta, Alpha, Information Ratio
- Trade-level statistics

✅ **Portfolio-Level Risk Analysis**:
- Combined portfolio metrics
- Diversification benefits
- Strategy correlations
- Risk contributions

✅ **Automated Risk Warnings**:
- Identifies high win rate / low return paradoxes
- Flags excessive drawdowns
- Detects poor risk/reward ratios
- Classifies overall risk level

---

## 🔧 Quick Start

### 1. Add Risk Analysis to Individual Strategies

In your `simulator.py`, after running the simulation:

```python
# At end of run_simulation()
from risk_analysis import RiskAnalyzer

print("\n" + "="*70)
print("RISK ANALYSIS REPORTS")
print("="*70)

for strategy in strategies:
    tracker = strategy_trackers[strategy.name]
    
    # Create risk analyzer
    analyzer = RiskAnalyzer(tracker, spy_tracker)
    
    # Print comprehensive risk report
    print(f"\n{'='*70}")
    print(f"RISK ANALYSIS: {strategy.name}")
    print(f"{'='*70}")
    
    analyzer.print_report()
    
    # Get programmatic access to metrics
    report = analyzer.generate_report()
    
    # Check risk level
    risk_assessment = report['risk_assessment']
    if risk_assessment['severity'] in ['CRITICAL', 'HIGH']:
        print(f"\n⚠️ WARNING: This strategy has {risk_assessment['severity']} risk issues!")
```

### 2. Add Portfolio-Level Analysis

After analyzing individual strategies:

```python
from portfolio_risk_analyzer import analyze_portfolio_risk

# Analyze portfolio (equal-weighted by default)
portfolio_analyzer = analyze_portfolio_risk(
    strategy_trackers,
    spy_tracker=spy_tracker
)

# Custom weights
custom_weights = {
    '500 Intersection': 0.4,
    'Weekly Threshold': 0.3,
    'RSI Mean Reversion': 0.3
}

portfolio_analyzer = analyze_portfolio_risk(
    strategy_trackers,
    spy_tracker=spy_tracker,
    weights=custom_weights
)
```

---

## 📊 Available Risk Metrics

### Basic Risk Metrics

```python
from risk_analysis import RiskAnalyzer

analyzer = RiskAnalyzer(tracker, spy_tracker)

# Volatility
volatility = analyzer.get_volatility(annualize=True)  # Annual volatility %

# Downside deviation (only negative returns)
downside_dev = analyzer.get_downside_deviation()

# Value at Risk (95% confidence)
var_95 = analyzer.get_var(confidence=0.95)  # Max expected loss

# Conditional VaR (tail risk)
cvar_95 = analyzer.get_cvar(confidence=0.95)  # Average loss beyond VaR
```

### Drawdown Analysis

```python
# Comprehensive drawdown metrics
dd_analysis = analyzer.get_max_drawdown_analysis()

print(f"Max Drawdown: {dd_analysis['max_drawdown_pct']:.2f}%")
print(f"Max DD Dollars: ${dd_analysis['max_drawdown_dollars']:,.0f}")
print(f"Peak Date: {dd_analysis['peak_date']}")
print(f"Trough Date: {dd_analysis['trough_date']}")
print(f"Recovery Days: {dd_analysis['recovery_days']}")
print(f"Currently in DD: {dd_analysis['currently_in_drawdown']}")
```

### Performance Ratios

```python
# Sharpe Ratio
sharpe = analyzer.get_sharpe_ratio()  # Return per unit of volatility

# Sortino Ratio
sortino = analyzer.get_sortino_ratio()  # Like Sharpe but only downside risk

# Calmar Ratio
calmar = analyzer.get_calmar_ratio()  # Return / Max Drawdown

# Omega Ratio
omega = analyzer.get_omega_ratio()  # Probability-weighted gains/losses
```

### Market Exposure

```python
# Beta (systematic risk)
beta = analyzer.get_beta()

# Alpha (excess return)
alpha = analyzer.get_alpha()

# Correlation with market
correlation = analyzer.get_correlation()

# Information Ratio
ir = analyzer.get_information_ratio()

# Treynor Ratio
treynor = analyzer.get_treynor_ratio()
```

### Trade-Level Metrics

```python
trade_metrics = analyzer.get_trade_metrics()

print(f"Total Trades: {trade_metrics['total_trades']}")
print(f"Win Rate: {trade_metrics['win_rate_pct']:.1f}%")
print(f"Profit Factor: {trade_metrics['profit_factor']:.2f}")
print(f"Risk/Reward: {trade_metrics['risk_reward_ratio']:.2f}:1")
print(f"Expectancy: ${trade_metrics['expectancy_dollars']:,.0f}")
print(f"Max Win Streak: {trade_metrics['max_consecutive_wins']}")
print(f"Max Loss Streak: {trade_metrics['max_consecutive_losses']}")
```

### Risk Assessment

```python
# Automated risk assessment
assessment = analyzer.assess_risk_level()

print(f"Risk Level: {assessment['severity']}")  # LOW, MEDIUM, HIGH, CRITICAL
print(f"Risk Score: {assessment['risk_score']}/100")
print(f"Summary: {assessment['summary']}")

# Check warnings
for warning in assessment['warnings']:
    print(f"\n{warning['message']}")
    print(f"  Explanation: {warning['explanation']}")
    print(f"  Recommendation: {warning['recommendation']}")
```

---

## 🎯 Portfolio-Level Metrics

### Basic Portfolio Analysis

```python
from portfolio_risk_analyzer import PortfolioRiskAnalyzer

# Create analyzer
portfolio_analyzer = PortfolioRiskAnalyzer(
    strategy_trackers,
    spy_tracker=spy_tracker,
    weights={'Strategy1': 0.5, 'Strategy2': 0.5}  # Optional custom weights
)

# Portfolio metrics
portfolio_return = portfolio_analyzer.get_portfolio_return()
portfolio_vol = portfolio_analyzer.get_portfolio_volatility()
portfolio_sharpe = portfolio_analyzer.get_portfolio_sharpe()
```

### Diversification Analysis

```python
# Diversification benefit
div_benefit = portfolio_analyzer.get_diversification_benefit()
print(f"Diversification reduces risk by: {div_benefit:.1f}%")

# Correlation matrix
corr_matrix = portfolio_analyzer.get_correlation_matrix()
print(corr_matrix)

# Correlation analysis
corr_analysis = portfolio_analyzer.analyze_strategy_correlations()
print(f"Average Correlation: {corr_analysis['average_correlation']:.3f}")
print(f"Diversification Score: {corr_analysis['diversification_score']:.1f}/100")

# High correlation pairs (redundant strategies)
for pair in corr_analysis['high_correlation_pairs']:
    print(f"{pair['strategy1']} ↔ {pair['strategy2']}: {pair['correlation']:.3f}")
```

### Risk Contributions

```python
# Each strategy's contribution to portfolio risk
risk_contrib = portfolio_analyzer.get_contribution_to_risk()

for name, contrib in sorted(risk_contrib.items(), 
                            key=lambda x: x[1], 
                            reverse=True):
    print(f"{name}: {contrib:.1f}% of portfolio risk")
```

---

## 📈 Integration with Analysis Dashboard

### Add Risk Panel to GUI

In `strategy_analysis.py`:

```python
from risk_analysis import RiskAnalyzer

def show_strategy_analysis(strategy, tracker, stock_data, symbols, spy_tracker=None):
    # ... existing code ...
    
    # Add risk analysis panel
    risk_ax = fig.add_subplot(gs[2, 2:])
    create_risk_analysis_panel(risk_ax, tracker, spy_tracker)
    
    # ... rest of code ...

def create_risk_analysis_panel(ax, tracker, spy_tracker):
    """Create risk analysis visualization panel"""
    ax.axis('off')
    
    # Create risk analyzer
    analyzer = RiskAnalyzer(tracker, spy_tracker)
    assessment = analyzer.assess_risk_level()
    
    # Risk score gauge
    risk_score = assessment['risk_score']
    severity = assessment['severity']
    
    # Color based on severity
    colors = {
        'LOW': '#4CAF50',
        'MEDIUM': '#FF9800',
        'HIGH': '#FF5722',
        'CRITICAL': '#D32F2F'
    }
    color = colors.get(severity, '#757575')
    
    # Create visual representation
    ax.barh(0.85, risk_score/100, height=0.08, color=color, alpha=0.7)
    ax.barh(0.85, 1, height=0.08, color='lightgray', alpha=0.3)
    
    ax.text(0.5, 0.85, f'Risk Score: {risk_score}/100',
            ha='center', va='center', fontweight='bold')
    
    # Add warning text
    y_pos = 0.7
    ax.text(0.5, y_pos, assessment['summary'], 
            ha='center', fontsize=9, wrap=True)
    
    # Show top warnings
    y_pos = 0.5
    for warning in assessment['warnings'][:3]:
        ax.text(0.05, y_pos, f"⚠️ {warning['type'].replace('_', ' ')}",
                ha='left', fontsize=8, fontweight='bold')
        y_pos -= 0.1
    
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
```

---

## 🎓 Understanding Risk Metrics

### Sharpe Ratio

**What it measures**: Risk-adjusted return

**Formula**: (Return - Risk-free) / Volatility

**Interpretation**:
- < 0: Losing money
- 0-1: Poor risk-adjusted return
- 1-2: Good
- 2-3: Very good
- \> 3: Excellent

### Sortino Ratio

**What it measures**: Return per unit of downside risk

**Why it's better**: Only penalizes downside volatility, not upside

**Interpretation**: Same as Sharpe, but usually higher

### Calmar Ratio

**What it measures**: Return relative to worst drawdown

**Formula**: Annual Return / Max Drawdown

**Interpretation**:
- < 0.5: Poor
- 0.5-1.0: Fair
- 1.0-3.0: Good
- \> 3.0: Excellent

### Beta

**What it measures**: Sensitivity to market movements

**Interpretation**:
- β = 1.0: Moves with market
- β > 1.0: More volatile than market
- β < 1.0: Less volatile than market
- β < 0: Moves opposite to market

### Alpha

**What it measures**: Excess return vs expected (CAPM)

**Interpretation**:
- α > 0: Outperforming for given risk
- α = 0: Fair return for risk taken
- α < 0: Underperforming

### Value at Risk (VaR)

**What it measures**: Maximum expected loss at confidence level

**Example**: VaR(95%) = 5% means "95% confident we won't lose more than 5%"

### Conditional VaR (CVaR)

**What it measures**: Average loss when VaR is exceeded

**Why it matters**: Tells you how bad things get in worst 5% of cases

---

## ⚠️ Risk Warnings System

### Severity Levels

**LOW**: Strategy looks reasonable
- No major issues
- Metrics within acceptable ranges

**MEDIUM**: Some improvements recommended
- Minor issues that could be optimized
- Not critical but worth addressing

**HIGH**: Significant issues
- Major problems that need fixing
- Strategy likely underperforming

**CRITICAL**: NOT ready for live trading
- Fundamental flaws
- High probability of losses

### Common Warning Types

#### HIGH_WIN_RATE_LOW_RETURN
```
Trigger: Win rate > 70% but return < 5%
Issue: Small wins, huge losses
Fix: Better position sizing, let winners run
```

#### EXCESSIVE_DRAWDOWN
```
Trigger: Max drawdown > 20%
Issue: Severe capital loss
Fix: Implement stop losses, reduce position size
```

#### POOR_RISK_REWARD
```
Trigger: Avg win < Avg loss
Issue: Losing more when wrong than winning when right
Fix: Cut losses faster, let winners run
```

#### UNPROFITABLE
```
Trigger: Profit factor < 1.0
Issue: Gross losses > gross profits
Fix: Strategy needs redesign
```

#### UNDERPERFORMING_BENCHMARK
```
Trigger: Return < S&P 500
Issue: Not worth the complexity and risk
Fix: Improve strategy or just buy SPY
```

---

## 📝 Complete Integration Example

```python
# In simulator.py, at end of run_simulation()

print("\n" + "="*70)
print("COMPREHENSIVE RISK ANALYSIS")
print("="*70)

from risk_analysis import RiskAnalyzer
from portfolio_risk_analyzer import analyze_portfolio_risk

# ============================================================
# 1. INDIVIDUAL STRATEGY ANALYSIS
# ============================================================

strategy_risk_reports = {}

for strategy in strategies:
    tracker = strategy_trackers[strategy.name]
    
    print(f"\n{'='*70}")
    print(f"STRATEGY: {strategy.name}")
    print(f"{'='*70}")
    
    # Create analyzer
    analyzer = RiskAnalyzer(tracker, spy_tracker)
    
    # Generate full report
    report = analyzer.generate_report()
    strategy_risk_reports[strategy.name] = report
    
    # Print formatted report
    analyzer.print_report()
    
    # Check risk level
    assessment = report['risk_assessment']
    
    if assessment['severity'] == 'CRITICAL':
        print(f"\n🚨 CRITICAL: {strategy.name} is NOT ready for live trading!")
        print("   DO NOT trade this strategy with real money.")
    elif assessment['severity'] == 'HIGH':
        print(f"\n⚠️ WARNING: {strategy.name} has significant risk issues")
        print("   Review warnings and make improvements before trading.")

# ============================================================
# 2. PORTFOLIO-LEVEL ANALYSIS
# ============================================================

print(f"\n\n{'='*70}")
print("PORTFOLIO-LEVEL RISK ANALYSIS")
print("="*70)

# Analyze portfolio with equal weights
portfolio_analyzer = analyze_portfolio_risk(
    strategy_trackers,
    spy_tracker=spy_tracker
)

# Get correlation insights
corr_analysis = portfolio_analyzer.analyze_strategy_correlations()

if corr_analysis['average_correlation'] > 0.8:
    print(f"\n⚠️ WARNING: High average correlation ({corr_analysis['average_correlation']:.2f})")
    print("   Strategies are not well diversified")
    print("   Consider developing strategies with different logic")

if corr_analysis['high_correlation_pairs']:
    print(f"\n⚠️ REDUNDANT STRATEGIES DETECTED:")
    for pair in corr_analysis['high_correlation_pairs']:
        print(f"   {pair['strategy1']} and {pair['strategy2']} are highly correlated ({pair['correlation']:.2f})")
    print("   Consider removing one strategy from each pair")

# ============================================================
# 3. COMPARATIVE RANKING
# ============================================================

print(f"\n\n{'='*70}")
print("STRATEGY RANKING (Risk-Adjusted)")
print("="*70)

# Rank by Sharpe Ratio
rankings = []
for name, report in strategy_risk_reports.items():
    rankings.append({
        'name': name,
        'sharpe': report['sharpe_ratio'],
        'return': report['total_return_pct'],
        'risk_score': report['risk_assessment']['risk_score'],
        'severity': report['risk_assessment']['severity']
    })

rankings.sort(key=lambda x: x['sharpe'], reverse=True)

print(f"\n{'Rank':<6} {'Strategy':<25} {'Sharpe':<10} {'Return %':<12} {'Risk':<15}")
print(f"{'-'*70}")

for i, r in enumerate(rankings, 1):
    severity_emoji = {
        'LOW': '✅',
        'MEDIUM': '⚠️',
        'HIGH': '🔶',
        'CRITICAL': '🚨'
    }
    
    emoji = severity_emoji.get(r['severity'], '❓')
    
    print(f"{i:<6} {r['name']:<25} {r['sharpe']:>8.3f} {r['return']:>10.2f}% {emoji} {r['severity']:<10}")

print(f"\n{'='*70}\n")

# ============================================================
# 4. SAVE REPORTS TO FILE
# ============================================================

# Save detailed reports
report_dir = Path('./risk_reports')
report_dir.mkdir(exist_ok=True)

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

for name, report in strategy_risk_reports.items():
    filename = report_dir / f"{name.replace(' ', '_')}_{timestamp}.json"
    
    # Convert non-serializable objects to strings
    serializable_report = {}
    for key, value in report.items():
        if isinstance(value, pd.DataFrame):
            serializable_report[key] = value.to_dict()
        elif isinstance(value, dict):
            serializable_report[key] = value
        else:
            serializable_report[key] = str(value)
    
    import json
    with open(filename, 'w') as f:
        json.dump(serializable_report, f, indent=2)

print(f"✅ Risk reports saved to: {report_dir}/")
print(f"{'='*70}\n")
```

---

## 🎯 Best Practices

### 1. Always Run Risk Analysis

```python
# Never skip risk analysis!
analyzer = RiskAnalyzer(tracker, spy_tracker)
assessment = analyzer.assess_risk_level()

if assessment['severity'] in ['CRITICAL', 'HIGH']:
    print("⚠️ WARNING: Strategy has serious risk issues")
    # Don't proceed to live trading
```

### 2. Monitor Portfolio Correlations

```python
# Check for over-concentration
corr_analysis = portfolio_analyzer.analyze_strategy_correlations()

if corr_analysis['average_correlation'] > 0.7:
    print("⚠️ Strategies are too similar - limited diversification")
```

### 3. Track Risk Over Time

```python
# Save reports after each simulation
reports_history = []

for simulation in simulations:
    analyzer = RiskAnalyzer(tracker, spy_tracker)
    report = analyzer.generate_report()
    
    reports_history.append({
        'date': datetime.now(),
        'metrics': report
    })

# Compare metrics across simulations
```

### 4. Use Risk Warnings as Gates

```python
def can_trade_strategy(analyzer):
    """Determine if strategy is ready for live trading"""
    assessment = analyzer.assess_risk_level()
    
    # Hard stops
    if assessment['severity'] == 'CRITICAL':
        return False
    
    # Risk score threshold
    if assessment['risk_score'] > 70:
        return False
    
    # Max drawdown threshold
    dd_analysis = analyzer.get_max_drawdown_analysis()
    if dd_analysis['max_drawdown_pct'] > 15:
        return False
    
    return True
```

---

## 📚 Summary

✅ **Risk Analysis Hierarchy**:
1. Trade-level metrics (win rate, profit factor, etc.)
2. Strategy-level risk (Sharpe, drawdown, volatility)
3. Portfolio-level risk (diversification, correlations)

✅ **Key Metrics to Watch**:
- **Sharpe Ratio**: Risk-adjusted return (target: > 1.0)
- **Max Drawdown**: Worst loss (target: < 15%)
- **Profit Factor**: Gross profit / Gross loss (target: > 1.5)
- **Risk/Reward**: Avg win / Avg loss (target: > 2:1)

✅ **Red Flags**:
- High win rate but low returns
- Max drawdown > 20%
- Profit factor < 1.0
- Underperforming benchmark

✅ **Portfolio Optimization**:
- Target correlation < 0.5 between strategies
- Monitor risk contributions
- Rebalance weights based on performance

Your simulation framework now has enterprise-grade risk management! 🚀