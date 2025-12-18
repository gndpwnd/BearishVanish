# 🚀 Strategy Development Guide

## Overview

This guide shows you how to create profitable trading strategies for the BearishVanish simulator. The system is designed to be modular, allowing you to focus on signal generation without worrying about data management, performance optimization, or metrics calculation.

---

## Quick Start: Your First Strategy

Here's a minimal working strategy:

```python
# File: simulator/strategies/strategy_my_first_strategy.py

from strategy_base import StrategyBase, StrategyConfig

class Strategy(StrategyBase):
    """My first trading strategy"""
    
    def __init__(self, config: StrategyConfig = None):
        if config is None:
            config = StrategyConfig(
                name="My First Strategy",
                initial_capital=100000,
                position_size_pct=0.10,
                max_positions=10
            )
        super().__init__(config)
    
    def generate_signal(self, symbol, data, spy_data, bar_index):
        """
        Generate trading signals
        
        Args:
            symbol: Stock ticker (e.g., 'AAPL')
            data: DataFrame with all historical data up to current bar
            spy_data: S&P 500 historical data (for correlation/comparison)
            bar_index: Current bar index in the data
        
        Returns:
            'BUY', 'SELL', or 'HOLD'
        """
        if len(data) < 2:
            return 'HOLD'
        
        current_price = data['close'].iloc[-1]
        previous_price = data['close'].iloc[-2]
        
        # Simple strategy: buy if price goes up, sell if goes down
        if current_price > previous_price:
            return 'BUY'
        elif current_price < previous_price:
            return 'SELL'
        else:
            return 'HOLD'
```

Save this as `simulator/strategies/strategy_my_first_strategy.py` and run the simulator. Your strategy will automatically be discovered and tested!

---

## Understanding the Data Available

### Market Data (in `data` DataFrame)

When your `generate_signal()` method is called, the `data` parameter contains all historical data for that symbol up to (and including) the current bar. Each row represents one trading day:

#### OHLCV Data (Always Available)
```python
data['open']      # Open price
data['high']      # High price
data['low']       # Low price
data['close']     # Close price
data['volume']    # Trading volume (number of shares)
data['trade_count']  # Number of trades
```

#### Pre-computed Indicators (Available)
```python
# Simple Moving Averages
data['sma_20']    # 20-day simple moving average
data['sma_50']    # 50-day simple moving average
data['sma_200']   # 200-day simple moving average

# Exponential Moving Averages
data['ema_12']    # 12-day exponential moving average
data['ema_26']    # 26-day exponential moving average

# Relative Strength Index
data['rsi_14']    # RSI with 14-day period

# Bollinger Bands
data['bb_middle']  # Middle band (20-day SMA)
data['bb_upper']   # Upper band
data['bb_lower']   # Lower band
data['bb_width']   # Width of bands

# Volume Indicators
data['on_balance_volume']  # OBV
data['volume_sma_20']      # 20-day volume average

# Additional metrics
data['daily_return_pct']   # Daily percentage return
```

#### Index Data
```python
data.index         # DatetimeIndex with trading dates
data.index.year    # Year
data.index.month   # Month (1-12)
data.index.day     # Day of month
```

#### Duration/Timing
```python
len(data)          # Number of bars (days) in historical data
len(data) - 1      # Index of current bar (0-based)
data.index[-1]     # Current date
```

### SPY Benchmark Data (in `spy_data` DataFrame)

The `spy_data` parameter contains S&P 500 data for the same date range:

```python
# Same columns as market data
spy_data['close']        # SPY close price
spy_data['volume']       # SPY volume
spy_data['sma_20']       # SPY 20-day moving average
# ... all same indicators available
```

---

## Common Data Access Patterns

### Current vs Historical Data

**Important: Simulation prevents look-ahead bias!**

Each call to `generate_signal()` receives ONLY data up to the current bar. You cannot see future prices.

```python
def generate_signal(self, symbol, data, spy_data, bar_index):
    # ✅ GOOD: Access current/past data
    current_price = data['close'].iloc[-1]      # Current bar (latest)
    yesterday_price = data['close'].iloc[-2]    # Previous bar
    week_ago_price = data['close'].iloc[-5]     # 5 bars ago
    
    # ✅ GOOD: Use iloc with negative indices (from end)
    last_20_closes = data['close'].iloc[-20:]   # Last 20 bars
    
    # ✅ GOOD: Use loc with actual dates
    all_jan_data = data.loc['2024-01-01':'2024-01-31']
    
    # ❌ WRONG: This will raise an error or give 0 rows
    try:
        future_data = data.iloc[len(data)+5]  # IndexError!
    except IndexError:
        pass  # Out of bounds
    
    return 'HOLD'
```

### Working with Time Windows

```python
def generate_signal(self, symbol, data, spy_data, bar_index):
    if len(data) < 20:
        return 'HOLD'  # Need minimum 20 bars of history
    
    # Get data windows relative to today (last bar)
    recent_high = data['high'].iloc[-10:].max()  # Max of last 10 bars
    recent_low = data['low'].iloc[-10:].min()    # Min of last 10 bars
    
    # Calculate simple statistics
    avg_volume_20d = data['volume'].iloc[-20:].mean()
    current_volume = data['volume'].iloc[-1]
    
    if current_volume > 2 * avg_volume_20d:
        return 'BUY'  # High volume spike
    
    return 'HOLD'
```

### Comparing to SPY (Benchmark)

```python
def generate_signal(self, symbol, data, spy_data, bar_index):
    if len(data) < 50 or len(spy_data) < 50:
        return 'HOLD'
    
    # Calculate cumulative returns
    stock_return = (data['close'].iloc[-1] - data['close'].iloc[-50]) / data['close'].iloc[-50]
    spy_return = (spy_data['close'].iloc[-1] - spy_data['close'].iloc[-50]) / spy_data['close'].iloc[-50]
    
    # Buy stocks outperforming SPY
    if stock_return > spy_return:
        return 'BUY'
    else:
        return 'SELL'
    
    return 'HOLD'
```

---

## Working with Pre-computed Indicators

### Using Included Indicators

Indicators are automatically pre-computed and added to the data:

```python
def generate_signal(self, symbol, data, spy_data, bar_index):
    if len(data) < 50:
        return 'HOLD'
    
    # Golden Cross: 20-day SMA crosses above 50-day SMA
    sma_20 = data['sma_20'].iloc[-1]
    sma_50 = data['sma_50'].iloc[-1]
    
    sma_20_prev = data['sma_20'].iloc[-2]
    sma_50_prev = data['sma_50'].iloc[-2]
    
    # Cross detection
    if sma_20_prev <= sma_50_prev and sma_20 > sma_50:
        return 'BUY'  # Golden cross
    
    if sma_20_prev >= sma_50_prev and sma_20 < sma_50:
        return 'SELL'  # Death cross
    
    return 'HOLD'
```

### RSI Strategy

```python
def generate_signal(self, symbol, data, spy_data, bar_index):
    if len(data) < 14:
        return 'HOLD'  # RSI needs 14 bars
    
    rsi = data['rsi_14'].iloc[-1]
    
    if rsi < 30:
        return 'BUY'   # Oversold
    elif rsi > 70:
        return 'SELL'  # Overbought
    
    return 'HOLD'
```

### Bollinger Bands

```python
def generate_signal(self, symbol, data, spy_data, bar_index):
    if len(data) < 20:
        return 'HOLD'
    
    current_price = data['close'].iloc[-1]
    bb_upper = data['bb_upper'].iloc[-1]
    bb_lower = data['bb_lower'].iloc[-1]
    
    if current_price < bb_lower:
        return 'BUY'   # Below lower band
    elif current_price > bb_upper:
        return 'SELL'  # Above upper band
    
    return 'HOLD'
```

---

## Building Custom Indicators

While the system includes common indicators, you can build your own or use custom ones:

```python
def generate_signal(self, symbol, data, spy_data, bar_index):
    if len(data) < 5:
        return 'HOLD'
    
    # Calculate custom momentum indicator
    closes = data['close'].values
    current_momentum = (closes[-1] - closes[-5]) / closes[-5] * 100
    
    if current_momentum > 5:
        return 'BUY'   # Strong upward momentum
    elif current_momentum < -5:
        return 'SELL'  # Strong downward momentum
    
    return 'HOLD'
```

For more complex indicators, see `./simulator/indicator_development_guide.md`.

---

## State Management (Important!)

When a strategy holds positions, it needs to manage state across multiple signals. The system provides a framework:

```python
class Strategy(StrategyBase):
    def __init__(self, config: StrategyConfig = None):
        if config is None:
            config = StrategyConfig(name="State Example")
        super().__init__(config)
        
        # Initialize per-symbol state tracking
        self._position_state = {}  # Dict to track if we own each symbol
    
    def generate_signal(self, symbol, data, spy_data, bar_index):
        # Initialize this symbol's state if needed
        if symbol not in self._position_state:
            self._position_state[symbol] = 'NEUTRAL'
        
        current_state = self._position_state[symbol]
        current_price = data['close'].iloc[-1]
        
        # State machine: NEUTRAL → BOUGHT → SOLD → NEUTRAL
        if current_state == 'NEUTRAL':
            if current_price < 100:
                self._position_state[symbol] = 'BOUGHT'
                return 'BUY'
        
        elif current_state == 'BOUGHT':
            if current_price > 110:  # Take profit
                self._position_state[symbol] = 'NEUTRAL'
                return 'SELL'
            elif current_price < 95:  # Stop loss
                self._position_state[symbol] = 'NEUTRAL'
                return 'SELL'
        
        return 'HOLD'
```

---

## Signal Generation Best Practices

### Rule #1: Prevent Multiple Signals Per Event

Don't emit BUY on every rising bar after initial buy signal:

```python
# ❌ WRONG: Emits BUY every rising bar
def generate_signal(self, symbol, data, spy_data, bar_index):
    if data['close'].iloc[-1] > data['close'].iloc[-2]:
        return 'BUY'  # This fires EVERY rising day
    return 'HOLD'

# ✅ RIGHT: Emit BUY only at crossover
def generate_signal(self, symbol, data, spy_data, bar_index):
    if len(data) < 2:
        return 'HOLD'
    
    if not hasattr(self, '_last_signal_was_buy'):
        self._last_signal_was_buy = {}
    
    if symbol not in self._last_signal_was_buy:
        self._last_signal_was_buy[symbol] = False
    
    # Emit BUY only on upward cross (not every rising bar)
    crossing_up = (data['close'].iloc[-2] <= data['sma_20'].iloc[-2] and
                   data['close'].iloc[-1] > data['sma_20'].iloc[-1])
    
    if crossing_up and not self._last_signal_was_buy[symbol]:
        self._last_signal_was_buy[symbol] = True
        return 'BUY'
    
    # Reset flag when crossing down
    crossing_down = (data['close'].iloc[-2] >= data['sma_20'].iloc[-2] and
                     data['close'].iloc[-1] < data['sma_20'].iloc[-1])
    
    if crossing_down:
        self._last_signal_was_buy[symbol] = False
    
    return 'HOLD'
```

### Rule #2: Require Sufficient History

Always check you have enough data before accessing indicators:

```python
def generate_signal(self, symbol, data, spy_data, bar_index):
    # ✅ Always check length first
    if len(data) < 50:
        return 'HOLD'  # Not enough data yet
    
    # Now safe to access 50-day indicators
    return 'BUY' if data['sma_20'].iloc[-1] > data['sma_50'].iloc[-1] else 'HOLD'
```

### Rule #3: Consistent Signal Chaining

Buy before sell, sell before buy:

```python
class Strategy(StrategyBase):
    def __init__(self, config=None):
        super().__init__(config or StrategyConfig(name="Chaining Example"))
        self._has_position = {}  # Track if we own stock
    
    def generate_signal(self, symbol, data, spy_data, bar_index):
        if symbol not in self._has_position:
            self._has_position[symbol] = False
        
        # Only allow SELL if we own it, only allow BUY if we don't
        if not self._has_position[symbol]:
            if is_bullish(data):
                self._has_position[symbol] = True
                return 'BUY'
        else:
            if is_bearish(data):
                self._has_position[symbol] = False
                return 'SELL'
        
        return 'HOLD'

def is_bullish(data):
    return data['close'].iloc[-1] > data['sma_20'].iloc[-1]

def is_bearish(data):
    return data['close'].iloc[-1] < data['sma_20'].iloc[-1]
```

---

## Common Strategies to Implement

### 1. Moving Average Crossover (Golden Cross)

```python
def generate_signal(self, symbol, data, spy_data, bar_index):
    if len(data) < 50:
        return 'HOLD'
    
    sma_20 = data['sma_20']
    sma_50 = data['sma_50']
    
    # Golden Cross: 20 crosses above 50
    if sma_20.iloc[-2] <= sma_50.iloc[-2] and sma_20.iloc[-1] > sma_50.iloc[-1]:
        return 'BUY'
    
    # Death Cross: 20 crosses below 50
    if sma_20.iloc[-2] >= sma_50.iloc[-2] and sma_20.iloc[-1] < sma_50.iloc[-1]:
        return 'SELL'
    
    return 'HOLD'
```

### 2. RSI Overbought/Oversold

```python
def generate_signal(self, symbol, data, spy_data, bar_index):
    if len(data) < 14:
        return 'HOLD'
    
    rsi = data['rsi_14'].iloc[-1]
    
    if rsi < 30:
        return 'BUY'
    elif rsi > 70:
        return 'SELL'
    
    return 'HOLD'
```

### 3. Bollinger Bands Reversal

```python
def generate_signal(self, symbol, data, spy_data, bar_index):
    if len(data) < 20:
        return 'HOLD'
    
    price = data['close'].iloc[-1]
    bb_upper = data['bb_upper'].iloc[-1]
    bb_lower = data['bb_lower'].iloc[-1]
    
    if price < bb_lower:
        return 'BUY'
    elif price > bb_upper:
        return 'SELL'
    
    return 'HOLD'
```

### 4. Relative Strength vs Benchmark

```python
def generate_signal(self, symbol, data, spy_data, bar_index):
    if len(data) < 20 or len(spy_data) < 20:
        return 'HOLD'
    
    stock_momentum = (data['close'].iloc[-1] - data['close'].iloc[-20]) / data['close'].iloc[-20]
    spy_momentum = (spy_data['close'].iloc[-1] - spy_data['close'].iloc[-20]) / spy_data['close'].iloc[-20]
    
    if stock_momentum > spy_momentum:
        return 'BUY'
    else:
        return 'SELL'
    
    return 'HOLD'
```

---

## Testing Your Strategy

To test your strategy:

```bash
cd /home/dev/BearishVanish/simulator

# Run simulation with your strategy
python3 main.py --offline --tickers AAPL,MSFT,GOOGL,TSLA

# The system will automatically load your strategy
# Results will appear in simulation database
```

To analyze results:

```bash
cd /home/dev/BearishVanish/analysis

# Analyze results
python3 analysis_engine.py --latest

# Results will include your strategy's performance metrics
```

---

## Advanced Features

### Configuration Options

```python
config = StrategyConfig(
    name="Advanced Strategy",
    initial_capital=100000,           # Starting cash
    position_size_pct=0.10,           # Percent of capital per trade
    max_positions=10,                 # Max concurrent positions
    stop_loss_pct=0.05,              # Stop loss at 5% loss
    take_profit_pct=0.10,            # Take profit at 10% gain
    allow_shorting=False,            # Can't sell short
    max_leverage=1.0                 # No margin
)
```

### Accessing Indicator Library

```python
def generate_signal(self, symbol, data, spy_data, bar_index):
    # Access any available indicator
    if hasattr(self, 'indicator_library'):
        fibonacci = self.indicator_library.get('fibonacci', 
                                               data=data, 
                                               window=20)
        # Use fibonacci levels
```

See `./simulator/indicator_development_guide.md` for custom indicators.

---

## Troubleshooting

### Strategy Not Running

1. Check filename: Must be `strategy_*.py` in `./strategies/` directory
2. Check class name: Must be exactly `class Strategy(StrategyBase)`
3. Check method: Must have `generate_signal()` method with correct signature
4. Run simulator with `--tickers` flag to test small universe

### Signals Not Generating

1. Check that `generate_signal()` returns 'BUY', 'SELL', or 'HOLD'
2. Ensure you have sufficient data: Check `if len(data) < minimum_bars`
3. Add logging to debug: `print(f"Signal for {symbol}: {signal}")`
4. Check state management: Use per-symbol tracking for signal flags

### Look-Ahead Bias

Don't do this:
```python
# ❌ WRONG: Accessing future data
future_price = data['close'].iloc[bar_index + 1]

# ✅ RIGHT: Only use data up to current bar
current_price = data['close'].iloc[-1]
past_price = data['close'].iloc[-2]
```

---

## Performance Tips

1. **Minimize per-bar calculations** - Pre-compute when possible
2. **Use NumPy/Pandas efficiently** - Vectorized operations are faster than loops
3. **Check data length early** - Fail fast if not enough history
4. **Cache results** - Store intermediate calculations if reusing

---

## Next Steps

- Read `./simulator/indicator_development_guide.md` to create custom indicators
- Study the included strategies in `./strategies/` directory
- Check strategy performance in the analysis dashboard
- Iterate and improve based on metrics

Good luck! 🚀
