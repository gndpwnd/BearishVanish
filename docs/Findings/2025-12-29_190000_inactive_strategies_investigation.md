# Inactive Strategies Investigation: Why 8 Strategies Generated 0 Trades

**Date**: 2025-12-29 19:00:00
**Type**: Root Cause Analysis
**Priority**: CRITICAL - Must fix before strategy optimization

---

## Executive Summary

Investigated why 8 strategies generated 0 trades during the real data test (Jul-Dec 2025). Root causes fall into three categories:

| Category | Strategies | Fix Complexity |
|----------|------------|----------------|
| **Logical Contradictions** | Mean Reversion, Conservative Income | Easy |
| **State Machine Restrictions** | 500 Intersection, SP500 Slope v2 | Easy |
| **Indicator Issues** | Trend Following, AMIS, Momentum MFI | Medium |
| **Overly Strict Thresholds** | Breakout | Easy |

---

## Market Context (Jul-Dec 2025)

| Metric | Value | Implication |
|--------|-------|-------------|
| SPY Return | +10.77% | Bull market throughout |
| RSI < 30 | 13.48% of bars | Oversold conditions rare |
| ADX > 25 | 70.32% of bars | Strong trends common |
| Volume > 1.5x avg | 27.39% of bars | Volume spikes regular |

---

## Strategy-by-Strategy Root Causes

### 1. Mean Reversion - LOGICAL CONTRADICTION

**BUY Requirements**:
- Price < Bollinger Band Lower (oversold)
- Price > VWAP (contradicts above!)
- RSI < 30
- Volume > 1.2x

**Problem**: When price is 2 std below the 20-period mean (BB lower), it is almost NEVER above VWAP.

**Fix**:
```python
# Remove the VWAP requirement (line ~140)
# above_vwap = current_price > vwap  # DELETE THIS
```

**Expected Impact**: +100-300 trades

---

### 2. Conservative Income - LOGICAL CONTRADICTION

**BUY Requirements (Pattern 1)**:
- Price < Bollinger Band Lower * 1.01 (oversold)
- Price > SMA50 (contradicts above!)
- RSI < 35

**Problem**: When price is below BB lower, it's almost always below SMA50 too.

**Fix**:
```python
# Use SMA20 instead of SMA50 for Pattern 1
above_20_sma = current_price > sma_20  # Was sma_50
```

**Expected Impact**: +50-100 trades

---

### 3. 500 Intersection & SP500 Slope v2 - STATE MACHINE RESTRICTION

**BUY Requirements**:
- Stock crosses below S&P 500 performance
- Only ONE signal allowed per cross event
- Slope must reverse from negative to positive

**Problem**: The "one-signal-per-cross" restriction prevents additional entries even when conditions remain valid.

**Fix**:
```python
# Replace line 156:
# self._last_signal_index[symbol] < self._last_cross_index[symbol]
# With cooldown instead:
bar_index - self._last_signal_index.get(symbol, -999) > 24  # 24-hour cooldown
```

**Expected Impact**: +10-30 trades each

---

### 4. Breakout - OVERLY STRICT THRESHOLDS

**BUY Requirements**:
- Price breaks 20-day high
- Volume > 1.5x average (too strict)
- ADX > 20
- Price > VWAP
- NEW breakout (previous bar was NOT a breakout)

**Problem**: Volume threshold of 1.5x is too strict; 27% of bars meet this vs 35% at 1.2x.

**Fix**:
```python
self.volume_breakout_threshold = 1.2  # Was 1.5
```

**Expected Impact**: +80-200 trades

---

### 5. Trend Following - INDICATOR AVAILABILITY

**BUY Requirements**:
- ADX > 25
- Supertrend bullish (direction > 0)
- EMA(20) > EMA(50)
- Price > VWAP
- Plus DI > Minus DI

**Problem**: Supertrend indicator returns NaN values, causing early exit.

**Fix**:
```python
# Make Supertrend optional (line ~117)
if np.isnan(supertrend_direction):
    bullish_supertrend = ema_fast > ema_slow  # Use EMA as proxy
else:
    bullish_supertrend = supertrend_direction > 0
```

**Expected Impact**: +50-150 trades

---

### 6. AMIS - INDICATOR COLUMN NAMES

**Problem**: Strategy expects specific column names (`sma_20`, `rsi_14`, etc.) that may not exist in the pre-computed indicators DataFrame.

**Fix**:
```python
# Use .get() with fallbacks
fast_ma = data.get(f'sma_{self.fast_ma}',
                   data['close'].rolling(self.fast_ma).mean()).iloc[-1]
```

**Expected Impact**: +200-500 trades

---

### 7. Momentum MFI - MULTIPLE STRICT CONDITIONS

**BUY Requirements**:
- MFI between 20-50
- Price > SMA50
- OBV rising in 2 of last 3 bars
- Supertrend bullish
- ADX > 20

**Problem**: OBV rising requirement + Supertrend + ADX creates too narrow a window.

**Fix**:
```python
# Relax OBV requirement
obv_rising = self._obv_history[symbol][-1] > self._obv_history[symbol][0]  # Net positive

# Lower ADX threshold
self.adx_threshold = 15  # Was 20
```

**Expected Impact**: +50-150 trades

---

## Priority Ranking

### HIGH (Quick Wins - Implement First)

| Strategy | Fix | Expected Trades |
|----------|-----|-----------------|
| Mean Reversion | Remove VWAP requirement | +100-300 |
| Conservative Income | Use SMA20 instead of SMA50 | +50-100 |
| 500 Intersection | Add cooldown, remove one-per-cross | +10-30 |
| SP500 Slope v2 | Add cooldown, remove one-per-cross | +10-30 |
| Breakout | Lower volume from 1.5x to 1.2x | +80-200 |

### MEDIUM (Requires More Testing)

| Strategy | Fix | Expected Trades |
|----------|-----|-----------------|
| Momentum MFI | Relax OBV, lower ADX | +50-150 |
| Trend Following | Make Supertrend optional | +50-150 |
| AMIS | Fix indicator column mapping | +200-500 |

---

## Total Expected Impact

If all fixes are implemented:
- **Current trades**: 4 strategies, ~200 trades total
- **After fixes**: 12 strategies, ~800-1,800 trades total
- **Improvement**: 4x-9x increase in trade volume

---

## Next Steps

1. Implement HIGH priority fixes first
2. Run pipeline with real data
3. Verify each strategy now generates trades
4. Analyze new performance metrics
5. Iterate on threshold tuning

---

*Generated by BearishVanish Strategy Investigation*
