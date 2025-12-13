# Strategy Development Guide

## 📋 Table of Contents
1. [Quick Start](#quick-start)
2. [Strategy Structure](#strategy-structure)
3. [Available Data](#available-data)
4. [Signal Generation Rules](#signal-generation-rules)
5. [Common Patterns](#common-patterns)
6. [Testing & Debugging](#testing--debugging)
7. [Best Practices](#best-practices)

---

## Quick Start

### Minimum Viable Strategy

```python
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from strategy_base import StrategyBase

class Strategy(StrategyBase):
    def __init__(self, color="blue"):
        super().__init__(name="My Strategy", color=color)
    
    def reset(self):
        super().reset()
        # Add your state variables here
        self.my_state = {}
    
    def on_data(self, stock_data, spy_data, current_date, symbol):
        """
        Called once per time step per symbol
        
        Args:
            stock_data: DataFrame with ALL historical data up to current point
            spy_data: DataFrame with ALL historical S&P 500 data up to current point
            current_date: Current simulation date (datetime)
            symbol: Current stock symbol (str)
        
        Returns:
            'BUY', 'SELL', or None
        """
        
        # Your strategy logic here
        if some_buy_condition:
            if self.can_generate_signal('BUY', symbol):
                return self.emit_signal('BUY', symbol)
        
        if some_sell_condition:
            if self.can_generate_signal('SELL', symbol):
                return self.emit_signal('SELL', symbol)
        
        return None
```

Save as `strategies/strategy_myname.py` and it will be auto-loaded!

---

## Strategy Structure

### Required Components

```python
class Strategy(StrategyBase):
    """
    1. __init__: Set strategy name and color
    2. reset: Initialize/reset state variables
    3. on_data: Generate buy/sell signals
    """
    
    def __init__(self, color="blue"):
        super().__init__(name="Strategy Name", color=color)
        # Optional: Set config parameters
        self.threshold = 0.05
    
    def reset(self):
        """Called at start of each simulation"""
        super().reset()
        
        # Symbol-specific state (dict keyed by symbol)
        self.entry_prices = {}
        self.trade_count = {}
        
        # Global state (shared across all symbols)
        self.market_regime = None
    
    def on_data(self, stock_data, spy_data, current_date, symbol):
        """
        Generate signals based on data
        
        IMPORTANT: This is called ONCE per symbol per time step
        All symbols share the same time, but each gets separate call
        """
        
        # Minimum data check
        if len(stock_data) < 20:
            return None
        
        # Your logic here...
        return None  # or 'BUY' or 'SELL'
```

---

## Available Data

### stock_data DataFrame

**Columns:**
- `open`: Opening price
- `high`: High price
- `low`: Low price  
- `close`: Closing price
- `volume`: Trading volume
- `trade_count`: Number of trades (if available)
- `vwap`: Volume-weighted average price (if available)

**Index:** DatetimeIndex with hourly timestamps

**CRITICAL:** This is ALL historical data up to current point (no look-ahead)

```python
# Current values
current_price = stock_data['close'].iloc[-1]
current_volume = stock_data['volume'].iloc[-1]

# Historical values
prices = stock_data['close']
volumes = stock_data['volume']

# Lookback periods
price_7_days_ago = stock_data['close'].iloc[-7*6.5]  # 6.5 hours per day
price_30_bars_ago = stock_data['close'].iloc[-30]

# Slicing (safe - no look-ahead)
recent_20_bars = stock_data.iloc[-20:]
last_week = stock_data.iloc[-35:]  # ~7 days × 5 hours
```

### spy_data DataFrame

Same structure as stock_data, but for S&P 500 (SPY):

```python
spy_price = spy_data['close'].iloc[-1]
spy_returns = spy_data['close'].pct_change()
```

### current_date

Python datetime object representing simulation time:

```python
from datetime import datetime, timedelta

# Date operations
day_of_week = current_date.weekday()  # 0=Monday, 6=Sunday
is_monday = day_of_week == 0

# Compare dates
if current_date > some_entry_date + timedelta(days=30):
    # Held for 30+ days
    pass
```

### symbol

String containing stock ticker:

```python
# Per-symbol state
if symbol not in self.entry_prices:
    self.entry_prices[symbol] = None

# Symbol filtering
if symbol.startswith('A'):
    # Only trade symbols starting with A
    pass
```

---

## Signal Generation Rules

### The Signal Flow

1. **Generate Signal**: Strategy decides BUY/SELL/None
2. **Validation**: `can_generate_signal()` checks if allowed
3. **Emission**: `emit_signal()` records attempt
4. **Execution**: Simulator tries to execute trade
5. **Recording**: If successful, `record_execution()` updates state

### Signal Validation

```python
# WRONG - Don't do this:
return 'BUY'  # Bypasses validation!

# CORRECT - Always use this pattern:
if buy_condition:
    if self.can_generate_signal('BUY', symbol):
        return self.emit_signal('BUY', symbol)
```

### Why Signals Fail

A signal can be **attempted** but **not executed** if:

1. **Max positions reached** (default: 10)
2. **Insufficient cash** for buy
3. **No shares to sell**
4. **Duplicate signal** (can't BUY twice in a row)

**Example:**
```python
# Portfolio has 10 open positions (max)
# Strategy attempts BUY on symbol #11
# Signal is BLOCKED - max positions reached
```

### Tracking Executed vs Attempted

```python
# Check what actually executed
last_signal = self.last_executed_signal.get(symbol)

if last_signal == 'BUY':
    # We actually own shares
    if sell_condition:
        return self.emit_signal('SELL', symbol)

# Debug: See all signal attempts
stats = self.get_debug_stats()
print(f"Attempts: {stats['total_attempts']}")
print(f"Blocks: {stats['total_blocks']}")
```

---

## Common Patterns

### Pattern 1: Simple Threshold Strategy

```python
def on_data(self, stock_data, spy_data, current_date, symbol):
    if len(stock_data) < 2:
        return None
    
    # Calculate daily return
    current_price = stock_data['close'].iloc[-1]
    prev_price = stock_data['close'].iloc[-2]
    daily_return = (current_price - prev_price) / prev_price
    
    # Buy on 2% drop
    if daily_return <= -0.02:
        if self.can_generate_signal('BUY', symbol):
            return self.emit_signal('BUY', symbol)
    
    # Sell on 3% gain (only if we bought)
    if daily_return >= 0.03:
        if (self.last_executed_signal.get(symbol) == 'BUY' and 
            self.can_generate_signal('SELL', symbol)):
            return self.emit_signal('SELL', symbol)
    
    return None
```

### Pattern 2: Moving Average Crossover

```python
def on_data(self, stock_data, spy_data, current_date, symbol):
    if len(stock_data) < 50:
        return None
    
    # Calculate moving averages
    prices = stock_data['close']
    ma_fast = prices.iloc[-20:].mean()  # 20-bar MA
    ma_slow = prices.iloc[-50:].mean()  # 50-bar MA
    
    # Previous MAs
    ma_fast_prev = prices.iloc[-21:-1].mean()
    ma_slow_prev = prices.iloc[-51:-1].mean()
    
    # Detect crossover
    crossed_above = (ma_fast > ma_slow) and (ma_fast_prev <= ma_slow_prev)
    crossed_below = (ma_fast < ma_slow) and (ma_fast_prev >= ma_slow_prev)
    
    if crossed_above and self.can_generate_signal('BUY', symbol):
        return self.emit_signal('BUY', symbol)
    
    if crossed_below and self.can_generate_signal('SELL', symbol):
        return self.emit_signal('SELL', symbol)
    
    return None
```

### Pattern 3: Relative Strength vs S&P 500

```python
def on_data(self, stock_data, spy_data, current_date, symbol):
    if len(stock_data) < 30 or len(spy_data) < 30:
        return None
    
    # Calculate 30-bar returns
    stock_return = (stock_data['close'].iloc[-1] / stock_data['close'].iloc[-30] - 1)
    spy_return = (spy_data['close'].iloc[-1] / spy_data['close'].iloc[-30] - 1)
    
    # Relative strength
    relative_strength = stock_return - spy_return
    
    # Buy if outperforming S&P by 5%+
    if relative_strength > 0.05:
        if self.can_generate_signal('BUY', symbol):
            return self.emit_signal('BUY', symbol)
    
    # Sell if underperforming S&P by 5%+
    if relative_strength < -0.05:
        if (self.last_executed_signal.get(symbol) == 'BUY' and
            self.can_generate_signal('SELL', symbol)):
            return self.emit_signal('SELL', symbol)
    
    return None
```

### Pattern 4: Momentum with Volume Confirmation

```python
def on_data(self, stock_data, spy_data, current_date, symbol):
    if len(stock_data) < 20:
        return None
    
    # Price momentum
    current_price = stock_data['close'].iloc[-1]
    price_10_ago = stock_data['close'].iloc[-10]
    momentum = (current_price - price_10_ago) / price_10_ago
    
    # Volume surge
    current_volume = stock_data['volume'].iloc[-1]
    avg_volume = stock_data['volume'].iloc[-20:].mean()
    volume_ratio = current_volume / avg_volume
    
    # Buy on strong momentum + volume
    if momentum > 0.05 and volume_ratio > 1.5:
        if self.can_generate_signal('BUY', symbol):
            return self.emit_signal('BUY', symbol)
    
    # Sell on momentum reversal
    if momentum < -0.03:
        if (self.last_executed_signal.get(symbol) == 'BUY' and
            self.can_generate_signal('SELL', symbol)):
            return self.emit_signal('SELL', symbol)
    
    return None
```

### Pattern 5: State Machine Strategy

```python
def reset(self):
    super().reset()
    self.state = {}  # Track state per symbol
    self.entry_date = {}

def on_data(self, stock_data, spy_data, current_date, symbol):
    # Initialize state
    if symbol not in self.state:
        self.state[symbol] = 'NEUTRAL'
    
    current_price = stock_data['close'].iloc[-1]
    
    # State machine
    if self.state[symbol] == 'NEUTRAL':
        # Look for entry opportunity
        if some_condition:
            if self.can_generate_signal('BUY', symbol):
                self.state[symbol] = 'LONG'
                self.entry_date[symbol] = current_date
                return self.emit_signal('BUY', symbol)
    
    elif self.state[symbol] == 'LONG':
        # Look for exit opportunity
        days_held = (current_date - self.entry_date[symbol]).days
        
        if exit_condition or days_held > 30:
            if self.can_generate_signal('SELL', symbol):
                self.state[symbol] = 'NEUTRAL'
                return self.emit_signal('SELL', symbol)
    
    return None
```

---

## Testing & Debugging

### Print Debugging

```python
def on_data(self, stock_data, spy_data, current_date, symbol):
    # Conditional printing (only for specific symbols)
    if symbol == 'AAPL':
        print(f"{current_date}: AAPL price = {stock_data['close'].iloc[-1]:.2f}")
    
    # Debug signal generation
    if some_condition:
        print(f"[{symbol}] BUY signal triggered at ${stock_data['close'].iloc[-1]:.2f}")
        
        if self.can_generate_signal('BUY', symbol):
            print(f"  → Signal allowed")
            return self.emit_signal('BUY', symbol)
        else:
            print(f"  → Signal blocked (duplicate or other reason)")
    
    return None
```

### Signal Statistics

```python
# After simulation, check stats
strategy.print_debug_stats()

# Output:
# 📊 Strategy Signal Statistics:
#    Symbols with signal attempts: 347
#    Symbols with executions: 142
#    Total signal attempts: 1,523
#    Total blocked signals: 381
```

### Common Issues

**Issue: "Strategy generates no signals"**
```python
# Check: Are conditions being met?
print(f"Condition A: {condition_a}")
print(f"Condition B: {condition_b}")

# Check: Enough data?
if len(stock_data) < MIN_BARS:
    print(f"Not enough data: {len(stock_data)} < {MIN_BARS}")
    return None
```

**Issue: "Win rate is 0%"**
```python
# Check: Are you generating BOTH buy AND sell signals?
# Can't have wins without completing buy→sell pairs

# Verify both paths exist:
if buy_condition:
    print("BUY path triggered")
if sell_condition:
    print("SELL path triggered")
```

**Issue: "Signals blocked constantly"**
```python
# Check: Are you alternating BUY/SELL properly?
last_signal = self.last_executed_signal.get(symbol)
print(f"Last executed: {last_signal}, trying to: {new_signal}")

# Can't BUY twice or SELL twice in a row!
```

---

## Best Practices

### ✅ DO:

1. **Always validate signals**
   ```python
   if self.can_generate_signal('BUY', symbol):
       return self.emit_signal('BUY', symbol)
   ```

2. **Check minimum data requirements**
   ```python
   if len(stock_data) < 50:
       return None
   ```

3. **Use symbol-specific state**
   ```python
   self.entry_prices[symbol] = current_price
   ```

4. **Track what was EXECUTED, not attempted**
   ```python
   last_signal = self.last_executed_signal.get(symbol)
   ```

5. **Test with small universes first**
   ```bash
   python main.py --tickers AAPL,GOOGL,MSFT  # Test with 3 stocks
   ```

### ❌ DON'T:

1. **Don't look ahead**
   ```python
   # WRONG: Using future data
   next_price = stock_data['close'].iloc[0]  # Index 0 is oldest!
   
   # CORRECT: Only use past data
   current_price = stock_data['close'].iloc[-1]  # -1 is most recent
   ```

2. **Don't bypass validation**
   ```python
   # WRONG:
   return 'BUY'
   
   # CORRECT:
   if self.can_generate_signal('BUY', symbol):
       return self.emit_signal('BUY', symbol)
   ```

3. **Don't use global state for symbol-specific data**
   ```python
   # WRONG:
   self.entry_price = price  # Shared across all symbols!
   
   # CORRECT:
   self.entry_prices[symbol] = price  # Per-symbol tracking
   ```

4. **Don't assume signals execute**
   ```python
   # WRONG:
   self.emit_signal('BUY', symbol)
   self.my_state[symbol] = 'BOUGHT'  # Assumes it worked!
   
   # CORRECT:
   # Check self.last_executed_signal after simulation
   ```

5. **Don't hardcode dates**
   ```python
   # WRONG:
   if current_date == datetime(2024, 1, 15):  # Specific date
   
   # CORRECT:
   if current_date.day == 15:  # Any 15th of month
   ```

---

## Example: Complete Strategy with Best Practices

```python
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from strategy_base import StrategyBase
import numpy as np
from datetime import timedelta

class Strategy(StrategyBase):
    """
    RSI Mean Reversion Strategy
    
    Logic:
    - Buy when RSI < 30 (oversold)
    - Sell when RSI > 70 (overbought) OR after 30 days
    
    Risk Management: None (pure strategy for testing)
    """
    
    def __init__(self, color="purple", rsi_period=14):
        super().__init__(name="RSI Mean Reversion", color=color)
        self.rsi_period = rsi_period
        self.rsi_buy_threshold = 30
        self.rsi_sell_threshold = 70
        self.max_hold_days = 30
    
    def reset(self):
        super().reset()
        self.entry_dates = {}  # Track when we entered
    
    def calculate_rsi(self, prices, period=14):
        """Calculate Relative Strength Index"""
        if len(prices) < period + 1:
            return None
        
        # Calculate price changes
        deltas = prices.diff()
        
        # Separate gains and losses
        gains = deltas.copy()
        losses = deltas.copy()
        gains[gains < 0] = 0
        losses[losses > 0] = 0
        losses = abs(losses)
        
        # Calculate average gains and losses
        avg_gain = gains.rolling(window=period).mean()
        avg_loss = losses.rolling(window=period).mean()
        
        # Calculate RS and RSI
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi.iloc[-1]  # Return current RSI
    
    def on_data(self, stock_data, spy_data, current_date, symbol):
        # Need enough data for RSI calculation
        min_bars = self.rsi_period + 1
        if len(stock_data) < min_bars:
            return None
        
        # Initialize entry date tracking
        if symbol not in self.entry_dates:
            self.entry_dates[symbol] = None
        
        # Calculate RSI
        prices = stock_data['close']
        rsi = self.calculate_rsi(prices, self.rsi_period)
        
        if rsi is None or np.isnan(rsi):
            return None
        
        # ==============================================================
        # BUY LOGIC: RSI indicates oversold
        # ==============================================================
        if rsi < self.rsi_buy_threshold:
            if self.can_generate_signal('BUY', symbol):
                self.entry_dates[symbol] = current_date
                return self.emit_signal('BUY', symbol)
        
        # ==============================================================
        # SELL LOGIC: RSI indicates overbought OR max hold time reached
        # ==============================================================
        if self.last_executed_signal.get(symbol) == 'BUY':
            # Calculate how long we've held
            entry_date = self.entry_dates.get(symbol)
            if entry_date:
                days_held = (current_date - entry_date).days
            else:
                days_held = 0
            
            # Sell if overbought or held too long
            if (rsi > self.rsi_sell_threshold or days_held >= self.max_hold_days):
                if self.can_generate_signal('SELL', symbol):
                    self.entry_dates[symbol] = None
                    return self.emit_signal('SELL', symbol)
        
        return None
```

---

## Advanced Topics

### Using Technical Indicators

Many strategies use technical indicators. Here's how to implement common ones:

```python
def calculate_sma(self, prices, period):
    """Simple Moving Average"""
    return prices.iloc[-period:].mean()

def calculate_ema(self, prices, period):
    """Exponential Moving Average"""
    return prices.ewm(span=period, adjust=False).mean().iloc[-1]

def calculate_bollinger_bands(self, prices, period=20, num_std=2):
    """Bollinger Bands"""
    sma = prices.iloc[-period:].mean()
    std = prices.iloc[-period:].std()
    upper = sma + (std * num_std)
    lower = sma - (std * num_std)
    return upper, sma, lower

def calculate_atr(self, stock_data, period=14):
    """Average True Range (volatility)"""
    high = stock_data['high']
    low = stock_data['low']
    close = stock_data['close']
    
    tr1 = high - low
    tr2 = abs(high - close.shift())
    tr3 = abs(low - close.shift())
    
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()
    
    return atr.iloc[-1]
```

### Multi-Timeframe Analysis

```python
def on_data(self, stock_data, spy_data, current_date, symbol):
    # Short-term: 20 bars
    short_term_return = (stock_data['close'].iloc[-1] / 
                         stock_data['close'].iloc[-20] - 1)
    
    # Medium-term: 50 bars
    medium_term_return = (stock_data['close'].iloc[-1] / 
                          stock_data['close'].iloc[-50] - 1)
    
    # Long-term: 200 bars
    long_term_return = (stock_data['close'].iloc[-1] / 
                        stock_data['close'].iloc[-200] - 1)
    
    # Buy only if all timeframes are positive
    if (short_term_return > 0 and 
        medium_term_return > 0 and 
        long_term_return > 0):
        # Strong uptrend across all timeframes
        pass
```

---

## Quick Reference

### Data Access Cheat Sheet

```python
# Current values
current_price = stock_data['close'].iloc[-1]
current_volume = stock_data['volume'].iloc[-1]
current_high = stock_data['high'].iloc[-1]
current_low = stock_data['low'].iloc[-1]

# Historical values
all_prices = stock_data['close']
all_volumes = stock_data['volume']

# Lookback (N bars ago)
price_n_ago = stock_data['close'].iloc[-n]

# Time slicing
last_20_bars = stock_data.iloc[-20:]
last_week = stock_data.iloc[-35:]  # ~7 days

# Calculations
returns = stock_data['close'].pct_change()
log_returns = np.log(stock_data['close'] / stock_data['close'].shift(1))
volatility = returns.std()
```

### Signal Generation Cheat Sheet

```python
# Standard pattern
if condition:
    if self.can_generate_signal('BUY', symbol):
        return self.emit_signal('BUY', symbol)

# Check last executed signal
last = self.last_executed_signal.get(symbol)
if last == 'BUY':
    # We own shares
    pass

# State tracking
self.my_state[symbol] = some_value

# Debugging
stats = self.get_debug_stats()
self.print_debug_stats()
```

---

## Summary

1. **Inherit from `StrategyBase`**
2. **Implement `on_data()` method**
3. **Always validate signals** with `can_generate_signal()`
4. **Emit signals** with `emit_signal()`
5. **Use symbol-specific state** (dicts keyed by symbol)
6. **Test with small datasets first**
7. **Check debug stats** to verify strategy is working

Your strategy is now ready to test! 🚀