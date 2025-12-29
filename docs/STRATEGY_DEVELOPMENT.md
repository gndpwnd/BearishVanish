# Strategy Development Guide

This guide explains how to create custom trading strategies for BearishVanish.

---

## Quick Start

Create a new file in `simulator/strategies/` with the naming convention `strategy_*.py`:

```python
# simulator/strategies/strategy_my_custom.py

from strategy_base import StrategyBase, StrategyConfig

class Strategy(StrategyBase):
    """My custom trading strategy"""

    def __init__(self, config=None):
        super().__init__(config)
        # Custom initialization here
        self.lookback = 20

    def next_bar(self, date, row, portfolio):
        """Process each bar and return trading signal"""
        # Your trading logic here
        if self.should_buy(row):
            return 'BUY'
        elif self.should_sell(row):
            return 'SELL'
        return None

    def should_buy(self, row):
        # Entry conditions
        return row['close'] > row.get('sma_20', row['close'])

    def should_sell(self, row):
        # Exit conditions
        return row['close'] < row.get('sma_20', row['close'])
```

The strategy is automatically discovered and included in simulations.

---

## Strategy Base Class

All strategies inherit from `StrategyBase` which provides:

### Configuration

```python
config = StrategyConfig(
    name="My Strategy",          # Display name
    color="#FF6B6B",             # Chart color
    initial_capital=100000,      # Starting capital
    position_size_pct=0.10,      # 10% per position
    max_positions=10,            # Maximum concurrent positions
    verbose=False                # Enable logging
)

class Strategy(StrategyBase):
    def __init__(self, config=None):
        super().__init__(config)
```

### Available Methods

| Method | Description |
|--------|-------------|
| `next_bar(date, row, portfolio)` | Called for each bar, return 'BUY', 'SELL', or None |
| `log(message)` | Print debug messages (disabled in parallel mode) |
| `get_position(symbol)` | Get current position for symbol |
| `has_position(symbol)` | Check if holding symbol |

### Portfolio Object

The `portfolio` parameter in `next_bar` provides:

```python
portfolio.cash              # Available cash
portfolio.value             # Total portfolio value
portfolio.positions         # Dict of current positions
portfolio.position_count    # Number of open positions
```

---

## Available Indicators

Pre-computed indicators are available in the `row` parameter:

### Moving Averages

```python
row['sma_5']      # 5-day Simple Moving Average
row['sma_10']     # 10-day SMA
row['sma_20']     # 20-day SMA
row['sma_50']     # 50-day SMA
row['sma_200']    # 200-day SMA

row['ema_12']     # 12-day Exponential Moving Average
row['ema_26']     # 26-day EMA
row['ema_50']     # 50-day EMA
```

### Momentum Indicators

```python
row['rsi_14']     # 14-day Relative Strength Index (0-100)
row['rsi_7']      # 7-day RSI

row['macd']       # MACD line
row['macd_signal']  # Signal line
row['macd_hist']  # MACD histogram

row['mfi_14']     # 14-day Money Flow Index
```

### Volatility Indicators

```python
row['bb_upper']   # Bollinger Band upper (2 std)
row['bb_lower']   # Bollinger Band lower (2 std)
row['bb_middle']  # Bollinger Band middle (20-day SMA)

row['atr_14']     # 14-day Average True Range
```

### Volume Indicators

```python
row['volume']           # Raw volume
row['volume_sma_20']    # 20-day volume SMA
row['relative_volume']  # Current volume / average volume
```

### Price Data

```python
row['open']       # Open price
row['high']       # High price
row['low']        # Low price
row['close']      # Close price
row['volume']     # Volume
```

---

## Example Strategies

### RSI Oversold/Overbought

```python
class Strategy(StrategyBase):
    def next_bar(self, date, row, portfolio):
        rsi = row.get('rsi_14')
        if rsi is None:
            return None

        # Buy when RSI < 30 (oversold)
        if rsi < 30 and portfolio.position_count < self.config.max_positions:
            return 'BUY'

        # Sell when RSI > 70 (overbought)
        if rsi > 70 and self.has_position(row['symbol']):
            return 'SELL'

        return None
```

### Moving Average Crossover

```python
class Strategy(StrategyBase):
    def __init__(self, config=None):
        super().__init__(config)
        self.prev_sma_20 = None
        self.prev_sma_50 = None

    def next_bar(self, date, row, portfolio):
        sma_20 = row.get('sma_20')
        sma_50 = row.get('sma_50')

        if sma_20 is None or sma_50 is None:
            return None

        signal = None

        # Golden cross: 20-day crosses above 50-day
        if self.prev_sma_20 and self.prev_sma_50:
            if self.prev_sma_20 < self.prev_sma_50 and sma_20 > sma_50:
                signal = 'BUY'
            # Death cross: 20-day crosses below 50-day
            elif self.prev_sma_20 > self.prev_sma_50 and sma_20 < sma_50:
                signal = 'SELL'

        self.prev_sma_20 = sma_20
        self.prev_sma_50 = sma_50

        return signal
```

### Breakout Strategy

```python
class Strategy(StrategyBase):
    def __init__(self, config=None):
        super().__init__(config)
        self.lookback = 20
        self.highs = []
        self.lows = []

    def next_bar(self, date, row, portfolio):
        close = row['close']
        high = row['high']
        low = row['low']

        # Track highs and lows
        self.highs.append(high)
        self.lows.append(low)

        if len(self.highs) > self.lookback:
            self.highs.pop(0)
            self.lows.pop(0)

        if len(self.highs) < self.lookback:
            return None

        # Breakout above 20-day high
        highest = max(self.highs[:-1])
        if close > highest:
            return 'BUY'

        # Breakdown below 20-day low
        lowest = min(self.lows[:-1])
        if close < lowest:
            return 'SELL'

        return None
```

### Mean Reversion with Bollinger Bands

```python
class Strategy(StrategyBase):
    def next_bar(self, date, row, portfolio):
        close = row['close']
        bb_lower = row.get('bb_lower')
        bb_upper = row.get('bb_upper')

        if bb_lower is None or bb_upper is None:
            return None

        # Buy when price touches lower band
        if close <= bb_lower:
            return 'BUY'

        # Sell when price touches upper band
        if close >= bb_upper:
            return 'SELL'

        return None
```

### Volume-Confirmed Momentum

```python
class Strategy(StrategyBase):
    def next_bar(self, date, row, portfolio):
        rsi = row.get('rsi_14')
        rel_vol = row.get('relative_volume', 1.0)
        sma_20 = row.get('sma_20')
        close = row['close']

        if rsi is None or sma_20 is None:
            return None

        # Strong momentum: RSI > 60, above SMA, high volume
        if rsi > 60 and close > sma_20 and rel_vol > 1.5:
            return 'BUY'

        # Weakness: RSI < 40, below SMA
        if rsi < 40 and close < sma_20:
            return 'SELL'

        return None
```

---

## Best Practices

### 1. Handle Missing Indicators

Always check if indicators exist:

```python
def next_bar(self, date, row, portfolio):
    rsi = row.get('rsi_14')
    if rsi is None:
        return None  # Skip bar if indicator not ready
```

### 2. Avoid Look-Ahead Bias

Only use data up to the current bar:

```python
# WRONG - using future data
if row['next_day_close'] > row['close']:
    return 'BUY'

# CORRECT - using current and past data only
if row['close'] > row.get('sma_20', row['close']):
    return 'BUY'
```

### 3. Respect Position Limits

Check before entering new positions:

```python
def next_bar(self, date, row, portfolio):
    if portfolio.position_count >= self.config.max_positions:
        return None  # Already at max positions

    if self.entry_signal(row):
        return 'BUY'
```

### 4. Use Proper Position Sizing

The `position_size_pct` config is used automatically, but you can override:

```python
# Default: 10% of portfolio per position
config = StrategyConfig(position_size_pct=0.10)

# Smaller positions for higher volatility
config = StrategyConfig(position_size_pct=0.05)
```

### 5. Add Logging for Debugging

```python
def next_bar(self, date, row, portfolio):
    rsi = row.get('rsi_14')

    # This only prints when verbose=True
    self.log(f"{date}: RSI={rsi:.2f}, Close={row['close']:.2f}")

    if rsi < 30:
        self.log(f"BUY signal triggered!")
        return 'BUY'
```

---

## Testing Your Strategy

### Manual Testing

```bash
cd simulator

# Test with small universe first
python main.py --tickers AAPL,GOOGL,MSFT

# Check specific strategy output
python main.py --universe sp500 --offline
```

### Performance Validation

After simulation, check the analysis:

```bash
cd ../analysis
python analysis_engine.py --latest

# View results
cd ../visualizer
python main.py
# Open http://localhost:8000
```

### Key Metrics to Check

| Metric | Good | Warning |
|--------|------|---------|
| Win Rate | > 50% | < 40% |
| Profit Factor | > 1.5 | < 1.0 |
| Sharpe Ratio | > 1.0 | < 0.5 |
| Max Drawdown | < 20% | > 30% |
| Avg Hold Days | Varies | Too short/long |

---

## Adding Custom Indicators

### Method 1: Use Existing Indicator Library

The indicator library is passed to strategies:

```python
class Strategy(StrategyBase):
    def __init__(self, config=None):
        super().__init__(config)

    def calculate_custom_indicator(self, df):
        # Use the indicator library
        sma = self.indicator_library.sma(df['close'], 20)
        return sma
```

### Method 2: Create Custom Indicator File

Create `simulator/indicators/indicator_my_indicator.py`:

```python
import numpy as np
from numba import jit

@jit(nopython=True)
def my_indicator_numba(close, period):
    """Fast Numba implementation"""
    result = np.empty(len(close))
    result[:] = np.nan

    for i in range(period, len(close)):
        # Your calculation here
        result[i] = np.mean(close[i-period:i])

    return result

def my_indicator(df, period=20):
    """Wrapper function"""
    return my_indicator_numba(df['close'].values, period)
```

---

## Common Pitfalls

### 1. Trading on Every Bar

```python
# WRONG - trades too frequently
def next_bar(self, date, row, portfolio):
    if row['close'] > row['open']:
        return 'BUY'
    else:
        return 'SELL'

# BETTER - use thresholds and confirmation
def next_bar(self, date, row, portfolio):
    if row['rsi_14'] < 30 and row['close'] > row['sma_20']:
        return 'BUY'
```

### 2. Ignoring Transaction Costs

The simulator includes transaction cost modeling. Be aware:

- Avoid strategies with very short hold times
- Factor in bid-ask spread for illiquid stocks
- Consider position sizing impact on slippage

### 3. Overfitting to Historical Data

```python
# WRONG - magic numbers from optimization
if row['rsi_14'] < 27.3 and row['sma_17'] > row['sma_43']:
    return 'BUY'

# BETTER - use standard periods
if row['rsi_14'] < 30 and row['sma_20'] > row['sma_50']:
    return 'BUY'
```

### 4. Not Handling Edge Cases

```python
def next_bar(self, date, row, portfolio):
    # Handle potential None/NaN values
    sma = row.get('sma_20')
    if sma is None or np.isnan(sma):
        return None

    # Handle zero prices
    if row['close'] <= 0:
        return None

    # Your logic here
```

---

## Advanced Topics

### Multi-Symbol Correlation

```python
class Strategy(StrategyBase):
    def __init__(self, config=None):
        super().__init__(config)
        self.spy_data = {}

    def set_spy_reference(self, spy_df):
        """Called before simulation with SPY data"""
        for date, row in spy_df.iterrows():
            self.spy_data[date] = row

    def next_bar(self, date, row, portfolio):
        # Check market trend via SPY
        spy = self.spy_data.get(date)
        if spy and spy['close'] < spy.get('sma_200', spy['close']):
            return None  # Don't buy in bear market

        # Continue with normal logic
        if self.entry_signal(row):
            return 'BUY'
```

### Sector Rotation

```python
class Strategy(StrategyBase):
    def __init__(self, config=None):
        super().__init__(config)
        self.sector_momentum = {}

    def update_sector_momentum(self, sector_data):
        """Called with sector ETF data"""
        for sector, df in sector_data.items():
            self.sector_momentum[sector] = df['close'].pct_change(20).iloc[-1]

    def next_bar(self, date, row, portfolio):
        symbol = row.get('symbol', '')
        sector = self.get_sector(symbol)

        # Only trade in top momentum sectors
        if sector not in self.get_top_sectors(3):
            return None

        # Normal entry logic
        if self.entry_signal(row):
            return 'BUY'
```

---

## Strategy Checklist

Before deploying a strategy:

- [ ] No look-ahead bias
- [ ] Handles missing indicator data
- [ ] Respects max positions limit
- [ ] Reasonable trade frequency
- [ ] Tested on out-of-sample data
- [ ] Risk metrics within acceptable range
- [ ] Transaction costs considered
- [ ] Works across market conditions
