# 🔍 Comprehensive System Audit - Critical Findings

## Executive Summary

Your trading system has significant issues that explain the inconsistent metrics (33% returns with 95% drawdown). The problems span the simulator, analysis engine, and visualization layers. This audit identifies root causes and provides a remediation plan.

---

## 🚨 CRITICAL ISSUES FOUND

### Issue #1: Open Positions Not Valued in Analysis ⭐ TOP PRIORITY

**Symptom:** 33% returns but 95% drawdown seems impossible

**Root Cause:** 
- Analysis engine calculates drawdown from portfolio_value in trades table
- But open positions are NOT updated with current market value at analysis time
- Strategy can open 10 positions, each drops 95%, but if 1 position is up 35%, it shows 33% total return
- Drawdown calculation doesn't account for unrealized losses being recovered

**Impact:** High
- All risk metrics are inaccurate when strategies have open positions
- Portfolio_value in database frozen at last closed trade
- Open positions' current values unknown

**Evidence:**
- [trade_metrics.py](calculators/trade_metrics.py#L15): Only counts closed trades for profit factor
- [chart_processor.py](analysis/processors/chart_processor.py#L80): Uses portfolio.portfolio_value which is stale
- SimulationTelemetry doesn't update open positions when generating telemetry

**Solution Needed:**
1. Load current market prices at analysis time
2. Calculate unrealized PnL for all open positions
3. Update portfolio value to include unrealized gains/losses
4. Mark unrealized vs realized gains in database
5. Show both in visualizer with distinction

---

### Issue #2: Missing Stock Performance Data

**Symptom:** "Top/Bottom Stock Performance - No stock performance data available"

**Root Cause:**
- StockPerformanceCalculator likely not implemented or buggy
- Or endpoint not returning data properly
- Charts might be aggregating incorrectly

**Impact:** Medium
- Dashboard can't show which individual stocks performed best/worst
- User can't assess individual stock contribution to strategy

**Files to Check:**
- `analysis/calculators/` - Is there a StockPerformanceCalculator?
- `analysis/analysis_engine.py` - Is it being called?
- `visualizer/routers/strategies.py` - GET /api/charts/{strategy}/stock-performance endpoint

---

### Issue #3: Chart Axis Labels Show 0.0% (or Missing Labels)

**Symptom:** "Some charts on the X axis shows all 0.0%"

**Root Cause:**
- Label generation in chart_processor.py may be using default values
- Or visualizer not formatting percentage labels correctly
- Or monthly_heatmap using incorrect index labels

**Impact:** Medium
- Charts unreadable
- Users can't understand time axis

**Files to Check:**
- [chart_processor.py](analysis/processors/chart_processor.py) - `_process_monthly_heatmap()` 
- `visualizer/static/js/dashboard.js` - chart rendering
- `visualizer/templates/strategy_detail.html` - axis labels

---

### Issue #4: Some Strategies Return No Closed Trades

**Symptom:** Strategies generate buy signals but no closed trades are recorded

**Root Cause:**
- Likely: Sell signal never fires because:
  - Signal logic is incomplete
  - State tracking is broken
  - Signal cancellation happens silently
- Or: Sell signals fire but don't execute because of portfolio rules

**Possible Causes:**
1. **Signal Logic Incomplete** - Strategy doesn't emit sell signal
2. **State Tracking Bug** - Assumes certain conditions that never occur
3. **Signal Chains Broken** - Strategy requires buy before sell but signal timing is off
4. **Silent Cancellations** - `can_generate_signal()` returns False but no log

**Strategies to Audit:**
- strategy_momentum_example.py - Golden cross/death cross
- strategy_500_intersection.py - Crossover logic  
- strategy_WAM.py - Rolling window signals
- strategy_AMIS.py - Multi-indicator strategy

---

### Issue #5: Look-Ahead Bias - POTENTIALLY STILL PRESENT

**Current State:** Simulator CLAIMS to prevent look-ahead bias via:
```python
# Line in simulator.py ~330
historical_data = stock_data.iloc[:i+1]  # Up to current bar only
```

**But Several Red Flags:**
1. Pre-computed indicators might access future data?
   - `indicator_base.py` uses full DataFrame for computation
   - Then selects current bar at runtime
   - Should be safe IF indicators only use .iloc[-1] during simulation

2. Strategy `on_data()` signature changed but not all strategies updated?
   - Some strategies might use old interface

3. No validation that `bar_index` matches data window size

**Solution:**
- Audit every strategy's generate_signal() implementation
- Verify each one ONLY accesses data up to current bar
- Add assertions to prevent future bugs

---

## 📊 SPECIFIC FINDINGS BY COMPONENT

### Simulator (`simulator.py`)

**Status:** ✅ Mostly good, but:

1. **Data Window** (Line 330):
   ```python
   historical_data = stock_data.iloc[:i+1]  # ✅ Correct - includes current bar only
   ```
   This is correct - no look-ahead

2. **SPY Data Alignment** (Line 331):
   ```python
   historical_spy = spy_data.iloc[:i+1] if i < len(spy_data) else spy_data
   ```
   ⚠️ Problem: If SPY data is shorter than stock data, it falls back to full SPY data
   - This could introduce look-ahead bias if SPY is shorter!

3. **Indicator Pre-computation**:
   - Pre-computes on full dataset then reads current bar
   - Should be safe IF indicators don't leak future info
   - Need to verify indicator_base.py

---

### Analysis Engine (`analysis_engine.py`)

**Status:** ⚠️ Issues found

1. **Missing Open Position Valuation**:
   - No mechanism to update open positions with current market prices
   - Portfolio value frozen at last trade

2. **Missing Stock Performance**:
   - Not calling any stock performance calculator
   - Or calculator is broken

3. **No Unrealized P&L**:
   - Database doesn't track unrealized gains/losses
   - Can't calculate accurate drawdown with open positions

---

### Chart Processor (`analysis/processors/chart_processor.py`)

**Status:** ⚠️ Issues found

1. **_process_monthly_heatmap()** (Line ~240):
   - No data? Labels might be month indices instead of month names
   - Check if returns are being calculated

2. **_process_returns_scatter()** (Line ~200):
   - Samples returns into bins
   - But labels might not be proper percentages

3. **Cumulative PnL** (Line ~180):
   - Calculates from trades
   - Doesn't include unrealized positions

---

### Strategies

**Status:** ⚠️ Problems confirmed

1. **Momentum Example** - Appears OK
   - Uses pre-computed SMA and RSI
   - Should generate both buy and sell signals
   - Check: Does it emit HOLD signals when conditions aren't met?

2. **500 Intersection** - ⚠️ Likely issue
   - Complex state tracking (_last_cross_index, _last_cross_was_below)
   - Need to verify slope reversal logic fires correctly
   - Might never emit sell signal in some cases

3. **WAM** (Weekly Threshold) - ⚠️ Likely issue
   - State tracking for weekly/monthly signals
   - Need to verify signal chaining works (buy before sell)

4. **AMIS** - Need to audit

---

## 🔧 REMEDIATION PLAN

### Phase 1: Fix Critical Issues (Do First)

#### 1A. Implement Open Position Valuation
- [ ] Create script to load current market prices
- [ ] Update database schema to track unrealized_pnl
- [ ] Calculate unrealized gains for all open positions
- [ ] Recalculate portfolio_value including unrealized
- [ ] Update analysis engine to use these values
- [ ] Update visualizer to show realized vs unrealized

#### 1B. Fix SPY Data Alignment Bug
- [ ] Ensure SPY data matches stock data length in simulator
- [ ] If mismatched, only use common date range
- [ ] Add assertion to prevent alignment issues

### Phase 2: Fix Data Issues

#### 2A. Debug Strategy Signal Generation
- [ ] Add logging to every strategy's generate_signal()
- [ ] Record when buy/sell signals are generated
- [ ] Record when signals are rejected (can_generate_signal returns False)
- [ ] Run each strategy and check logs for missing sell signals

#### 2B. Fix Chart Data
- [ ] Implement missing stock_performance calculation
- [ ] Fix monthly heatmap labels
- [ ] Fix axis labels (should show month names, not 0.0%)
- [ ] Test all chart types with real data

#### 2C. Fix Metrics Accuracy
- [ ] Verify drawdown calculation with open positions
- [ ] Update profit factor to include unrealized gains
- [ ] Add assertions for sanity checks (e.g., total return >= max_drawdown for reasonable strategies)

### Phase 3: New Features

#### 3A. Create Fibonacci Indicator
- [ ] Implement fibonacci retracement levels
- [ ] Fibonacci extension levels
- [ ] Support other indicators depending on it

#### 3B. Implement New Strategies
- [ ] Strategy #1: Slope reversal vs S&P500 (corrected version)
- [ ] Strategy #2: Weekly/Monthly percentage changes
- [ ] Strategy #3: Monthly percentage changes only
- [ ] Demo strategy using Fibonacci

### Phase 4: Validation

#### 4A. Comprehensive Testing
- [ ] Test each strategy on sample data
- [ ] Verify no look-ahead bias
- [ ] Verify all trades are recorded
- [ ] Verify metrics are reasonable

---

## 📋 DETAILED ISSUE CHECKLIST

### Simulator Issues
- [ ] SPY data alignment with stock data
- [ ] Indicator pre-computation doesn't leak future data
- [ ] All strategies only access data up to current bar
- [ ] Trade rejection reasons logged

### Analysis Engine Issues
- [ ] Open positions valued with current prices ⭐
- [ ] Unrealized P&L calculated separately
- [ ] Drawdown calculation accurate with open positions
- [ ] Stock performance calculated
- [ ] All metrics make mathematical sense
- [ ] NaN/Inf values handled

### Visualizer Issues
- [ ] Stock performance endpoint returning data
- [ ] Chart axis labels correct
- [ ] Monthly heatmap labels showing month names
- [ ] Returns scatter labels showing percentages
- [ ] All optional fields handled gracefully
- [ ] Realized vs unrealized distinction clear

### Strategy Issues
- [ ] All strategies record both buy and sell signals
- [ ] No silent signal rejections
- [ ] State tracking per-symbol correct
- [ ] Signal chaining enforced (buy before sell)
- [ ] No look-ahead bias in any strategy

---

## 🎯 NEXT STEPS

1. **Start with Issue #1** - Open position valuation (explains 33%/95% inconsistency)
2. **Audit strategies** - Identify why some have no closed trades
3. **Fix chart data** - Stock performance and axis labels
4. **Create new strategies** - With proper validation

Should I start implementing these fixes? Which issue would you like me to tackle first?

