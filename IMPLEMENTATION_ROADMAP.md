# 🛠️ Implementation Roadmap - Priority Order

## Phase 1: Fix Critical Issues (Complete Before New Features)

### 1.1 Fix Stock Performance Data [PRIORITY 1]
**Issue:** Empty stock_performance table causing missing dashboard data
**Files:**
- `simulator/simulator.py` - Add write of stock_performance at end of simulation
- `simulator/strategy_tracker.py` - Already has get_stock_performance_summary()

**Implementation:**
1. After running all strategies, call tracker.get_stock_performance_summary() for each strategy
2. Write results to stock_performance table with columns: strategy_name, symbol, num_trades, num_buys, num_sells, total_invested, total_returned, pnl, pnl_pct, win_rate, wins, losses, current_shares
3. Verify data appears in analysis_engine processing

---

### 1.2 Add Open Position Valuation [PRIORITY 1]
**Issue:** Open positions not valued at analysis time - causes 95% drawdown with 33% returns paradox
**Files:**
- Need to refactor analysis to load current prices and calculate unrealized PnL
- Update portfolio_value to include unrealized gains/losses
- Modify all metrics to account for open positions

**Implementation Steps:**
1. Create new utility to load current market prices for all symbols at analysis time
2. Calculate unrealized P&L for all open positions
3. Create "portfolio_with_unrealized" calculation
4. Update all metrics (drawdown, returns, etc.) to use this
5. Add unrealized_pnl column to trades database
6. Mark trades as realized vs unrealized in visualizer

**Challenge:** Need current prices - where from?
- Option A: Use last price from simulation data (frozen at simulation end)
- Option B: User provides snapshot of current prices
- Option C: Download current prices from API

Recommendation: Use last price from simulation data for now (conservative)

---

### 1.3 Fix 500 Intersection Strategy Signal Bug [PRIORITY 2]
**Issue:** May never emit sell signal due to state tracking bug
**Root Cause:** Once stock crosses above S&P, _last_cross_was_below set to False, then keeps checking for sell on every bar with downward slope
**Fix:** Reset cross state after generating signal, or track signal separately

**Current Logic:**
```python
if (self._last_cross_was_below[symbol] is not None and
    not self._last_cross_was_below[symbol] and  # LOOKING FOR UPWARD CROSS
    prev_slope > 0 and curr_slope < 0):        # EVERY DOWNWARD SLOPE
    return 'SELL'
```

This fires every time slope reverses to negative, potentially multiple times per upward cross

**Fix:** Either:
- Track "last_buy_at_index" and only allow ONE sell per upward cross
- Or use per-symbol "can_sell" flag

---

### 1.4 Add Logging to Detect Silent Signal Rejections [PRIORITY 2]
**Issue:** Strategies may generate signals but they're silently rejected
**Files:**
- `simulator/strategy_tracker.py` - can_generate_signal() method
- `simulator/simulator.py` - signal generation loop

**Implementation:**
1. Add DEBUG log when can_generate_signal() returns False
2. Add DEBUG log showing rejection reason
3. Add counter of rejected signals vs accepted signals
4. Report stats at end of simulation: "Signals generated: X, Accepted: Y, Rejected: Z"

---

## Phase 2: Chart/Data Fixes

### 2.1 Fix Chart Axis Labels [PRIORITY 3]
**Issue:** Monthly heatmap showing 0.0% instead of month names
**Files:**
- `analysis/processors/chart_processor.py` - _process_monthly_heatmap()

**Fix:** Ensure labels are formatted as "Jan 2025", "Feb 2025", etc.

---

### 2.2 Implement Stock Performance Visualization [PRIORITY 3]
**Files:**
- `visualizer/routers/strategies.py` - Add endpoint to fetch stock performance
- `visualizer/database/analysis_reader.py` - Add get_stock_performance() method
- `visualizer/static/` - Add table to display per-stock metrics

**Implementation:**
1. Read stock_performance_cache from analysis database
2. Sort by pnl_pct descending
3. Show top 5 winners and top 5 losers
4. Show as table with: Stock, Trades, Profit, Return %, Win Rate

---

## Phase 3: New Strategies & Indicators

### 3.1 Create Fibonacci Indicator [PRIORITY 4]
**File:** `simulator/indicators/fibonacci.py`
**Spec:**
- Function: calculate_fibonacci_levels(data, window=20)
- Inputs: DataFrame with 'close' column, lookback window
- Outputs: Dict with keys: level_0_0, level_0_236, level_0_382, level_0_500, level_0_618, level_0_786, level_1_0
- Should support dependent indicators accessing it

---

### 3.2 Strategy #1: Slope Reversal vs S&P500 [PRIORITY 4]
**File:** `simulator/strategies/strategy_slope_sp500.py`
**Spec:**
- Buy when: Stock crosses below S&P500, then slope reverses upward (only ONE buy per cross)
- Sell when: Stock crosses above S&P500, then slope reverses downward (only ONE sell per cross)
- Must maintain: buy before sell, sell before buy
- Cannot buy if above S&P500
- Cannot sell if below S&P500

---

### 3.3 Strategy #2: Weekly/Monthly Percentage Changes [PRIORITY 4]
**File:** `simulator/strategies/strategy_rolling_threshold.py`
**Spec:**
- 7-day window: Buy on -5%, Sell on +10%
- 30-day window: Buy on -5%, Sell on +10%
- Use rolling windows (streaming data, not calendar dates)
- Chain signals: must have buy before sell, sell before buy
- Per-window tracking

---

### 3.4 Strategy #3: Monthly Only [PRIORITY 4]
**File:** `simulator/strategies/strategy_monthly_threshold.py`
**Spec:**
- Same as Strategy #2 but 30-day window only
- Simpler version for comparison

---

### 3.5 Demo Strategy Using Fibonacci [PRIORITY 4]
**File:** `simulator/strategies/strategy_fibonacci_demo.py`
**Spec:**
- Buy when price touches Fibonacci 0.618 level (reversal indicator)
- Sell when price touches 0.0 level (reversal back up)
- Requires Fibonacci indicator as dependency

---

## Phase 4: Validation & Testing

### 4.1 Create Test Suite [PRIORITY 5]
**File:** `simulator/tests/test_strategies.py` (new)
**Tests:**
1. No look-ahead bias - verify each strategy only accesses data up to current bar
2. All strategies emit both buy and sell signals on sample data
3. Signal chaining enforced - no sell without buy
4. Metrics are reasonable - no -95% return with +35% gain
5. Open positions tracked correctly

### 4.2 Test Each New Strategy [PRIORITY 5]
**Process:**
1. Run on small universe (10 stocks, 90 days)
2. Verify closed trades > 0
3. Verify returns reasonable
4. Verify drawdown makes sense

---

## Implementation Dependencies

```
1.1 Stock Performance Write
   ↓ (needed by)
1.3, 2.1 Analysis fixes
   ↓ (needed by)
2.2 Stock Performance Visualization
   ↓ (ready for)
3.x New Strategies & Indicators

1.2 Open Position Valuation
   ↓ (impacts)
1.4 Logging
   ↓ (helps debug)
3.x New Strategies
```

---

## Quick Reference: What Each Fix Addresses

| Issue | Root Cause | Fix Priority | Files Affected |
|-------|-----------|--------------|------------------|
| 33% returns / 95% drawdown | Open positions not valued | 1.2 | analysis_engine.py, calculators/* |
| Missing stock performance | Empty table in sim DB | 1.1 | simulator.py, strategy_tracker.py |
| No closed trades from strategies | Signal logic bugs + rejections | 1.3, 1.4 | All strategies, strategy_tracker.py |
| 0.0% on chart axis | Label formatting | 2.1 | chart_processor.py |
| Missing top/bottom stocks | Data not written | 1.1 | simulator.py |

---

## Questions Before Implementation

1. **Open Positions Valuation:** Should we use:
   - Last price from simulation data (conservative)?
   - Or require user to provide current prices?
   - Or download current prices from API?

2. **New Strategies:** Should they use pre-computed indicators or inline calculations?

3. **Test Data:** Should I create test strategies first, or just implement and test with real simulation?

Ready to proceed? Where should I start?
