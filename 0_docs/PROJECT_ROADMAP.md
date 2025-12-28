# BearishVanish Project Roadmap

## Vision

**Goal:** Achieve consistent 1% monthly returns (12%+ annually) with controlled risk.

**Metrics:**
- Monthly return average: ≥ 1%
- Maximum drawdown: ≤ 15%
- Sharpe ratio: ≥ 1.0
- Losing months per year: ≤ 4

---

## Current State Assessment

### What We Have
- Simulation engine with parallel processing
- 12 trading strategies (momentum, mean reversion, trend following)
- Analysis engine with 50+ metrics
- Interactive web dashboard
- HPC deployment scripts (fully functional)
- Multi-threading configuration for HPC (48 workers default)

### Completed Fixes (2024-12-28)

| Issue | Status | Impact |
|-------|--------|--------|
| Sharpe ratio annualization (Issue #10) | FIXED | Correct 252-day annualization |
| Daily return calculation (Issue #1) | FIXED | Portfolio-level returns |
| Unrealized P&L (Issue #9) | FIXED | Included in total return |
| Timestamp consistency (Issue #8) | FIXED | Simulation time, not wall-clock |
| Offline mode API init | FIXED | Works without API keys |
| HPC multi-threading | ADDED | --sim-workers flag, auto-detect |

### Remaining Improvements

| Component | Issues | Priority |
|-----------|--------|----------|
| Strategies | Some entry logic contradictory | MEDIUM |
| Visualizer | Chart caching not used | LOW |
| Testing | Unit tests needed for calculators | MEDIUM |

---

## Phase 1: Foundation Fixes - COMPLETED (2024-12-28)

### 1.1 Fix Critical Accuracy Issues - DONE

**Simulator Fixes (All Completed):**

| Issue | File | Status |
|-------|------|--------|
| Daily return calculation | simulator.py:449-477 | FIXED - Uses portfolio value change |
| Multi-symbol portfolio value | simulator.py:452 | FIXED - Correct valuation |
| Timestamp consistency | simulator.py:354, 498 | FIXED - Uses simulation time |
| Offline mode API init | data_manager.py:34 | FIXED - No API needed offline |

**Analysis Fixes (All Completed):**

| Issue | File | Status |
|-------|------|--------|
| Sharpe annualization | risk_metrics.py | FIXED - Uses 252 trading days/year |
| Unrealized P&L | analysis_engine.py | FIXED - Includes open positions |
| Risk-free rate | risk_metrics.py | FIXED - Configurable, 4% default |

### 1.2 Add Multi-Threading Configuration - DONE

```python
# Added to simulator/main.py
parser.add_argument('--sim-workers', type=int, default=None,
                    help='Parallel workers (default: auto, 48 for HPC)')

# HPC script auto-detects and sets 48 workers for 192-core system
```

### 1.3 HPC Environment - CONFIGURED

- Python module loading for ctypes support
- Virtual environment with all dependencies
- Scripts tested and working
- **Blocking:** Need market data (download or sync from source with API keys)

### 1.4 Validation Tests - PENDING

- [ ] Create unit tests for each calculator
- [ ] Compare Sharpe calculation to manual calculation
- [ ] Verify daily returns sum to total return
- [ ] Test with known benchmark (SPY buy-and-hold)

---

## Phase 2: Risk Management Improvements (Weeks 3-4)

### 2.1 Add Volatility-Scaled Position Sizing

**New file:** `simulator/risk_management.py`

```python
def volatility_scaled_position(target_vol, realized_vol, base_size=0.10):
    """Scale position by inverse volatility."""
    scalar = target_vol / realized_vol if realized_vol > 0 else 1.0
    return min(base_size * scalar, 0.20)  # Max 20% per position

def calculate_portfolio_heat(positions, stops):
    """Calculate total portfolio risk."""
    return sum(size * abs(stop_pct) for size, stop_pct in zip(positions, stops))
```

### 2.2 Add ATR-Based Stops

**Update:** `simulator/strategy_base.py`

```python
def get_atr_stop(self, entry_price, atr, multiplier=2.5):
    """Calculate stop-loss using ATR."""
    return entry_price - (atr * multiplier)

def get_trailing_stop(self, current_price, highest_price, atr, multiplier=2.0):
    """Calculate trailing stop."""
    return highest_price - (atr * multiplier)
```

### 2.3 Add Regime Detection

**New file:** `simulator/regime_detector.py`

```python
def detect_regime(spy_data):
    """Detect market regime from SPY data."""
    price = spy_data['close'].iloc[-1]
    ma_50 = spy_data['close'].rolling(50).mean().iloc[-1]
    ma_200 = spy_data['close'].rolling(200).mean().iloc[-1]
    vol_20d = spy_data['close'].pct_change().rolling(20).std().iloc[-1] * np.sqrt(252)

    if price > ma_200 and ma_50 > ma_200 and vol_20d < 0.20:
        return 'BULL_LOW_VOL'
    elif price > ma_200 and vol_20d >= 0.20:
        return 'BULL_HIGH_VOL'
    elif price < ma_200:
        return 'BEAR'
    else:
        return 'TRANSITION'
```

---

## Phase 3: Strategy Improvements (Weeks 5-8)

### 3.1 Fix Existing Strategy Issues

**Mean Reversion (`strategy_mean_reversion.py`):**
- Remove contradictory `above_vwap` condition
- Change to: `(price < BB_lower) OR (RSI < 35 AND volume_spike)`

**Trend Following (`strategy_trend_following.py`):**
- Add dual momentum check (stock AND SPY positive)
- Add volatility scaling

**Conservative Income (`strategy_conservative_income.py`):**
- Add trailing stops after 3% profit
- Consider ATR-based stops instead of fixed %

### 3.2 Implement New Strategies

**Priority 1: Low Volatility Strategy**
```
Entry: Hold stocks in lowest 20% volatility (60-day)
Exit: Monthly rebalance
Expected: 8-10% annual, low drawdown
```

**Priority 2: Quality + Momentum**
```
Screen: ROE > 15%, Debt/Equity < 0.5
Filter: 12-month return > 0
Rebalance: Monthly
Expected: 12-15% annual, moderate drawdown
```

**Priority 3: Dual Momentum**
```
Monthly check:
- If SPY 12-month return > AGG: Run stock strategies
- If AGG > SPY: Conservative only or cash
- If both negative: Cash
```

### 3.3 Strategy Combination Framework

**New file:** `simulator/strategy_ensemble.py`

```python
class StrategyEnsemble:
    def __init__(self, strategies, weights=None):
        self.strategies = strategies
        self.weights = weights or [1/len(strategies)] * len(strategies)

    def get_signal(self, date, row, portfolio):
        """Combine signals from multiple strategies."""
        signals = []
        for strategy, weight in zip(self.strategies, self.weights):
            sig = strategy.next_bar(date, row, portfolio)
            signals.append((sig, weight))

        # Voting logic
        buy_weight = sum(w for sig, w in signals if sig == 'BUY')
        sell_weight = sum(w for sig, w in signals if sig == 'SELL')

        if buy_weight > 0.5 and sell_weight == 0:
            return 'BUY'
        elif sell_weight > 0.3:
            return 'SELL'
        return None
```

---

## Phase 4: Indicator Improvements (Weeks 9-12)

### 4.1 Add Missing Indicators

**Evidence-based indicators to add:**

| Indicator | Purpose | Implementation |
|-----------|---------|----------------|
| Rate of Change (ROC) | Simple momentum | `(close - close[n]) / close[n]` |
| On-Balance Volume (OBV) | Volume trend | Cumulative volume direction |
| Relative Strength (vs SPY) | Sector leadership | `stock_return / spy_return` |
| Market Breadth | Market filter | `% stocks > 50-day MA` |

### 4.2 Indicator Dependency System

**New file:** `simulator/indicator_dependencies.py`

```python
INDICATOR_GRAPH = {
    # Level 0: Raw data (no dependencies)
    'close': [],
    'volume': [],

    # Level 1: Simple calculations
    'sma_20': ['close'],
    'ema_12': ['close'],
    'true_range': ['high', 'low', 'close'],

    # Level 2: Composite
    'rsi_14': ['close'],
    'atr_14': ['true_range'],
    'bollinger': ['sma_20'],

    # Level 3: Complex
    'macd': ['ema_12', 'ema_26'],
    'adx': ['atr_14'],

    # Level 4: Custom
    'regime': ['sma_50', 'sma_200', 'atr_14'],
}

def compute_in_order(df, required_indicators):
    """Compute indicators respecting dependencies."""
    computed = set(['close', 'high', 'low', 'volume'])
    queue = list(required_indicators)

    while queue:
        indicator = queue.pop(0)
        deps = INDICATOR_GRAPH.get(indicator, [])

        if all(d in computed for d in deps):
            df[indicator] = calculate_indicator(df, indicator)
            computed.add(indicator)
        else:
            queue.append(indicator)  # Try later
```

### 4.3 Custom Indicator Development

**Create composite indicators:**

1. **Trend Strength Index:**
   - Combines ADX, MA slope, and momentum
   - Output: 0-100 scale

2. **Volume-Confirmed Momentum:**
   - RSI + Volume confirmation
   - Higher confidence entries

3. **Regime-Adjusted RSI:**
   - RSI with dynamic thresholds based on volatility
   - Lower threshold in high-vol environments

---

## Phase 5: Analysis Improvements (Weeks 13-16)

### 5.1 Trade-Level Analysis

**Add to analysis calculators:**

| Analysis | Purpose | Implementation |
|----------|---------|----------------|
| Entry quality score | Rate entry timing | Compare to optimal entry in window |
| Exit quality score | Rate exit timing | Compare to optimal exit |
| Trade attribution | What caused P&L | Decompose into factors |
| Slippage estimate | Realistic costs | Model based on volume |

### 5.2 Portfolio-Level Analysis

**Add metrics:**

| Metric | Description |
|--------|-------------|
| Concentration risk | Largest positions as % |
| Sector exposure | Breakdown by sector |
| Correlation matrix | Strategy correlations |
| Regime performance | Returns by market regime |

### 5.3 Walk-Forward Validation

**New analysis mode:**

```python
def walk_forward_analysis(simulation_db, train_years=3, test_years=1):
    """
    Validate strategy robustness with walk-forward.

    Example: 2015-2024 data
    - Train: 2015-2017, Test: 2018
    - Train: 2016-2018, Test: 2019
    - Train: 2017-2019, Test: 2020
    ...
    """
    results = []
    # Implementation...
    return results
```

---

## Phase 6: Visualizer Improvements (Weeks 17-18)

### 6.1 Performance Fixes

- [ ] Use `chart_cache` table (already computed, not used)
- [ ] Add response caching for expensive queries
- [ ] Pagination for large trade lists

### 6.2 New Visualizations

| Chart | Purpose |
|-------|---------|
| Regime overlay | Show regime on equity curve |
| Correlation heatmap | Strategy correlations |
| Factor exposure | Breakdown by factors |
| Walk-forward results | Out-of-sample performance |

### 6.3 Comparison Features

- [ ] Side-by-side strategy comparison
- [ ] Blend analysis (what-if combinations)
- [ ] Benchmark comparison (SPY, AGG)

---

## Phase 7: Research & Validation (Ongoing)

### 7.1 Strategy Research Protocol

1. **Hypothesis:** Define what you're testing
2. **Backtest:** Run on S&P 500, 2015-2024
3. **Analyze:** Check all metrics
4. **Validate:** Walk-forward test
5. **Document:** Save to `0_docs/Findings/`

### 7.2 Continuous Improvement

**Monthly tasks:**
- [ ] Review strategy performance
- [ ] Check for overfitting signs
- [ ] Update regime detection
- [ ] Document new findings

**Quarterly tasks:**
- [ ] Re-run walk-forward validation
- [ ] Recalibrate parameters if needed
- [ ] Add new strategies based on research
- [ ] Clean up underperforming strategies

---

## Milestone Targets

| Milestone | Target Date | Success Criteria |
|-----------|-------------|------------------|
| Foundation fixes complete | Week 2 | All HIGH priority issues fixed |
| Risk management added | Week 4 | Vol scaling, ATR stops working |
| 3 strategies improved | Week 6 | Better backtested metrics |
| 2 new strategies added | Week 8 | Low vol, quality+momentum working |
| Walk-forward validated | Week 12 | T-stat > 2.0 for main strategies |
| 1% monthly achieved | Week 16 | Average 1% monthly in backtest |

---

## Success Metrics

### Primary Goals (Must Achieve)

| Metric | Target | How to Measure |
|--------|--------|----------------|
| Average monthly return | ≥ 1% | Analysis DB |
| Maximum drawdown | ≤ 15% | Drawdown calculator |
| Sharpe ratio | ≥ 1.0 | Risk metrics (corrected) |
| Losing months | ≤ 4/year | Monthly returns |

### Secondary Goals (Nice to Have)

| Metric | Target | How to Measure |
|--------|--------|----------------|
| Win rate | ≥ 50% | Trade metrics |
| Profit factor | ≥ 1.5 | Trade metrics |
| Statistical significance | T-stat > 2.0 | Walk-forward analysis |
| Regime robustness | Works in bull/bear | Regime analysis |

---

## Resource Requirements

### HPC Usage

- **Simulation:** Use 48-96 workers for S&P 500 backtests
- **Expected time:** ~5-10 minutes for full S&P 500 simulation
- **Storage:** ~500MB per simulation database

### Development Time

- **Phase 1-2:** 20-30 hours (critical fixes)
- **Phase 3-4:** 40-60 hours (strategy/indicator work)
- **Phase 5-6:** 20-30 hours (analysis/viz improvements)
- **Phase 7:** Ongoing (research)

---

## Risk Factors

### Technical Risks

| Risk | Mitigation |
|------|------------|
| Overfitting to historical data | Walk-forward validation, simple rules |
| Bug in calculations | Unit tests, benchmark comparisons |
| HPC failures | Local backup testing, checkpoints |

### Strategy Risks

| Risk | Mitigation |
|------|------------|
| Market regime change | Regime detection, strategy diversification |
| Crowded trades | Avoid obvious signals, use proprietary indicators |
| Black swan events | Stop losses, position sizing, max heat |

---

## Next Steps

### Immediate (Blocking):
1. **Configure API access** for market data download:
   ```bash
   # On HPC: Create .env file with Alpaca credentials
   ssh nelsg10@vegaln1.erau.edu
   cd /home2/nelsg10/BearishVanish
   echo "ALPACA_API_KEY=your_key" > .env
   echo "ALPACA_SECRET_KEY=your_secret" >> .env
   ```

2. **Download market data:**
   ```bash
   ./hpc_scripts/run_simulation.sh sp500 --download
   ```

3. **Run simulation:**
   ```bash
   ./hpc_scripts/run_simulation.sh sp500 --offline --sim-workers=48
   ```

### This Week:
- Run full S&P 500 simulation on HPC
- Analyze results with corrected metrics
- Validate Sharpe ratios are now reasonable
- Document findings in Findings folder

### Next Week:
- Add volatility-scaled position sizing (Phase 2)
- Implement ATR-based stops

### This Month:
- Improve 3 existing strategies (Phase 3)
- Add low volatility strategy
- Run walk-forward validation
