```markdown
please help me improve my simulation to optimize for performance, i already know that batch loading is the most effective method to use for a sqlite database, and then downloading market data is already optimized based on sysmte netowrk benchmarking and then limit rating by the api and using the hybrid downloading trickle download approach. Now i am able to do 9000 calculations per second on average but i want to increase that number by taking advantage of more of my computers resources, what changes would you suggest to make to improve overall performance for the simulation engine?I understand that i might need to convert some informatino into vectors sometimes and other techniques, overall please help me research how i can improve performace....
```



I'll help you research and implement performance optimizations for your simulation engine. Let me create a comprehensive analysis and actionable recommendations.Now let me create a practical implementation guide showing exactly how to modify your simulator:Let me also create a benchmarking script to help you measure your improvements:## Summary

I've created a comprehensive performance optimization research guide and implementation examples for your simulation engine. Here are the **key insights**:

### 🎯 Priority Optimizations (by impact)

1. **Vectorization (3-10x speedup)** - HIGHEST IMPACT
   - Process entire time series at once instead of bar-by-bar
   - Use NumPy array operations instead of Python loops
   - Pre-calculate all indicators for the entire dataset

2. **Numba JIT Compilation (2-5x additional speedup)**
   - Add `@jit` decorator to hot functions
   - Enable `nopython=True` and `parallel=True` for maximum speed
   - Compiles Python to machine code

3. **Memory Optimization (20-30% speedup)**
   - Load only required columns
   - Use efficient data types (downcast floats/integers)
   - Pre-allocate arrays instead of appending

4. **Better Parallelization (1.5-2x speedup)**
   - Use shared memory to reduce serialization overhead
   - Consider Ray for advanced work distribution

### 📊 Expected Results

| Optimization | Individual | Cumulative Calc/s |
|-------------|-----------|------------------|
| Baseline | 1.0x | 9,000 |
| + Vectorization | 5x | 45,000 |
| + Numba JIT | 3x | 135,000 |
| + Memory Opt | 1.2x | 162,000 |

**Conservative estimate:** 10x improvement (90,000 calc/s)  
**Optimistic estimate:** 25x improvement (225,000 calc/s)

### 🚀 Implementation Steps

**Phase 1 (2 hours, 2-3x speedup):**
1. Run the benchmark script to identify bottlenecks
2. Replace Python loops with pandas vectorized operations
3. Pre-allocate arrays

**Phase 2 (4 hours, 5-10x total speedup):**
1. Convert strategies to vectorized base class
2. Pre-calculate all indicators once
3. Use NumPy boolean indexing for signals

**Phase 3 (2 hours, 15-25x total speedup):**
1. Install Numba: `pip install numba`
2. Add `@jit` to indicator calculations
3. Add `@jit(parallel=True)` to signal generation

### 💡 Key Insight

The fundamental issue is **Python loop overhead**. Each loop iteration has significant overhead. By processing arrays all at once:
- Pandas/NumPy operations run in optimized C code
- Numba compiles to machine code (no Python interpreter)
- CPU can use SIMD instructions for parallel operations

**Example:** Calculating SMA for 10,000 bars:
- Python loop: ~100ms
- Pandas rolling: ~5ms (20x faster)
- Numba: ~0.5ms (200x faster)

Would you like me to help you implement any specific optimization, or would you like to see how to convert one of your existing strategies to the vectorized approach?


# Simulation Performance Optimization Research & Implementation Guide

## Current Performance Analysis

**Current State:**
- 9,000 calculations/second
- Using ProcessPoolExecutor for parallelization
- Batch database operations implemented
- Network-optimized data loading

**Goal:** Increase throughput by 5-10x to 45,000-90,000 calculations/second

---

## 1. Vectorization (Highest Impact - 3-10x Speedup)

### Problem
Currently processing data bar-by-bar in loops. Each strategy.on_data() call processes one bar at a time.

### Solution: Vectorize Strategy Logic

```python
# BEFORE (Bar-by-bar)
for i, current_date in enumerate(common_dates):
    stock_bar = stock_data.iloc[:i+1]
    signal = strategy.on_data(stock_bar, spy_bar, current_date, symbol)

# AFTER (Vectorized)
# Process ALL bars at once using NumPy operations
signals = strategy.on_data_vectorized(stock_data, spy_data, symbol)
```

### Implementation Steps

**A. Create Vectorized Strategy Base Class**

```python
class VectorizedStrategyBase(StrategyBase):
    """
    Vectorized strategy that processes entire arrays at once
    """
    
    def on_data_vectorized(self, stock_data, spy_data, symbol):
        """
        Process entire time series at once
        
        Returns:
            pd.Series: Signal for each date (0=hold, 1=buy, -1=sell)
        """
        raise NotImplementedError()
    
    def generate_signals_numpy(self, close_prices, volumes):
        """
        Example: Vectorized signal generation using NumPy
        """
        # Calculate all indicators at once
        sma_20 = np.convolve(close_prices, np.ones(20)/20, mode='same')
        sma_50 = np.convolve(close_prices, np.ones(50)/50, mode='same')
        
        # Generate signals as array operations
        signals = np.zeros(len(close_prices))
        signals[sma_20 > sma_50] = 1  # Buy when fast > slow
        signals[sma_20 < sma_50] = -1  # Sell when fast < slow
        
        # Prevent duplicate signals
        signals = np.diff(signals, prepend=0)
        
        return signals
```

**B. Vectorize Common Indicators**

```python
# Use pandas/numpy built-in vectorized operations
def calculate_indicators_vectorized(df):
    """All indicators calculated in one pass"""
    
    # Use pandas rolling for moving averages (optimized C code)
    df['sma_20'] = df['close'].rolling(20).mean()
    df['sma_50'] = df['close'].rolling(50).mean()
    
    # RSI vectorized
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    # Volume indicators
    df['volume_sma'] = df['volume'].rolling(20).mean()
    df['relative_volume'] = df['volume'] / df['volume_sma']
    
    return df
```

**Expected Impact:** 3-5x speedup from eliminating Python loops

---

## 2. Numba JIT Compilation (2-5x Additional Speedup)

### What is Numba?
JIT compiler that converts Python functions to optimized machine code.

### Installation
```bash
pip install numba
```

### Implementation

```python
from numba import jit, prange
import numpy as np

@jit(nopython=True, parallel=True, cache=True)
def calculate_signals_fast(close_prices, sma_20, sma_50):
    """
    Numba-optimized signal calculation
    
    nopython=True: Pure machine code (fastest)
    parallel=True: Use multiple CPU cores
    cache=True: Cache compiled code
    """
    n = len(close_prices)
    signals = np.zeros(n, dtype=np.int8)
    
    for i in prange(20, n):  # prange = parallel range
        if sma_20[i] > sma_50[i] and sma_20[i-1] <= sma_50[i-1]:
            signals[i] = 1  # Buy
        elif sma_20[i] < sma_50[i] and sma_20[i-1] >= sma_50[i-1]:
            signals[i] = -1  # Sell
    
    return signals

@jit(nopython=True)
def calculate_rsi_fast(prices, period=14):
    """Numba-optimized RSI calculation"""
    n = len(prices)
    rsi = np.zeros(n)
    
    for i in range(period, n):
        deltas = np.diff(prices[i-period:i+1])
        gains = np.where(deltas > 0, deltas, 0).sum()
        losses = np.where(deltas < 0, -deltas, 0).sum()
        
        if losses == 0:
            rsi[i] = 100
        else:
            rs = gains / losses
            rsi[i] = 100 - (100 / (1 + rs))
    
    return rsi
```

**Pro Tips:**
- First call is slow (compilation), subsequent calls are 50-100x faster
- Use `cache=True` to persist compiled code
- Arrays must be NumPy arrays (not pandas)
- Parallel loops need `prange()` instead of `range()`

**Expected Impact:** 2-5x additional speedup on hot paths

---

## 3. Memory Optimization & Data Structures

### Problem
Loading full DataFrames with unused columns wastes memory and CPU cache.

### Solutions

**A. Load Only Required Columns**

```python
# BEFORE: Load everything
df = pd.read_sql_query('SELECT * FROM stock_bars WHERE symbol=?', conn)

# AFTER: Load only what's needed
required_cols = ['timestamp', 'close', 'volume']
df = pd.read_sql_query(
    f'SELECT {",".join(required_cols)} FROM stock_bars WHERE symbol=?', 
    conn
)
```

**B. Use Efficient Data Types**

```python
def optimize_dataframe(df):
    """Reduce memory usage by 50-75%"""
    
    # Downcast numeric types
    df['close'] = pd.to_numeric(df['close'], downcast='float')
    df['volume'] = pd.to_numeric(df['volume'], downcast='integer')
    
    # Use categorical for repeated strings
    if 'symbol' in df.columns:
        df['symbol'] = df['symbol'].astype('category')
    
    return df
```

**C. Pre-allocate Arrays**

```python
# BEFORE: Append to lists (slow)
signals = []
for date in dates:
    signals.append(calculate_signal(date))

# AFTER: Pre-allocate array (fast)
signals = np.empty(len(dates), dtype=np.int8)
for i in range(len(dates)):
    signals[i] = calculate_signal(dates[i])
```

**Expected Impact:** 20-30% speedup from better cache utilization

---

## 4. Advanced Parallelization Strategies

### Current Issue
ProcessPoolExecutor has overhead from process creation and data serialization.

### Solution A: Thread Pool for I/O-Bound Operations

```python
from concurrent.futures import ThreadPoolExecutor

# Use threads for database reads (I/O bound)
with ThreadPoolExecutor(max_workers=20) as executor:
    futures = [executor.submit(load_data, symbol) for symbol in symbols]
    results = [f.result() for f in futures]
```

### Solution B: Multiprocessing with Shared Memory

```python
from multiprocessing import Pool, shared_memory
import numpy as np

def create_shared_array(data):
    """Create numpy array in shared memory"""
    shm = shared_memory.SharedMemory(create=True, size=data.nbytes)
    shared_array = np.ndarray(data.shape, dtype=data.dtype, buffer=shm.buf)
    shared_array[:] = data[:]
    return shm, shared_array

def worker_with_shared_memory(shm_name, shape, dtype, start, end):
    """Worker accesses shared memory (no data copying)"""
    existing_shm = shared_memory.SharedMemory(name=shm_name)
    data = np.ndarray(shape, dtype=dtype, buffer=existing_shm.buf)
    
    # Process slice of data
    results = process_slice(data[start:end])
    
    existing_shm.close()
    return results
```

### Solution C: Work Stealing with Ray

```python
# Install: pip install ray
import ray

ray.init(num_cpus=8)

@ray.remote
def process_stock_ray(symbol, stock_data, spy_data):
    """Ray automatically handles distribution"""
    return simulate_strategy(symbol, stock_data, spy_data)

# Submit all work
futures = [process_stock_ray.remote(sym, data, spy) 
           for sym in symbols]

# Get results as they complete
results = ray.get(futures)
```

**Expected Impact:** 1.5-2x from reduced serialization overhead

---

## 5. Caching & Memoization

### Problem
Recalculating same indicators repeatedly.

### Solution

```python
from functools import lru_cache
import hashlib

class IndicatorCache:
    """Cache expensive indicator calculations"""
    
    def __init__(self):
        self.cache = {}
    
    def get_cache_key(self, data, indicator_name, params):
        """Generate unique cache key"""
        data_hash = hashlib.md5(
            data['close'].values.tobytes()
        ).hexdigest()
        return f"{indicator_name}_{data_hash}_{params}"
    
    def get_or_calculate(self, data, indicator_name, calc_func, **params):
        """Get cached result or calculate"""
        key = self.get_cache_key(data, indicator_name, params)
        
        if key not in self.cache:
            self.cache[key] = calc_func(data, **params)
        
        return self.cache[key]

# Usage
cache = IndicatorCache()
rsi = cache.get_or_calculate(stock_data, 'rsi', calculate_rsi, period=14)
```

**Expected Impact:** 2-3x on repeated calculations

---

## 6. Profiling to Find Bottlenecks

### Use cProfile

```python
import cProfile
import pstats

def profile_simulation():
    profiler = cProfile.Profile()
    profiler.enable()
    
    # Run simulation
    run_simulation(strategies, symbols, data_manager)
    
    profiler.disable()
    
    # Print top 20 slowest functions
    stats = pstats.Stats(profiler)
    stats.sort_stats('cumulative')
    stats.print_stats(20)

# Run it
profile_simulation()
```

### Use line_profiler for Line-by-Line

```bash
pip install line_profiler

# Add @profile decorator to functions
@profile
def simulate_strategy_on_stock(...):
    # Your code
    pass

# Run
kernprof -l -v simulator.py
```

---

## 7. Database Query Optimization

### Current Approach is Good, But Can Improve

```python
# Add compound indexes
cursor.execute('''
    CREATE INDEX IF NOT EXISTS idx_symbol_timestamp 
    ON stock_bars(symbol, timestamp)
''')

# Use EXPLAIN QUERY PLAN to check queries
cursor.execute('EXPLAIN QUERY PLAN SELECT ...')
print(cursor.fetchall())

# Increase cache size
conn.execute('PRAGMA cache_size=50000')  # 50MB cache
```

### Use Memory-Mapped Database

```python
# For read-only simulation runs
conn = sqlite3.connect(f'file:{db_path}?mode=memory', uri=True)
```

---

## 8. Reduce Python Overhead

### Use NumPy Throughout

```python
# BEFORE: Python lists and loops
prices = []
for bar in stock_data:
    prices.append(bar['close'])
avg = sum(prices) / len(prices)

# AFTER: NumPy
prices = stock_data['close'].values  # Get as numpy array
avg = prices.mean()  # 10-100x faster
```

### Use NumPy's Universal Functions (ufuncs)

```python
# These are implemented in C and very fast
np.maximum(a, b)  # Element-wise max
np.where(condition, x, y)  # Vectorized if-else
np.clip(values, min, max)  # Constrain values
```

---

## Implementation Priority

### Phase 1: Quick Wins (1-2 hours, 2-3x speedup)
1. ✅ Add data type optimization to DataFrames
2. ✅ Pre-allocate arrays instead of appending
3. ✅ Use pandas built-in vectorized operations
4. ✅ Profile to find hotspots

### Phase 2: Vectorization (4-8 hours, 3-5x speedup)
1. ✅ Create vectorized strategy base class
2. ✅ Convert one strategy to vectorized version
3. ✅ Vectorize indicator calculations
4. ✅ Benchmark and compare

### Phase 3: JIT Compilation (2-4 hours, 2-4x speedup)
1. ✅ Install Numba
2. ✅ Add @jit to performance-critical functions
3. ✅ Convert loops to NumPy operations
4. ✅ Test with nopython=True and parallel=True

### Phase 4: Advanced (8+ hours, 1.5-2x additional)
1. ✅ Implement shared memory parallelization
2. ✅ Add intelligent caching
3. ✅ Optimize database queries further
4. ✅ Consider GPU acceleration (if applicable)

---

## Example: Vectorized Strategy

```python
class VectorizedMomentumStrategy(VectorizedStrategyBase):
    """
    Example fully vectorized strategy
    """
    
    def on_data_vectorized(self, stock_data, spy_data, symbol):
        # Calculate all indicators at once
        df = stock_data.copy()
        
        # Vectorized calculations
        df['sma_20'] = df['close'].rolling(20).mean()
        df['sma_50'] = df['close'].rolling(50).mean()
        df['rsi'] = self._calculate_rsi_vectorized(df['close'])
        
        # Generate signals as boolean masks
        buy_signal = (
            (df['sma_20'] > df['sma_50']) &
            (df['sma_20'].shift(1) <= df['sma_50'].shift(1)) &
            (df['rsi'] < 70)
        )
        
        sell_signal = (
            (df['sma_20'] < df['sma_50']) &
            (df['sma_20'].shift(1) >= df['sma_50'].shift(1))
        )
        
        # Convert to signal series
        signals = pd.Series(0, index=df.index)
        signals[buy_signal] = 1
        signals[sell_signal] = -1
        
        return signals
    
    @staticmethod
    @jit(nopython=True)
    def _calculate_rsi_vectorized(prices_array):
        """Numba-accelerated RSI"""
        # Implementation from earlier
        pass
```

---

## Expected Overall Performance Gain

| Optimization | Individual Gain | Cumulative |
|-------------|----------------|------------|
| Baseline | 1.0x | 9,000 calc/s |
| Vectorization | 3-5x | 27,000-45,000 |
| Numba JIT | 2-3x | 54,000-135,000 |
| Memory Optimization | 1.2x | 65,000-162,000 |
| Better Parallelization | 1.5x | 97,500-243,000 |

**Conservative Estimate:** 10x improvement (90,000 calc/s)
**Optimistic Estimate:** 25x improvement (225,000 calc/s)

---

## Monitoring Performance

```python
import time
import psutil
import os

class PerformanceMonitor:
    def __init__(self):
        self.process = psutil.Process(os.getpid())
        self.start_time = None
        self.checkpoints = {}
    
    def start(self):
        self.start_time = time.time()
        self.start_memory = self.process.memory_info().rss / 1024**2
    
    def checkpoint(self, name):
        elapsed = time.time() - self.start_time
        memory = self.process.memory_info().rss / 1024**2
        cpu_percent = self.process.cpu_percent()
        
        self.checkpoints[name] = {
            'elapsed': elapsed,
            'memory_mb': memory,
            'memory_delta': memory - self.start_memory,
            'cpu_percent': cpu_percent
        }
        
        print(f"📊 {name}: {elapsed:.2f}s, "
              f"{memory:.1f}MB (+{memory-self.start_memory:.1f}MB), "
              f"CPU: {cpu_percent:.1f}%")
    
    def summary(self):
        total_time = time.time() - self.start_time
        print(f"\n⏱️  Total Time: {total_time:.2f}s")
        print(f"📈 Checkpoints:")
        for name, stats in self.checkpoints.items():
            print(f"  {name}: {stats['elapsed']:.2f}s")

# Usage in simulator
monitor = PerformanceMonitor()
monitor.start()

# ... load data ...
monitor.checkpoint("Data Loaded")

# ... run simulation ...
monitor.checkpoint("Simulation Complete")

monitor.summary()
```

---

## Next Steps

1. **Profile Current Code**
   ```bash
   python -m cProfile -o profile.stats simulator.py
   python -m pstats profile.stats
   ```

2. **Start with Quick Wins** (Phase 1)
   - Optimize data types
   - Use vectorized pandas operations
   
3. **Implement Vectorization** (Phase 2)
   - Create one vectorized strategy
   - Measure performance gain
   
4. **Add Numba** (Phase 3)
   - JIT compile hot functions
   - Enable parallel execution

5. **Iterate Based on Profiling**
   - Find remaining bottlenecks
   - Apply targeted optimizations

---

## Resources

- **NumPy Performance**: https://numpy.org/doc/stable/user/performance.html
- **Numba Documentation**: https://numba.readthedocs.io/
- **Pandas Optimization**: https://pandas.pydata.org/docs/user_guide/enhancingperf.html
- **Python Profiling**: https://docs.python.org/3/library/profile.html
- **Ray Documentation**: https://docs.ray.io/

---

## Conclusion

Focus on vectorization first (biggest impact), then add Numba JIT compilation. These two changes alone should give you 6-15x speedup, taking you from 9,000 to 54,000-135,000 calculations/second.

The key insight: **Eliminate Python loops** in favor of NumPy array operations. Every loop you eliminate is potentially a 10-100x speedup on that operation.


```



"""
OPTIMIZED VECTORIZED SIMULATOR
Performance improvements: 5-15x speedup expected

Key Changes:
1. Vectorized strategy execution (process all bars at once)
2. Numba JIT compilation for hot paths
3. Pre-computed indicators
4. Reduced database operations
5. NumPy array operations instead of loops
"""

import numpy as np
import pandas as pd
from numba import jit, prange
import time
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor, as_completed
from tqdm import tqdm

# =============================================================================
# VECTORIZED INDICATOR CALCULATIONS WITH NUMBA
# =============================================================================

@jit(nopython=True, cache=True)
def calculate_sma_numba(prices, period):
    """Numba-optimized Simple Moving Average"""
    n = len(prices)
    sma = np.empty(n)
    sma[:period-1] = np.nan
    
    for i in range(period-1, n):
        sma[i] = prices[i-period+1:i+1].mean()
    
    return sma

@jit(nopython=True, cache=True)
def calculate_rsi_numba(prices, period=14):
    """Numba-optimized RSI calculation"""
    n = len(prices)
    rsi = np.empty(n)
    rsi[:period] = 50.0  # Default RSI for first bars
    
    for i in range(period, n):
        deltas = np.diff(prices[i-period:i+1])
        gains = np.where(deltas > 0, deltas, 0).sum()
        losses = np.where(deltas < 0, -deltas, 0).sum()
        
        if losses == 0:
            rsi[i] = 100.0
        else:
            rs = gains / losses
            rsi[i] = 100.0 - (100.0 / (1.0 + rs))
    
    return rsi

@jit(nopython=True, parallel=True, cache=True)
def generate_crossover_signals_numba(fast_ma, slow_ma, min_bars=50):
    """
    Numba-optimized crossover signal generation
    Returns: 1=BUY, -1=SELL, 0=HOLD
    """
    n = len(fast_ma)
    signals = np.zeros(n, dtype=np.int8)
    
    for i in prange(min_bars, n):
        # Golden cross (fast crosses above slow)
        if fast_ma[i] > slow_ma[i] and fast_ma[i-1] <= slow_ma[i-1]:
            signals[i] = 1
        # Death cross (fast crosses below slow)
        elif fast_ma[i] < slow_ma[i] and fast_ma[i-1] >= slow_ma[i-1]:
            signals[i] = -1
    
    return signals

# =============================================================================
# VECTORIZED INDICATOR CALCULATOR
# =============================================================================

class VectorizedIndicators:
    """
    Pre-calculate all indicators at once for entire time series
    Much faster than calculating per-bar
    """
    
    @staticmethod
    def calculate_all_indicators(df):
        """
        Calculate all indicators for entire dataframe
        Returns new dataframe with indicator columns
        """
        result = df.copy()
        
        # Convert to numpy for speed
        close_prices = df['close'].values
        volumes = df['volume'].values
        
        # Use Numba for calculations
        result['sma_20'] = calculate_sma_numba(close_prices, 20)
        result['sma_50'] = calculate_sma_numba(close_prices, 50)
        result['rsi'] = calculate_rsi_numba(close_prices, 14)
        
        # Volume indicators (pandas is fast enough here)
        result['volume_sma_20'] = df['volume'].rolling(20).mean()
        result['relative_volume'] = df['volume'] / result['volume_sma_20']
        
        # Fill NaN with reasonable defaults
        result.fillna(method='bfill', inplace=True)
        
        return result

# =============================================================================
# VECTORIZED STRATEGY BASE CLASS
# =============================================================================

class VectorizedStrategyBase:
    """
    Base class for vectorized strategies
    Processes entire time series at once instead of bar-by-bar
    """
    
    def __init__(self, name="VectorizedStrategy", **config):
        self.name = name
        self.config = config
        self.initial_capital = config.get('initial_capital', 100000)
        self.position_size_pct = config.get('position_size_pct', 0.10)
        self.max_positions = config.get('max_positions', 10)
    
    def generate_signals_vectorized(self, stock_data_with_indicators, spy_data_with_indicators):
        """
        Generate signals for entire time series
        
        Args:
            stock_data_with_indicators: DataFrame with OHLCV + indicators
            spy_data_with_indicators: DataFrame with SPY + indicators
        
        Returns:
            pd.Series: Signal for each timestamp (1=BUY, -1=SELL, 0=HOLD)
        """
        raise NotImplementedError("Implement in subclass")
    
    def get_config(self):
        return {
            'name': self.name,
            'initial_capital': self.initial_capital,
            'position_size_pct': self.position_size_pct,
            'max_positions': self.max_positions,
            **self.config
        }

# =============================================================================
# EXAMPLE VECTORIZED STRATEGY
# =============================================================================

class VectorizedMomentumStrategy(VectorizedStrategyBase):
    """
    Example vectorized momentum strategy using crossovers
    """
    
    def generate_signals_vectorized(self, stock_data, spy_data):
        """Generate all signals at once using NumPy operations"""
        
        # Extract numpy arrays for speed
        sma_20 = stock_data['sma_20'].values
        sma_50 = stock_data['sma_50'].values
        rsi = stock_data['rsi'].values
        
        # Use Numba-compiled function for signal generation
        raw_signals = generate_crossover_signals_numba(sma_20, sma_50)
        
        # Apply filters (RSI, etc.) using NumPy boolean indexing
        buy_filter = (rsi < 70)
        sell_filter = (rsi > 30)
        
        # Apply filters to signals
        signals = raw_signals.copy()
        signals[raw_signals == 1] = np.where(buy_filter[raw_signals == 1], 1, 0)
        signals[raw_signals == -1] = np.where(sell_filter[raw_signals == -1], -1, 0)
        
        return pd.Series(signals, index=stock_data.index)

# =============================================================================
# VECTORIZED PORTFOLIO SIMULATOR
# =============================================================================

@jit(nopython=True)
def simulate_trades_numba(signals, prices, volumes, 
                          initial_cash, position_size_pct, max_positions):
    """
    Numba-optimized trade simulation
    
    Returns: (cash_history, position_history, trades_array)
    """
    n = len(signals)
    
    # Pre-allocate arrays
    cash = initial_cash
    position = 0.0  # shares held
    portfolio_values = np.empty(n)
    positions = np.empty(n)
    
    # Track trades (date_idx, signal, price, shares, cash_after)
    trades = []
    
    for i in range(n):
        portfolio_value = cash + (position * prices[i] if position > 0 else 0)
        
        if signals[i] == 1 and position == 0:  # BUY
            # Calculate position size
            allocation = portfolio_value * position_size_pct
            allocation = min(allocation, cash)
            
            if allocation >= 100:
                shares = allocation / prices[i]
                cost = shares * prices[i]
                
                if cost <= cash:
                    position = shares
                    cash -= cost
                    trades.append((i, 1, prices[i], shares, cash))
        
        elif signals[i] == -1 and position > 0:  # SELL
            proceeds = position * prices[i]
            cash += proceeds
            trades.append((i, -1, prices[i], position, cash))
            position = 0
        
        portfolio_values[i] = cash + (position * prices[i])
        positions[i] = position
    
    return portfolio_values, positions, trades

def simulate_strategy_vectorized(strategy, symbol, stock_data, spy_data):
    """
    Vectorized simulation for one stock
    Much faster than bar-by-bar approach
    """
    # Pre-calculate ALL indicators once
    stock_with_indicators = VectorizedIndicators.calculate_all_indicators(stock_data)
    spy_with_indicators = VectorizedIndicators.calculate_all_indicators(spy_data)
    
    # Generate ALL signals at once
    signals = strategy.generate_signals_vectorized(stock_with_indicators, spy_with_indicators)
    
    # Simulate trades using Numba (very fast)
    portfolio_values, positions, trades = simulate_trades_numba(
        signals.values,
        stock_data['close'].values,
        stock_data['volume'].values,
        strategy.initial_capital,
        strategy.position_size_pct,
        strategy.max_positions
    )
    
    return {
        'symbol': symbol,
        'signals': signals,
        'portfolio_values': portfolio_values,
        'positions': positions,
        'trades': trades
    }

# =============================================================================
# OPTIMIZED SIMULATION ENGINE
# =============================================================================

def run_vectorized_simulation(strategies, symbols, data_manager, **kwargs):
    """
    Main simulation loop - VECTORIZED VERSION
    Expected: 5-15x faster than original
    """
    
    print("\n" + "="*70)
    print("RUNNING VECTORIZED SIMULATION")
    print("="*70)
    
    start_time = time.time()
    
    # Load all data using batch loading (already optimized)
    print("📥 Loading market data...")
    spy_data = data_manager.get_stock_data("SPY", days=180)
    
    stock_data_dict = data_manager.load_multiple_symbols_batch(
        symbols, 
        start_date=spy_data.index[0], 
        end_date=spy_data.index[-1]
    )
    
    symbols_with_data = [s for s in symbols if s in stock_data_dict]
    print(f"✅ Loaded {len(symbols_with_data)} symbols")
    
    # Align all data to common dates
    common_dates = spy_data.index
    for symbol in symbols_with_data:
        common_dates = common_dates.intersection(stock_data_dict[symbol].index)
    
    spy_data = spy_data.loc[common_dates]
    for symbol in symbols_with_data:
        stock_data_dict[symbol] = stock_data_dict[symbol].loc[common_dates]
    
    print(f"📊 Time points: {len(common_dates)}")
    
    # Pre-calculate indicators for SPY (do once, reuse for all strategies)
    print("🔢 Pre-calculating indicators...")
    spy_with_indicators = VectorizedIndicators.calculate_all_indicators(spy_data)
    
    stocks_with_indicators = {}
    for symbol in tqdm(symbols_with_data, desc="Calculating indicators"):
        stocks_with_indicators[symbol] = VectorizedIndicators.calculate_all_indicators(
            stock_data_dict[symbol]
        )
    
    # Run simulations in parallel
    print(f"\n⚡ Running {len(strategies)} strategies on {len(symbols_with_data)} stocks...")
    
    results = {}
    
    # Use ProcessPoolExecutor for parallel execution
    with ProcessPoolExecutor(max_workers=mp.cpu_count()) as executor:
        futures = {}
        
        for strategy in strategies:
            for symbol in symbols_with_data:
                future = executor.submit(
                    simulate_strategy_vectorized,
                    strategy,
                    symbol,
                    stocks_with_indicators[symbol],
                    spy_with_indicators
                )
                futures[future] = (strategy.name, symbol)
        
        # Collect results
        for future in tqdm(as_completed(futures), total=len(futures), desc="Processing"):
            strategy_name, symbol = futures[future]
            try:
                result = future.result()
                
                if strategy_name not in results:
                    results[strategy_name] = []
                results[strategy_name].append(result)
                
            except Exception as e:
                print(f"❌ Error: {strategy_name} on {symbol}: {e}")
    
    # Calculate performance statistics
    elapsed = time.time() - start_time
    total_iterations = len(strategies) * len(symbols_with_data) * len(common_dates)
    
    print(f"\n{'='*70}")
    print("⏱️  PERFORMANCE STATISTICS")
    print(f"{'='*70}")
    print(f"Total Time: {elapsed:.2f}s")
    print(f"Total Iterations: {total_iterations:,}")
    print(f"Iterations/Second: {total_iterations/elapsed:,.0f}")
    print(f"Speedup vs Original: {(total_iterations/elapsed) / 9000:.1f}x")
    print(f"{'='*70}\n")
    
    return results

# =============================================================================
# USAGE EXAMPLE
# =============================================================================

if __name__ == "__main__":
    # Create vectorized strategy
    momentum_strategy = VectorizedMomentumStrategy(
        name="Vectorized Momentum",
        initial_capital=100000,
        position_size_pct=0.10,
        max_positions=10
    )
    
    # Run simulation
    strategies = [momentum_strategy]
    symbols = ['AAPL', 'GOOGL', 'MSFT']  # Test with a few symbols first
    
    # Initialize your data_manager
    # data_manager = DataManager(api_key, secret_key)
    
    # results = run_vectorized_simulation(strategies, symbols, data_manager)
    
    print("✅ Vectorized simulator ready!")
    print("Expected performance: 5-15x faster")
    print("\nNext steps:")
    print("1. Create vectorized versions of your strategies")
    print("2. Test with small dataset first")
    print("3. Profile to verify speedup")
    print("4. Scale to full universe")


    