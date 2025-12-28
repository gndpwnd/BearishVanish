# Analysis Metrics Reference

This document describes all metrics computed by the Analysis Engine.

---

## Performance Metrics

### Return Metrics

| Metric | Description | Formula |
|--------|-------------|---------|
| `total_return_pct` | Total percentage return | ((Final - Initial) / Initial) * 100 |
| `total_profit_dollars` | Absolute profit/loss | Final Value - Initial Capital |
| `annualized_return_pct` | Annualized return | ((1 + Total Return) ^ (252/days) - 1) * 100 |
| `unrealized_pnl` | Unrealized P&L from open positions | Sum of open position values - cost basis |

### Trade Statistics

| Metric | Description | Interpretation |
|--------|-------------|----------------|
| `total_trades` | Total number of trades | Entry + Exit pairs |
| `completed_trades` | Fully closed trades | Trades with both entry and exit |
| `open_positions` | Currently open trades | Trades without exit |
| `winning_trades` | Profitable trades | Exit price > Entry price |
| `losing_trades` | Losing trades | Exit price < Entry price |
| `win_rate_pct` | Win percentage | (Winners / Total Completed) * 100 |

### Profit Metrics

| Metric | Description | Good Value |
|--------|-------------|------------|
| `gross_profit` | Sum of winning trades | Higher is better |
| `gross_loss` | Sum of losing trades (absolute) | Lower is better |
| `profit_factor` | Gross Profit / Gross Loss | > 1.5 is good |
| `avg_win_dollars` | Average winning trade | Higher is better |
| `avg_loss_dollars` | Average losing trade | Lower is better |
| `risk_reward_ratio` | Avg Win / Avg Loss | > 1.5 is good |
| `expectancy_dollars` | Expected profit per trade | Win% * AvgWin - Loss% * AvgLoss |

---

## Risk Metrics

### Risk-Adjusted Returns

| Metric | Description | Formula | Good Value |
|--------|-------------|---------|------------|
| `sharpe_ratio` | Risk-adjusted return | (Return - RiskFreeRate) / StdDev | > 1.0 |
| `sortino_ratio` | Downside risk-adjusted return | (Return - RiskFreeRate) / DownsideDev | > 1.5 |
| `calmar_ratio` | Return vs Max Drawdown | AnnualizedReturn / MaxDrawdown | > 1.0 |
| `omega_ratio` | Probability weighted gains/losses | Gains / Losses at threshold | > 1.5 |
| `treynor_ratio` | Return per unit of market risk | (Return - RiskFreeRate) / Beta | Higher is better |

### Volatility Metrics

| Metric | Description | Formula |
|--------|-------------|---------|
| `volatility_annual_pct` | Annualized standard deviation | StdDev(DailyReturns) * sqrt(252) |
| `downside_deviation_pct` | Standard deviation of negative returns | StdDev(NegativeReturns) * sqrt(252) |

### Value at Risk (VaR)

| Metric | Description | Interpretation |
|--------|-------------|----------------|
| `var_95_pct` | 5% worst-case daily loss | 95% confidence you won't lose more |
| `cvar_95_pct` | Expected loss beyond VaR | Average of worst 5% of days |

### Market Exposure

| Metric | Description | Good Value |
|--------|-------------|------------|
| `beta` | Sensitivity to market (SPY) | 0.8-1.2 is moderate |
| `alpha_pct` | Excess return vs market | > 0 means outperformance |
| `correlation` | Correlation with market | Lower = more diversified |
| `information_ratio` | Alpha / Tracking Error | > 0.5 is good |

---

## Drawdown Metrics

### Summary Metrics

| Metric | Description | Good Value |
|--------|-------------|------------|
| `max_drawdown_pct` | Largest peak-to-trough decline | < 20% |
| `max_drawdown_dollars` | Maximum dollar drawdown | Depends on account size |
| `avg_drawdown_pct` | Average drawdown size | < 10% |

### Drawdown Periods

For each significant drawdown, we track:

| Field | Description |
|-------|-------------|
| `peak_date` | Date of equity peak |
| `trough_date` | Date of lowest point |
| `recovery_date` | Date when recovered (or null) |
| `drawdown_pct` | Percentage decline |
| `drawdown_dollars` | Dollar decline |
| `duration_days` | Total drawdown duration |
| `recovery_days` | Days to recover |

---

## Streak Metrics

| Metric | Description |
|--------|-------------|
| `max_win_streak` | Longest consecutive winning trades |
| `max_loss_streak` | Longest consecutive losing trades |
| `current_streak` | Current streak (positive = wins) |

### Streak Periods

Each streak is recorded with:

| Field | Description |
|-------|-------------|
| `streak_type` | 'WIN' or 'LOSS' |
| `start_date` | First trade in streak |
| `end_date` | Last trade in streak |
| `length` | Number of trades |
| `cumulative_pnl` | Total P&L during streak |

---

## Monthly Metrics

For each month, we compute:

| Field | Description |
|-------|-------------|
| `year_month` | Month identifier (YYYY-MM) |
| `return_pct` | Monthly return percentage |
| `num_trades` | Number of trades in month |
| `win_rate_pct` | Win rate for the month |

### Seasonal Analysis

Use monthly data to identify:
- Best/worst months historically
- Seasonal patterns
- Monthly consistency

---

## Volume Metrics

| Metric | Description |
|--------|-------------|
| `trades_with_volume_data` | Trades with volume info |
| `avg_entry_volume_ratio` | Avg relative volume at entry |
| `avg_exit_volume_ratio` | Avg relative volume at exit |
| `high_volume_trades` | Trades with above-avg volume |
| `low_volume_trades` | Trades with below-avg volume |
| `high_vol_win_rate` | Win rate on high volume entries |
| `low_vol_win_rate` | Win rate on low volume entries |

---

## Holding Period Metrics

| Metric | Description |
|--------|-------------|
| `avg_hold_days` | Average trade duration |
| `max_hold_days` | Longest trade |
| `min_hold_days` | Shortest trade |

---

## Metric Calculations

### Sharpe Ratio

```python
def sharpe_ratio(returns, risk_free_rate=0.04):
    """
    Sharpe Ratio = (R - Rf) / σ

    Where:
    - R = Portfolio return
    - Rf = Risk-free rate
    - σ = Standard deviation of returns
    """
    excess_returns = returns - risk_free_rate / 252
    return np.sqrt(252) * excess_returns.mean() / excess_returns.std()
```

### Sortino Ratio

```python
def sortino_ratio(returns, risk_free_rate=0.04):
    """
    Sortino Ratio = (R - Rf) / σd

    Where:
    - σd = Downside deviation (only negative returns)
    """
    excess_returns = returns - risk_free_rate / 252
    downside = returns[returns < 0].std()
    return np.sqrt(252) * excess_returns.mean() / downside
```

### Maximum Drawdown

```python
def max_drawdown(equity_curve):
    """
    Maximum peak-to-trough decline

    1. Calculate running maximum
    2. Calculate drawdown at each point
    3. Find maximum drawdown
    """
    running_max = equity_curve.cummax()
    drawdown = (equity_curve - running_max) / running_max
    return drawdown.min()
```

### Profit Factor

```python
def profit_factor(trades):
    """
    Profit Factor = Gross Profit / Gross Loss

    - > 1.0: Profitable
    - > 1.5: Good
    - > 2.0: Excellent
    """
    winners = trades[trades['pnl'] > 0]['pnl'].sum()
    losers = abs(trades[trades['pnl'] < 0]['pnl'].sum())
    return winners / losers if losers > 0 else float('inf')
```

### Beta

```python
def beta(portfolio_returns, market_returns):
    """
    Beta = Cov(Rp, Rm) / Var(Rm)

    Measures sensitivity to market movements:
    - β = 1.0: Moves with market
    - β > 1.0: More volatile than market
    - β < 1.0: Less volatile than market
    """
    covariance = np.cov(portfolio_returns, market_returns)[0, 1]
    market_variance = market_returns.var()
    return covariance / market_variance
```

### Alpha

```python
def alpha(portfolio_returns, market_returns, risk_free_rate=0.04):
    """
    Alpha = Rp - [Rf + β(Rm - Rf)]

    Excess return beyond what's explained by market exposure:
    - α > 0: Outperformance
    - α < 0: Underperformance
    """
    beta_val = beta(portfolio_returns, market_returns)
    expected = risk_free_rate + beta_val * (market_returns.mean() * 252 - risk_free_rate)
    actual = portfolio_returns.mean() * 252
    return actual - expected
```

---

## Metric Interpretation Guide

### Overall Performance Rating

| Level | Sharpe | Sortino | Max DD | Win Rate | Profit Factor |
|-------|--------|---------|--------|----------|---------------|
| Excellent | > 2.0 | > 2.5 | < 10% | > 60% | > 2.0 |
| Good | > 1.0 | > 1.5 | < 20% | > 50% | > 1.5 |
| Average | > 0.5 | > 0.7 | < 30% | > 45% | > 1.2 |
| Poor | < 0.5 | < 0.5 | > 30% | < 40% | < 1.0 |

### Strategy Style Indicators

| Style | Typical Metrics |
|-------|-----------------|
| **Momentum** | Higher beta, lower win rate, larger avg win |
| **Mean Reversion** | Lower beta, higher win rate, smaller avg win |
| **Trend Following** | Moderate beta, ~40% win rate, large winners |
| **Value** | Low beta, moderate win rate, consistent |

### Red Flags

| Warning Sign | Possible Issue |
|--------------|----------------|
| Win rate > 80% | Overfitting or small sample |
| Max drawdown > 40% | Poor risk management |
| Avg hold < 1 day | Overtrading |
| Sharpe > 3.0 | Likely overfitting |
| Zero losing trades | Insufficient testing |

---

## Using Metrics for Strategy Selection

### Comparison Framework

1. **Risk-Adjusted Return**: Start with Sharpe/Sortino
2. **Tail Risk**: Check max drawdown and CVaR
3. **Consistency**: Look at monthly win rates
4. **Capacity**: Consider average hold days

### Blending Strategies

Good combinations have:
- Low correlation between strategies
- Different beta profiles
- Complementary win rate patterns
- Diversified sector exposure
