# How to Fix Losing Strategies - Step-by-Step Guide

## 🎯 Your Goal: Consistent Monthly Gains

**REALITY CHECK:** There's no "guaranteed 1% monthly" strategy. But we CAN build strategies that:
- Target 0.5-1.0% monthly (6-12% annually)
- Have <15% max drawdown
- Win >55% of trades
- Provide smooth, consistent gains

This beats most retail traders and matches many hedge funds.

---

## 📊 STEP 1: Diagnose WHY Your Strategies Are Failing

### Run the Diagnostic Tool

```bash
cd simulator

# First, run a simulation to get a database
python main.py --strategies "Mean Reversion,Trend Following" \
               --universe SP500_TOP_50 \
               --force-liquidate

# Then diagnose it
python strategy_diagnostics.py --db simulations/latest.db
```

### What the Diagnostic Tool Shows:

**1. Trade Execution Analysis**
- Are you generating signals?
- Are trades being rejected?
- Why are they rejected?

**Common Issue:** "NO TRADE ATTEMPTS"
→ **Fix:** Your indicator thresholds are too strict!

**2. Win/Loss Profile**
- Win rate
- Average win vs average loss
- Risk/reward ratio

**Common Issue:** "Average loss > Average win"
→ **Fix:** Add stop-losses immediately!

**3. Signal Generation**
- BUY vs SELL balance
- Signal frequency

**Common Issue:** "Only 5 BUY signals in 180 days"
→ **Fix:** Relax entry conditions!

**4. Risk Management**
- Max drawdown
- Sharpe ratio
- Total return

**Common Issue:** "Max drawdown 95%"
→ **Fix:** No stop-losses! Add 3-5% stops!

**5. Market Conditions**
- Test period
- Market regime

**Common Issue:** "Only tested 2024"
→ **Fix:** Test from 2022 (includes bear market)!

---

## 🔧 STEP 2: Common Fixes for Your Issues

### Issue: "Small winners, big losers"

**DIAGNOSIS:** No stop-losses or they're too wide

**FIXES:**
1. Add 3-5% stop-loss on ALL positions
2. Set profit targets at 2x the stop (6-10% targets)
3. Exit losers FAST, let winners run

**Example Fix:**
```python
# In your strategy's generate_signal():

if self._in_position[symbol]:
    entry_price = self._entry_prices[symbol]
    pnl_pct = (current_price - entry_price) / entry_price

    # STOP-LOSS: Exit if down 3%
    if pnl_pct <= -0.03:
        return 'SELL'

    # PROFIT TARGET: Exit if up 6%
    if pnl_pct >= 0.06:
        return 'SELL'
```

### Issue: "Strategies don't generate signals"

**DIAGNOSIS:** Indicator thresholds too strict

**FIXES:**
1. Relax ADX threshold: 25 → 20
2. Relax volume threshold: 1.5x → 1.1x
3. Use OR logic instead of AND for some conditions
4. Lower RSI oversold: 30 → 35

**Example Fix:**
```python
# BEFORE (too strict - ALL must be true):
if (adx > 25 and
    supertrend_bullish and
    ema_20 > ema_50 and
    price > vwap and
    volume > 1.5):
    return 'BUY'

# AFTER (relaxed - use OR for some):
if (adx > 20 and  # Relaxed from 25
    supertrend_bullish and
    (ema_20 > ema_50 or price > vwap) and  # OR instead of AND
    volume > 1.1):  # Relaxed from 1.5
    return 'BUY'
```

### Issue: "Low win rate (<50%)"

**DIAGNOSIS:** Entry criteria not selective enough OR exiting winners too early

**FIXES:**
1. Add trend filter (only buy if price > 50-SMA)
2. Wait for confirmation (2 bars instead of 1)
3. Let winners run longer (raise profit target)

**Example Fix:**
```python
# Add trend filter
sma_50 = data['sma_50'].iloc[-1]
if current_price < sma_50:
    return 'HOLD'  # Don't fight the trend

# Wait for confirmation
if condition_met:
    # Don't buy immediately, wait for next bar
    self._pending_signal[symbol] = True
    return 'HOLD'

if self._pending_signal[symbol] and condition_still_met:
    self._pending_signal[symbol] = False
    return 'BUY'
```

---

## 🎯 STEP 3: Use the Conservative Income Strategy

I've created a strategy specifically for your goals: **Conservative Income**

### Features:
- **Small position size:** 5% (vs 10-12% in aggressive strategies)
- **Tight stop-loss:** 3% (cuts losses fast)
- **Quick profit targets:** 6% (2:1 risk/reward)
- **Time exit:** Exits after 5 days (no holding losers)
- **Relaxed entry:** Easier to generate signals
- **Trend filter:** Only trades with the trend

### Run it:
```bash
cd simulator
python main.py --strategies "Conservative Income" \
               --universe SP500_TOP_50 \
               --force-liquidate
```

### Expected Results (REALISTIC):
- **Monthly return:** 0.5-1.0% (some months negative!)
- **Annual return:** 6-12%
- **Max drawdown:** 10-15%
- **Win rate:** 55-65%
- **Sharpe ratio:** 0.8-1.2

**This will NOT make you rich quickly, but it will grind upward consistently.**

---

## 📅 STEP 4: Test Over Realistic Time Periods

### Problem: You're only testing last 6 months (2024 bull market)

**2024 Market:** Strong bull market, everything goes up
→ Strategies that work in 2024 may FAIL in bear markets

### SOLUTION: Test from 2022

```bash
# Get data from 2022 (includes bear market)
python main.py --strategies "Conservative Income" \
               --universe SP500_TOP_50 \
               --days 730 \  # 2 years
               --force-liquidate
```

### Why This Matters:
- **2022:** Bear market (-20% S&P 500)
- **2023:** Recovery (+24% S&P 500)
- **2024:** Bull continuation (+25% S&P 500)

A strategy that works in ALL THREE periods is robust!

---

## 🔄 STEP 5: Iterate and Improve

### Process:
1. **Run diagnostic tool** → Find specific issues
2. **Make ONE change at a time** → Don't change everything
3. **Re-run simulation** → Test the change
4. **Compare results** → Did it improve?
5. **Repeat** → Keep improving

### Example Iteration:

**Iteration 1:** Baseline
- Run simulation
- Result: 5 trades, -10% return, 30% drawdown

**Iteration 2:** Add stop-losses
- Change: Add 5% stop-loss
- Result: 5 trades, -5% return, 15% drawdown
- Improvement: ✅ Drawdown cut in half!

**Iteration 3:** Relax entry thresholds
- Change: Lower ADX from 25 → 20
- Result: 15 trades, +2% return, 12% drawdown
- Improvement: ✅ More trades, positive returns!

**Iteration 4:** Tighten stop-loss
- Change: Stop-loss from 5% → 3%
- Result: 15 trades, +5% return, 8% drawdown
- Improvement: ✅ Better returns, lower drawdown!

---

## ⚠️ Common Mistakes to Avoid

### 1. Over-Optimization (Curve Fitting)
**Bad:** Tweaking parameters until backtest shows 100% win rate
**Good:** Find parameters that work across MULTIPLE time periods

### 2. Unrealistic Expectations
**Bad:** "I need 1% monthly guaranteed"
**Good:** "I'll target 0.5-1.0% monthly with some losing months"

### 3. Testing Only Bull Markets
**Bad:** Only test 2024 data
**Good:** Test 2022-2024 (bear + bull + recovery)

### 4. Too Many Indicators
**Bad:** Using 10 indicators, all must be perfect
**Good:** 3-4 key indicators with relaxed thresholds

### 5. No Risk Management
**Bad:** "I don't use stop-losses, I hold forever"
**Good:** "3% stop on all positions, no exceptions"

### 6. Chasing Perfect Trades
**Bad:** Waiting for the "perfect" setup (never comes)
**Good:** Taking good-enough setups frequently

---

## 📈 Realistic Return Expectations

### Conservative Strategy:
- **Monthly:** 0.3-0.8% (some months negative)
- **Annual:** 4-10%
- **Drawdown:** <15%
- **Sharpe:** 0.8-1.2

### Moderate Strategy:
- **Monthly:** 0.5-1.5%
- **Annual:** 6-18%
- **Drawdown:** 15-25%
- **Sharpe:** 0.6-1.0

### Aggressive Strategy:
- **Monthly:** 1.0-3.0% (very volatile)
- **Annual:** 12-36%
- **Drawdown:** 25-40%
- **Sharpe:** 0.4-0.8

**For "consistent monthly gains," aim for Conservative or Moderate.**

---

## 🎓 Next Steps

1. **Run diagnostics on your existing strategies:**
   ```bash
   python strategy_diagnostics.py --db simulations/latest.db
   ```

2. **Test Conservative Income strategy:**
   ```bash
   python main.py --strategies "Conservative Income" --universe SP500_TOP_50 --force-liquidate
   ```

3. **Analyze results:**
   ```bash
   cd ../analysis
   python analysis_engine.py --latest
   ```

4. **Compare to S&P 500:**
   - If your strategy beats S&P 500 (risk-adjusted), you're winning!
   - S&P 500 averages ~10% annually with ~15% drawdowns

5. **Iterate based on diagnostics:**
   - Fix one issue at a time
   - Re-test
   - Compare results

---

## 📞 When You Need Help

If strategies still fail after following this guide:

1. **Share diagnostic output** - Run the diagnostic tool and share results
2. **Describe specific issues** - "Win rate 30%, avg loss $500, avg win $200"
3. **Ask targeted questions** - "Should I relax RSI threshold or add trend filter?"

**Remember:** Building profitable strategies takes time and iteration. There's no magic bullet!

---

**Good luck! Focus on consistent small gains, not home runs.** 🎯
