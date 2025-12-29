# Strategy Analysis: Pre 1-Year Backtest

**Date**: 2025-12-28 22:42:20
**Purpose**: Comprehensive analysis of all 12 trading strategies to identify root causes of consistent losses
**Backtest Period**: Extended from 6 months (180 days) to 1 year (365 days) for this test

---

## Executive Summary

Analysis of all 12 strategies revealed **4 critical systemic issues** causing losses:

1. **75% of strategies have NO stop-loss protection** (9 of 12)
2. **Entry filters are too restrictive** - many AND conditions reduce signal frequency
3. **No market regime awareness** - strategies trade equally in bull/bear/sideways markets
4. **Fixed position sizing ignores volatility** - same size in calm vs chaotic markets

---

## Critical Findings by Strategy

### Strategies WITHOUT Stop Losses (CRITICAL RISK)

The following 9 strategies can hold losing positions indefinitely:

1. **AMIS** - Advanced Multi-Indicator Strategy
2. **500 Intersection** - Mean reversion based on S&P 500 slope
3. **Monthly Rolling** - Buys -5% dips, no downside protection
4. **Momentum MFI** - Exits only on signal reversal (lags 10-20%)
5. **WAM** - Weekly threshold, no stops
6. **Trend Following** - Relies on Supertrend flip (lags significantly)
7. **Rolling Windows** - Duplicate of WAM
8. **SP500 Slope v2** - Same issues as 500 Intersection
9. **Momentum Example** - Waits for death cross to exit

### Strategies WITH Stop Losses (Better but need tuning)

1. **Mean Reversion** - Has 5% stop but may be too tight for volatility
2. **Breakout** - Has 2x ATR stop but might be too wide (10-15% in volatile stocks)
3. **Conservative Income** - Has 3% stop and 6% target (best risk management overall)

---

## Detailed Analysis

### 1. AMIS (Advanced Multi-Indicator Strategy)

**Configuration:**
- Position Size: 8%
- Max Positions: 12
- Stop Loss: ❌ NONE

**Critical Issues:**

1. **Too Many Required Confirmations** (CRITICAL)
   - Requires 3+ confirmations from 6 indicators
   - Golden cross + volume spike + RSI recovery + BB + bull market = rare alignment
   - Result: Very low signal frequency, missed opportunities

2. **Contradictory Entry Logic** (HIGH)
   - Can require both "BB lower touch" (mean-reversion) AND "golden cross" (momentum) simultaneously
   - These are opposite market conditions
   - Result: Entry conditions rarely met

3. **No Downside Protection** (CRITICAL)
   - Only exits on signal reversal
   - Can hold -30% loser waiting for reversal
   - Result: Large losses compound

**Recommended Fixes:**
- Add 6-7% stop loss or 2x ATR stop
- Reduce required confirmations from 3 to 2
- Separate mean-reversion logic from momentum logic
- Use ATR-based position sizing

---

### 2. Mean Reversion Strategy

**Configuration:**
- Position Size: 8%
- Max Positions: 10
- Stop Loss: ✅ 5%

**Issues:**

1. **Entry Too Restrictive** (HIGH)
   - Requires: oversold + RSI<30 + volume spike + above VWAP
   - ALL conditions required = very low signal frequency
   - "Below BB lower" AND "above VWAP" is extremely rare

2. **Stop Loss May Be Too Tight** (MEDIUM)
   - Fixed 5% doesn't account for volatility
   - High-volatility stocks hit stop on normal fluctuations
   - Should use ATR-based stop (e.g., 2.5x ATR)

3. **No Regime Filter** (MEDIUM)
   - Mean reversion fails in strong trends
   - Needs trending vs ranging detection (e.g., ADX filter)

**Recommended Fixes:**
- Change stop to max(5%, 2.5x ATR)
- Relax entry to 3 of 4 conditions instead of all 4
- Remove VWAP requirement OR make it OR not AND
- Add ADX<25 filter (only trade in ranging markets)

---

### 3. Monthly Rolling Strategy

**Configuration:**
- Position Size: 10%
- Max Positions: 10
- Stop Loss: ❌ NONE

**Critical Issues:**

1. **Asymmetric Risk/Reward** (CRITICAL)
   - Buys at -5% dip, sells at +10% gain
   - BUT no protection if it goes to -15%, -25%, etc.
   - Actual risk:reward is unlimited:10%

2. **No Trend Filter** (HIGH)
   - Catches falling knives in strong downtrends
   - Needs 200-day SMA filter or similar

3. **No Volume Confirmation** (MEDIUM)
   - Buys dips on low volume = dead cat bounces

**Recommended Fixes:**
- Add 8-10% stop loss
- Only trade when price > 200-day SMA
- Require volume > 1.2x average on entry
- Add trailing stop to lock in profits

---

### 4. Breakout Strategy

**Configuration:**
- Position Size: 12% (HIGHEST)
- Max Positions: 6 (LOWEST)
- Stop Loss: ✅ 2x ATR below breakout

**Issues:**

1. **High Concentration Risk** (HIGH)
   - 12% per position × 6 max = 72% of capital at risk
   - One big loser wipes out multiple winners

2. **Stop Too Wide in Volatile Markets** (MEDIUM)
   - 2x ATR can be 10-15% in high-volatility stocks
   - Too much risk per trade given 12% position size

3. **False Breakout Risk** (HIGH)
   - No pullback requirement after breakout
   - Many breakouts fail immediately (bull trap)

**Recommended Fixes:**
- Reduce position size to 8-10%
- Tighten stop to 1.5x ATR
- Require pullback after breakout (2-3 bars)
- Remove volume exit condition

---

### 5. Conservative Income Strategy

**Configuration:**
- Position Size: 5% (LOWEST)
- Max Positions: 12
- Stop Loss: ✅ 3%
- Take Profit: 6%
- Max Hold: 5 days

**Analysis:**

This is the **BEST risk-managed strategy** with:
- Tight stops (3%)
- Quick exits (5 days max)
- 2:1 risk/reward ratio
- Small position size (5%)

**Issues:**

1. **Stop May Be Too Tight** (MEDIUM)
   - 3% can be hit by normal daily volatility
   - Should use max(3%, 1.5x ATR)

2. **Win Rate Likely Too Low** (HIGH)
   - Multiple restrictive entry filters
   - Tight stops reduce win rate
   - Need >40% win rate for 2:1 R/R to be profitable

**Recommended Fixes:**
- Change stop to max(3%, 1.5x ATR)
- Relax entry conditions (OR instead of AND)
- Extend max hold to 7-10 days
- Lower profit target to 4-5% for higher win rate

---

## Common Patterns Across All Strategies

### Risk Management Failures

| Issue | Count | Severity |
|-------|-------|----------|
| No stop loss | 9/12 | CRITICAL |
| No trailing stops | 12/12 | HIGH |
| Fixed position sizing (no volatility adjustment) | 12/12 | HIGH |
| No drawdown protection | 12/12 | MEDIUM |

### Entry/Exit Logic Issues

| Issue | Count | Severity |
|-------|-------|----------|
| Contradictory conditions (e.g., oversold BUT uptrend) | 8/12 | HIGH |
| Too many required confirmations (4+) | 6/12 | HIGH |
| No volume confirmation | 5/12 | MEDIUM |
| Lagging exits (wait for signal reversal) | 9/12 | HIGH |

### Market Condition Issues

| Issue | Count | Severity |
|-------|-------|----------|
| No regime filtering (bull/bear/sideways) | 11/12 | HIGH |
| No volatility adjustment | 12/12 | HIGH |
| No trend alignment check | 7/12 | MEDIUM |

---

## Recommended Fixes by Priority

### CRITICAL (Must Fix Immediately)

1. **Add stop losses to all strategies**
   - Use 2x ATR or 6-8% max
   - Implement in strategy base class for consistency

2. **Add regime filter**
   - Only go long when SPY > 200-day SMA
   - Or use VIX threshold (e.g., VIX < 30)

3. **Fix contradictory entry conditions**
   - Change AND to OR where appropriate
   - Separate mean-reversion from momentum logic

4. **Reduce required confirmations**
   - Max 2-3 confirmations, not 4-6
   - Use confidence scoring instead

### HIGH (Fix Soon)

5. **Add volatility-based position sizing**
   - Scale position size by 1/ATR or 1/VIX
   - Smaller positions in high-volatility environments

6. **Add volume confirmation**
   - Require volume > 1.2-1.5x average on entry
   - Prevents trading on low-liquidity moves

7. **Implement trailing stops**
   - Lock in profits on winning trades
   - Prevent giving back large gains

8. **Add trend filters**
   - Use ADX to identify trending vs ranging
   - Match strategy type to market condition

### MEDIUM (Nice to Have)

9. **Dynamic parameter adjustment**
   - Adapt RSI/BB levels to market conditions
   - Use percentile-based thresholds

10. **Drawdown protection**
    - Reduce position sizes after 10% portfolio drawdown
    - Pause trading after 20% drawdown

11. **Eliminate duplicate strategies**
    - WAM, Rolling Windows, Monthly Rolling are near-duplicates
    - Keep best performer, remove others

12. **Add max holding period**
    - Force exits after X days (30-60)
    - Prevent dead capital in stagnant positions

---

## Strategy Ranking by Risk Management Quality

| Rank | Strategy | Stop Loss | Position Size | Risk Level |
|------|----------|-----------|---------------|------------|
| 1 | Conservative Income | ✅ 3% | 5% | LOW |
| 2 | Breakout | ✅ 2xATR | 12% | MEDIUM |
| 3 | Mean Reversion | ✅ 5% | 8% | MEDIUM |
| 4-12 | All Others | ❌ NONE | 5-10% | CRITICAL |

---

## Expected Impact of 1-Year Backtest

Testing over 1 year (365 days) instead of 6 months (180 days) will reveal:

1. **Performance across different market regimes**
   - Bull markets (2023 Q4, 2024 Q1)
   - Corrections and volatility (2024 Q2-Q3)
   - Recovery periods (2024 Q4)

2. **Seasonality effects**
   - January effect
   - Summer doldrums
   - Year-end rallies

3. **Drawdown recovery ability**
   - How long to recover from losses
   - Maximum drawdown depth
   - Consecutive losing periods

4. **Strategy correlations**
   - Which strategies perform together
   - Which are truly uncorrelated
   - Portfolio diversification benefits

---

## Next Steps

1. ✅ Configure 1-year backtest (365 days)
2. ⏳ Run complete HPC pipeline
3. ⏳ Generate comprehensive reports
4. ⏳ Analyze results by market regime
5. ⏳ Prioritize strategy fixes based on data
6. ⏳ Implement critical fixes (stop losses first)
7. ⏳ Re-test with fixes applied

---

## Files Modified

- `simulator/simulator.py` - Changed backtest period from 180 to 365 days
  - Line 599: `pd.Timedelta(days=365)`
  - Line 615: `days=365` for SPY data

---

## Conclusion

The root cause of consistent losses is clear: **lack of risk management**. 75% of strategies have no downside protection, allowing small losses to become catastrophic. Combined with overly restrictive entry conditions and no market regime awareness, these strategies are losing money by design.

The 1-year backtest will quantify exactly how much these issues cost and validate which fixes provide the most impact.

**Bottom Line**: Fix stop losses first, then entry logic, then regime filtering. Everything else is optimization.
