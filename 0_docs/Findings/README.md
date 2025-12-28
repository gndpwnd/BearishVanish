# Strategy Findings

This folder contains documented findings from strategy research, backtesting, and analysis.

## Folder Structure

```
Findings/
├── README.md                    # This file
├── strategies/                  # Individual strategy test results
│   ├── momentum/               # Momentum-based strategies
│   ├── mean_reversion/         # Mean reversion strategies
│   ├── trend_following/        # Trend following strategies
│   └── hybrid/                 # Combined/hybrid approaches
├── indicators/                  # Indicator effectiveness studies
│   ├── technical/              # Technical indicator analysis
│   ├── volume/                 # Volume-based indicators
│   └── custom/                 # Custom indicator development
├── risk_management/            # Risk management findings
│   ├── position_sizing/        # Position sizing experiments
│   ├── stop_losses/            # Stop-loss effectiveness
│   └── portfolio_heat/         # Portfolio-level risk
└── market_conditions/          # Market regime analysis
    ├── bull_markets/           # Bull market performance
    ├── bear_markets/           # Bear market performance
    └── sideways/               # Range-bound performance
```

## Naming Convention

Use this format for finding documents:

```
YYYY-MM-DD_strategy-name_test-type.md

Examples:
2024-12-28_momentum-rsi_backtest-sp500.md
2024-12-28_mean-reversion-bollinger_parameter-sweep.md
2024-12-28_custom-volume-indicator_development.md
```

## Finding Template

Each finding should include:

```markdown
# [Strategy/Indicator Name] - [Test Type]

**Date:** YYYY-MM-DD
**Universe:** S&P 500 / NASDAQ 100 / Custom
**Period:** Start Date to End Date
**Author:** [Name]

## Summary
Brief 2-3 sentence summary of findings.

## Hypothesis
What we expected to find.

## Methodology
- Parameters tested
- Data used
- Metrics evaluated

## Results

### Key Metrics
| Metric | Value |
|--------|-------|
| Total Return | X% |
| Sharpe Ratio | X.XX |
| Max Drawdown | X% |
| Win Rate | X% |
| Profit Factor | X.XX |

### Charts
[Include equity curves, drawdown charts, monthly returns]

## Analysis
Detailed interpretation of results.

## Conclusions
- What worked
- What didn't work
- Recommended next steps

## Next Steps
- [ ] Follow-up tests to run
- [ ] Parameters to optimize
- [ ] Variations to try
```

## Goals

**Primary Goal:** Find strategies that achieve:
- 1% average monthly return (12%+ annually)
- Maximum drawdown < 15%
- Sharpe ratio > 1.0
- No losing months (stretch goal) or minimal losing months

**Secondary Goals:**
- Understand which indicators actually predict returns
- Identify optimal risk management parameters
- Document what doesn't work (equally valuable)
