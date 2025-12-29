# Strategy Research: Achieving 1% Monthly Returns

Comprehensive research on profitable systematic trading strategies.

---

## Executive Summary

Achieving consistent 1% monthly returns (12%+ annually) is realistic but challenging:

| Benchmark | Annual Return | Sharpe | Max Drawdown |
|-----------|---------------|--------|--------------|
| S&P 500 | ~10% | 0.4 | 15-20% |
| Top Quant Funds | 15-25% | 1.5-2.0 | 10-20% |
| **Our Target** | **12%+** | **≥1.0** | **≤15%** |

**Key Finding:** A Sharpe ratio of 1.0 means ~3-4 losing months per year. True "never lose" requires Sharpe > 3.0 (extremely rare).

---

## 1. Proven Quantitative Strategies

### 1.1 Momentum (Strong Academic Evidence)

**Source:** Jegadeesh & Titman (1993), Moskowitz et al. (2012)

**Cross-Sectional Momentum:**
- Rank stocks by 12-month returns (skip most recent month)
- Buy top 20%, avoid bottom 20%
- Hold 1-3 months
- Expected Sharpe: 0.5-0.8

**Time-Series Momentum:**
- Entry: 12-month return > 0 OR price > 12-month MA
- Exit: 12-month return < 0
- Volatility-scaled position sizing
- Expected Sharpe: 0.5-1.0

**Improvement to Our Trend Following:**
```python
# Add dual momentum check
def should_enter(self, stock_data, spy_data):
    stock_momentum = stock_data['close'].iloc[-1] / stock_data['close'].iloc[-252] - 1
    spy_momentum = spy_data['close'].iloc[-1] / spy_data['close'].iloc[-252] - 1

    # Only enter if BOTH stock and market show positive momentum
    return stock_momentum > 0 and spy_momentum > 0
```

### 1.2 Mean Reversion (Proven Short-Term)

**Source:** Poterba & Summers (1988), Lo & MacKinlay (1990)

**Short-Term Reversal:**
- Lookback: 1-4 weeks (5-20 trading days)
- Entry: Stock down 10%+ in 5 days with high volume
- Exit: Return to 20-day moving average
- Win rate: 55-60%, but small gains

**Bollinger Band Reversion:**
- Standard parameters (20-period, 2 std) are academically sound
- Use OR logic: `RSI < 35 OR below BB lower`
- Add volume spike > 1.5x for confirmation

**Fix for Our Mean Reversion Strategy:**
```python
# Current (broken): price_oversold AND above_vwap (contradictory!)
# Fixed:
if (rsi < 35 or close < bb_lower) and relative_volume > 1.5:
    return 'BUY'
```

### 1.3 Low Volatility Anomaly (Underutilized)

**Source:** Ang et al. (2006, 2009), Baker et al. (2011)

One of the most robust anomalies:
- Rank stocks by 60-day realized volatility
- Buy lowest 20% volatility stocks
- Rebalance monthly
- Expected: 8-10% annual with ~10% max drawdown
- Outperforms especially in bear markets

**Implementation:**
```python
def low_volatility_screen(universe_data, percentile=20):
    """Select lowest volatility stocks."""
    volatilities = {}
    for symbol, data in universe_data.items():
        vol = data['close'].pct_change().rolling(60).std().iloc[-1] * np.sqrt(252)
        volatilities[symbol] = vol

    threshold = np.percentile(list(volatilities.values()), percentile)
    return [s for s, v in volatilities.items() if v <= threshold]
```

### 1.4 Factor-Based Strategies

**The Fama-French Factors + Momentum:**

| Factor | Definition | Annual Premium |
|--------|------------|----------------|
| Market | Stock - T-bill | ~6% |
| Size (SMB) | Small - Large | ~2% |
| Value (HML) | High B/M - Low B/M | ~3% |
| Profitability | High - Low ROE | ~3% |
| Investment | Conservative - Aggressive | ~2% |
| **Momentum** | Winners - Losers | **~6%** |

**Multi-Factor Strategy:**
```python
def multi_factor_score(stock):
    """Composite factor score."""
    scores = {
        'value': (median_pe - stock.pe) / median_pe,  # Lower P/E is better
        'quality': stock.roe / median_roe,  # Higher ROE is better
        'momentum': stock.return_12m / median_return,  # Higher momentum is better
        'low_vol': (median_vol - stock.vol) / median_vol,  # Lower vol is better
    }
    return sum(scores.values()) / len(scores)
```

---

## 2. Risk Management Techniques

### 2.1 Position Sizing Methods

**Kelly Criterion (Optimal but Aggressive):**
```
Kelly % = (Win Rate * Avg Win/Avg Loss - (1 - Win Rate)) / (Avg Win/Avg Loss)

Example:
- Win Rate: 55%
- Avg Win: 6%, Avg Loss: 3%
- Kelly = (0.55 * 2 - 0.45) / 2 = 32.5%

Use HALF-KELLY for safety: 16% max per position
```

**Volatility-Scaled (Recommended):**
```python
def volatility_position_size(target_vol=0.15, realized_vol=0.30, max_size=0.10):
    """Scale position by inverse volatility."""
    raw_size = target_vol / realized_vol
    return min(raw_size, max_size)

# Examples:
# High vol stock (30%): position = 5%
# Low vol stock (15%): position = 10%
```

### 2.2 Stop-Loss Strategies

**Research Findings (Kaminski & Lo, 2014):**
- Simple stop-loss rules improve Sharpe by 0.1-0.2
- Optimal stop depends on strategy type:

| Strategy Type | Stop Type | Level |
|---------------|-----------|-------|
| Momentum | Trailing stop | 2-3 ATR |
| Mean Reversion | Fixed stop | 1.5-2 ATR |
| Trend Following | Trend reversal | Price < 200-day MA |

**ATR-Based Stop (Recommended):**
```python
def atr_stop(entry_price, atr, multiplier=2.5):
    """Volatility-adjusted stop loss."""
    return entry_price - (atr * multiplier)

# Trend following: multiplier = 2.5-3.0
# Mean reversion: multiplier = 1.5-2.0
```

### 2.3 Volatility Targeting

**The Key to Consistent Returns:**
```python
def volatility_target_adjustment(positions, realized_vol, target_vol=0.12):
    """Scale all positions to target volatility."""
    scalar = target_vol / realized_vol if realized_vol > 0 else 1.0
    scalar = max(0.5, min(scalar, 1.5))  # Limit 50%-150%

    return {symbol: pos * scalar for symbol, pos in positions.items()}
```

Target monthly volatility of 3-4% (10-14% annual) for smooth returns.

### 2.4 Portfolio Heat Management

**Maximum Portfolio Heat Rule:**
```
Total Open Risk = Sum of (Position Size * Distance to Stop)

Example:
- Position 1: 5% position, 3% stop = 0.15% risk
- Position 2: 8% position, 5% stop = 0.40% risk
- Total heat: 0.55%

MAX HEAT: Never exceed 6% total portfolio risk
```

---

## 3. Evidence-Based Indicators

### 3.1 Indicators with Academic Backing

| Indicator | Evidence | Best Use |
|-----------|----------|----------|
| Moving Averages (50/200) | Strong | Trend identification |
| RSI (14-period) | Moderate | Mean reversion timing |
| MACD | Weak-Moderate | Momentum confirmation |
| Bollinger Bands | Moderate | Volatility breakouts |
| Volume (OBV, MFI) | Strong | Entry confirmation |
| ATR | Strong | Position sizing, stops |

### 3.2 Fundamental Factors That Work

| Factor | How to Measure | Annual Premium |
|--------|----------------|----------------|
| Value | P/E, P/B, EV/EBITDA | 2-4% |
| Quality | ROE, margins, low debt | 3-5% |
| Low Volatility | 60-day std dev | 2-3% |
| Momentum | 12-month return | 4-6% |

### 3.3 Sentiment Indicators

| Indicator | Source | Signal |
|-----------|--------|--------|
| VIX | CBOE | > 25 = buy (contrarian) |
| Put/Call Ratio | Options | > 1.0 = oversold |
| AAII Sentiment | Surveys | Extreme bearishness = buy |

---

## 4. Realistic Expectations

### 4.1 Quant Fund Performance

| Fund Type | Annual Return | Sharpe | Max DD |
|-----------|---------------|--------|--------|
| Renaissance Medallion | 35-40%* | 2.0-3.0 | 10-15% |
| Two Sigma | 15-25% | 1.5-2.0 | 10-20% |
| AQR | 8-15% | 0.8-1.2 | 15-25% |
| Average Quant Fund | 8-12% | 0.6-1.0 | 15-25% |

*Medallion uses HFT/market making - not replicable

### 4.2 Sharpe Ratio Requirements

For 1% average monthly with "consistent" performance:

```
Target: 1% monthly = 12% annually
Acceptable volatility: 10-12% annually

Sharpe = (12% - 4% risk-free) / 11% = 0.73

For mostly positive months:
- Sharpe 1.0: ~35% months negative (4/year)
- Sharpe 1.5: ~25% months negative (3/year)
- Sharpe 2.0: ~15% months negative (2/year)
```

### 4.3 Monthly Return Distribution (Sharpe 1.0)

| Percentile | Monthly Return |
|------------|----------------|
| 95th | +5-7% |
| 75th | +2-4% |
| 50th (median) | +1% |
| 25th | -1% |
| 5th | -4-6% |

**Reality:** Plan for 3-4 losing months per year even with excellent strategy.

---

## 5. Strategy Combinations

### 5.1 Recommended Allocation

Based on risk parity and historical correlations:

| Strategy Type | Allocation | Expected Contribution |
|---------------|------------|----------------------|
| Momentum/Trend | 30% | +4% |
| Mean Reversion | 25% | +3% |
| Low Volatility | 25% | +2.5% |
| Quality/Value | 20% | +2.5% |
| **Total** | **100%** | **~12%** |

### 5.2 Regime-Based Switching

```python
REGIME_ALLOCATIONS = {
    'BULL_LOW_VOL': {
        'momentum': 0.50,
        'mean_reversion': 0.20,
        'low_volatility': 0.15,
        'conservative': 0.15
    },
    'BULL_HIGH_VOL': {
        'momentum': 0.30,
        'mean_reversion': 0.30,
        'low_volatility': 0.25,
        'conservative': 0.15
    },
    'BEAR': {
        'momentum': 0.10,
        'mean_reversion': 0.40,
        'low_volatility': 0.30,
        'conservative': 0.20
    },
    'TRANSITION': {
        'momentum': 0.20,
        'mean_reversion': 0.30,
        'low_volatility': 0.25,
        'conservative': 0.25
    }
}
```

### 5.3 Signal Ensemble

```python
def ensemble_signal(strategy_signals, weights):
    """Combine signals from multiple strategies."""
    buy_weight = sum(w for sig, w in zip(strategy_signals, weights) if sig == 'BUY')
    sell_weight = sum(w for sig, w in zip(strategy_signals, weights) if sig == 'SELL')

    total_weight = sum(weights)

    if buy_weight / total_weight > 0.5 and sell_weight == 0:
        return 'BUY'
    elif sell_weight / total_weight > 0.3:
        return 'SELL'
    return 'HOLD'
```

---

## 6. Actionable Recommendations

### 6.1 Immediate Fixes

1. **Mean Reversion:** Remove `above_vwap` condition (contradictory)
2. **Position Sizing:** Add volatility scaling
3. **Stops:** Implement ATR-based stops
4. **Regime Filter:** Add market regime detection

### 6.2 New Strategies to Add

**Priority 1: Low Volatility**
- Lowest 20% volatility stocks
- Monthly rebalance
- Expected: +2-3% improvement

**Priority 2: Quality + Momentum**
- ROE > 15%, Debt/Equity < 0.5
- 12-month return > 0
- Expected: +3% improvement

**Priority 3: Dual Momentum**
- Compare SPY vs AGG monthly
- If AGG > SPY: reduce equity exposure
- Protects in bear markets

### 6.3 Validation Protocol

1. **In-Sample:** 2015-2020
2. **Out-of-Sample:** 2021-2024
3. **Required:** T-stat > 2.0, Sharpe decline < 50%

---

## Key Academic References

1. Jegadeesh & Titman (1993) - "Returns to Buying Winners"
2. Fama & French (1993, 2015) - Factor Models
3. Moskowitz et al. (2012) - "Time Series Momentum"
4. Ang et al. (2006, 2009) - "Low Volatility Anomaly"
5. Asness et al. (2013) - "Value and Momentum Everywhere"
6. Kaminski & Lo (2014) - "When Do Stop-Loss Rules Stop Losses?"

---

## Summary

To achieve 1% monthly returns:

| Component | Recommendation |
|-----------|----------------|
| **Strategies** | Combine momentum (30%), mean reversion (25%), low vol (25%), quality (20%) |
| **Risk** | Volatility target 10-12%, ATR stops, 6% max heat |
| **Indicators** | Moving averages, RSI, Bollinger, volume confirmation |
| **Expectation** | 3-4 losing months/year with Sharpe 1.0 |
| **Validation** | Walk-forward, T-stat > 2.0 |
