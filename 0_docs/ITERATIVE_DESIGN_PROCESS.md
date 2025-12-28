# Iterative Design Process for Trading Strategies

A systematic approach to developing, testing, and refining trading strategies.

---

## Overview

The iterative design process follows a cycle:

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│    ┌──────────┐     ┌──────────┐     ┌──────────┐          │
│    │ DESIGN   │────▶│  BUILD   │────▶│  TEST    │          │
│    │ Indicator│     │ Strategy │     │ Backtest │          │
│    └──────────┘     └──────────┘     └──────────┘          │
│         ▲                                  │                │
│         │                                  ▼                │
│    ┌──────────┐     ┌──────────┐     ┌──────────┐          │
│    │  REFINE  │◀────│ DOCUMENT │◀────│ ANALYZE  │          │
│    │ Improve  │     │ Findings │     │ Metrics  │          │
│    └──────────┘     └──────────┘     └──────────┘          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Phase 1: Indicator Design

### 1.1 Identify the Signal

Before writing code, define:

- **What market condition are you trying to detect?**
  - Trend direction? Momentum strength? Overbought/oversold?
  - Volume surge? Volatility expansion? Support/resistance?

- **What data will you use?**
  - Price (OHLC)
  - Volume
  - Other indicators (dependencies)

- **What is the expected output?**
  - Continuous value (like RSI 0-100)
  - Binary signal (buy/sell)
  - Probability score

### 1.2 Research Existing Indicators

Check if similar indicators exist:

```python
# Common indicator categories

# Trend Indicators
- SMA, EMA (Moving Averages)
- MACD (Trend + Momentum)
- ADX (Trend Strength)
- Parabolic SAR

# Momentum Indicators
- RSI (Relative Strength Index)
- Stochastic Oscillator
- MFI (Money Flow Index)
- ROC (Rate of Change)

# Volatility Indicators
- Bollinger Bands
- ATR (Average True Range)
- Keltner Channels

# Volume Indicators
- OBV (On Balance Volume)
- VWAP
- Volume Profile
- Accumulation/Distribution
```

### 1.3 Design Indicator Dependencies

Some indicators depend on others:

```
Simple Indicators (no dependencies):
├── SMA
├── EMA
├── Volume SMA
└── True Range

Composite Indicators (with dependencies):
├── MACD (requires EMA)
├── Bollinger Bands (requires SMA, StdDev)
├── RSI (requires price changes)
└── ADX (requires True Range, DM)

Complex Indicators (multi-level dependencies):
├── Stochastic RSI (requires RSI, Stochastic)
├── MACD Histogram Divergence (requires MACD, price)
└── Custom Composite (your design)
```

### 1.4 Implement with Numba

For performance, use Numba JIT compilation:

```python
# simulator/indicators/indicator_my_custom.py

import numpy as np
from numba import jit

@jit(nopython=True)
def my_indicator_core(close: np.ndarray, period: int) -> np.ndarray:
    """
    Core calculation with Numba JIT.

    Args:
        close: Array of closing prices
        period: Lookback period

    Returns:
        Array of indicator values
    """
    n = len(close)
    result = np.empty(n)
    result[:] = np.nan  # Initialize with NaN

    for i in range(period, n):
        # Your calculation here
        window = close[i-period:i]
        result[i] = np.mean(window)  # Example

    return result


def my_indicator(df, period=20):
    """
    Wrapper function for DataFrame input.
    """
    return my_indicator_core(df['close'].values, period)
```

### 1.5 Validate Indicator

Before using in strategy:

```python
# Test indicator against known values
import pandas as pd
import numpy as np

# Create test data
test_data = pd.DataFrame({
    'close': [100, 102, 101, 103, 105, 104, 106, 108, 107, 109]
})

# Calculate indicator
result = my_indicator(test_data, period=3)

# Verify: SMA(3) at index 3 should be (100+102+101)/3 = 101
assert abs(result[2] - 101.0) < 0.001, "Indicator calculation incorrect"
```

---

## Phase 2: Strategy Design

### 2.1 Define Entry/Exit Rules

Document your rules clearly:

```markdown
## Strategy: RSI Mean Reversion

### Entry Conditions (ALL must be true):
1. RSI(14) < 30 (oversold)
2. Price > SMA(50) (still in uptrend)
3. Volume > 1.5x average (confirmation)

### Exit Conditions (ANY triggers exit):
1. RSI(14) > 70 (overbought)
2. Price drops 3% below entry (stop loss)
3. Held for 10+ days (time stop)
```

### 2.2 Implement Strategy

```python
# simulator/strategies/strategy_rsi_mean_reversion.py

from strategy_base import StrategyBase, StrategyConfig

class Strategy(StrategyBase):
    """RSI Mean Reversion Strategy"""

    def __init__(self, config=None):
        super().__init__(config)
        self.entry_prices = {}  # Track entry for stop loss

    def next_bar(self, date, row, portfolio):
        symbol = row.get('symbol', 'UNKNOWN')

        # Get indicator values
        rsi = row.get('rsi_14')
        sma_50 = row.get('sma_50')
        rel_volume = row.get('relative_volume', 1.0)
        close = row['close']

        # Skip if indicators not ready
        if rsi is None or sma_50 is None:
            return None

        # Check if we have a position
        has_position = self.has_position(symbol)

        # EXIT LOGIC
        if has_position:
            entry_price = self.entry_prices.get(symbol, close)

            # Exit 1: RSI overbought
            if rsi > 70:
                del self.entry_prices[symbol]
                return 'SELL'

            # Exit 2: Stop loss (3%)
            if close < entry_price * 0.97:
                del self.entry_prices[symbol]
                return 'SELL'

            # Exit 3: Time stop (handled by framework)

        # ENTRY LOGIC
        else:
            # Check all entry conditions
            if (rsi < 30 and
                close > sma_50 and
                rel_volume > 1.5 and
                portfolio.position_count < self.config.max_positions):

                self.entry_prices[symbol] = close
                return 'BUY'

        return None
```

### 2.3 Parameter Documentation

Document all tunable parameters:

```python
# Strategy parameters with defaults and ranges
PARAMETERS = {
    'rsi_period': {
        'default': 14,
        'range': (5, 30),
        'description': 'RSI calculation period'
    },
    'rsi_oversold': {
        'default': 30,
        'range': (20, 40),
        'description': 'RSI threshold for oversold condition'
    },
    'rsi_overbought': {
        'default': 70,
        'range': (60, 80),
        'description': 'RSI threshold for overbought condition'
    },
    'stop_loss_pct': {
        'default': 0.03,
        'range': (0.01, 0.10),
        'description': 'Stop loss percentage below entry'
    },
    'volume_threshold': {
        'default': 1.5,
        'range': (1.0, 3.0),
        'description': 'Minimum relative volume for entry'
    }
}
```

---

## Phase 3: Backtesting

### 3.1 Choose Test Universe

| Universe | Symbols | Use Case |
|----------|---------|----------|
| Small (5-10) | AAPL, GOOGL, MSFT, etc. | Quick iteration |
| Medium (30) | Dow 30 | Initial validation |
| Large (100) | NASDAQ 100 | Broader test |
| Full (500) | S&P 500 | Final validation |

### 3.2 Run Backtest

```bash
cd simulator

# Quick test (5 stocks, fast iteration)
python main.py --tickers AAPL,GOOGL,MSFT,NVDA,META --offline

# Medium test (Dow 30)
python main.py --universe dow30 --offline

# Full test (S&P 500)
python main.py --universe sp500 --offline

# For HPC (with multi-threading)
python main.py --universe sp500 --offline --workers 48
```

### 3.3 Run Analysis

```bash
cd ../analysis
python analysis_engine.py --latest
```

---

## Phase 4: Analysis & Metrics

### 4.1 Key Metrics to Evaluate

**Primary Goal Metrics:**
| Metric | Target | Your Result |
|--------|--------|-------------|
| Monthly Return (avg) | ≥ 1% | ____% |
| Annual Return | ≥ 12% | ____% |
| Max Drawdown | ≤ 15% | ____% |
| Sharpe Ratio | ≥ 1.0 | ____ |
| Losing Months | ≤ 3/year | ____ |

**Secondary Metrics:**
| Metric | Acceptable | Your Result |
|--------|------------|-------------|
| Win Rate | ≥ 45% | ____% |
| Profit Factor | ≥ 1.3 | ____ |
| Avg Hold Days | 5-20 | ____ |
| Max Consecutive Losses | ≤ 5 | ____ |

### 4.2 View Dashboard

```bash
cd ../visualizer
python main.py
# Open http://localhost:8000
```

### 4.3 Key Charts to Review

1. **Equity Curve** - Is growth consistent or erratic?
2. **Drawdown Chart** - How deep and long are drawdowns?
3. **Monthly Returns Heatmap** - Any seasonal patterns?
4. **Trade Distribution** - Are wins larger than losses?

---

## Phase 5: Document Findings

### 5.1 Create Finding Document

Save to `0_docs/Findings/strategies/[category]/`:

```markdown
# RSI Mean Reversion - S&P 500 Backtest

**Date:** 2024-12-28
**Universe:** S&P 500
**Period:** 2020-01-01 to 2024-12-01

## Summary
RSI mean reversion strategy shows promise but needs volatility filter.

## Results

| Metric | Value |
|--------|-------|
| Total Return | 45.3% |
| Annualized | 11.2% |
| Sharpe Ratio | 0.89 |
| Max Drawdown | 18.2% |
| Win Rate | 52% |

## What Worked
- Entry on RSI < 30 with volume confirmation effective
- SMA filter prevented many false signals

## What Didn't Work
- Too many trades during high volatility (March 2020)
- Stop loss triggered too often (3% too tight)

## Next Steps
- [ ] Add volatility filter (ATR-based)
- [ ] Test wider stop loss (5%)
- [ ] Add market regime filter (SPY trend)
```

---

## Phase 6: Refine & Iterate

### 6.1 Common Refinements

| Issue | Possible Refinement |
|-------|---------------------|
| Too many trades | Add confirmation filter |
| Too few trades | Loosen entry conditions |
| Stops triggered often | Widen stop or use ATR-based |
| Profits given back | Add trailing stop or time exit |
| Poor in volatility | Add VIX filter |
| Poor in trends | Add trend confirmation |

### 6.2 A/B Testing Parameters

Create variants and compare:

```python
# Test different RSI thresholds
variants = [
    {'rsi_oversold': 25, 'rsi_overbought': 75},
    {'rsi_oversold': 30, 'rsi_overbought': 70},  # baseline
    {'rsi_oversold': 35, 'rsi_overbought': 65},
]

# Run each variant and compare
for v in variants:
    # Modify strategy parameters
    # Run backtest
    # Record results
```

### 6.3 Walk-Forward Validation

To avoid overfitting:

1. **In-sample period:** Optimize parameters (2020-2022)
2. **Out-of-sample period:** Test with optimized params (2023-2024)
3. **Compare:** If out-of-sample is >70% of in-sample performance, strategy is robust

---

## Indicator Dependency Management

### Dependency Graph

When building complex indicators:

```
Level 0 (Raw Data):
├── close
├── high
├── low
├── volume

Level 1 (Simple):
├── sma_20 (depends: close)
├── ema_12 (depends: close)
├── true_range (depends: high, low, close)

Level 2 (Composite):
├── rsi_14 (depends: close changes)
├── bollinger (depends: sma_20, std_dev)
├── atr_14 (depends: true_range)

Level 3 (Complex):
├── macd (depends: ema_12, ema_26)
├── stoch_rsi (depends: rsi_14)
├── adx (depends: +DI, -DI, which depend on atr)

Level 4 (Custom):
├── your_indicator (depends: any combination)
```

### Calculating Dependencies in Order

```python
def compute_all_indicators(df):
    """Compute indicators in dependency order."""

    # Level 1
    df['sma_20'] = calculate_sma(df, 20)
    df['ema_12'] = calculate_ema(df, 12)
    df['ema_26'] = calculate_ema(df, 26)
    df['true_range'] = calculate_true_range(df)

    # Level 2 (depends on Level 1)
    df['rsi_14'] = calculate_rsi(df, 14)
    df['atr_14'] = calculate_atr(df, 14)  # uses true_range
    df['bb_upper'], df['bb_lower'] = calculate_bollinger(df, 20)

    # Level 3 (depends on Level 2)
    df['macd'] = df['ema_12'] - df['ema_26']
    df['macd_signal'] = calculate_ema(df['macd'], 9)
    df['adx'] = calculate_adx(df, 14)

    # Level 4 (custom, depends on any previous)
    df['my_indicator'] = my_custom_indicator(df)

    return df
```

---

## Checklist Before Moving to Production

- [ ] Backtest on 5+ years of data
- [ ] Test across multiple market conditions (bull, bear, sideways)
- [ ] Walk-forward validation passed
- [ ] Sharpe ratio > 1.0 out-of-sample
- [ ] Max drawdown < 20%
- [ ] At least 100+ trades for statistical significance
- [ ] No curve-fitting (simple, robust rules)
- [ ] Transaction costs accounted for
- [ ] Slippage considered for illiquid stocks
- [ ] Strategy documented in Findings folder
