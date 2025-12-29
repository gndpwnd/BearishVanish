# Performance Optimization Implementation Guide

## 🎯 Philosophy: Optimize Without Breaking Modularity

**Key Insight**: You don't need to abandon bar-by-bar simulation. Instead, we'll:
1. **Keep** bar-by-bar iteration (prevents look-ahead bias)
2. **Optimize** the hot paths within each bar
3. **Parallelize** across strategies and symbols (not within simulation)
4. **Pre-compute** indicators once per symbol
5. **Use Numba** for computational bottlenecks

---

## 📋 Implementation Roadmap

### Phase 1: Foundation (2-3 hours)
- Add Numba JIT to indicator calculations
- Implement indicator pre-computation
- Profile existing code to find bottlenecks

### Phase 2: Core Optimization (4-6 hours)
- Optimize strategy execution hot paths
- Implement parallel processing at strategy/symbol level
- Add memory optimization for large datasets

### Phase 3: Polish (2-3 hours)
- Auto-configuration based on hardware
- Enhanced telemetry with performance metrics
- Benchmarking tools

**Expected Result**: 5-15x speedup while maintaining all features

---

## 🔧 Step-by-Step Implementation

### STEP 1: Install Required Packages

```bash
pip install numba psutil line_profiler
```

### STEP 2: Update `indicator_base.py` - Add Numba Optimization

**Goal**: Make indicator calculations 10-100x faster without changing the API

Create this new structure in `indicator_base.py`:

```python
"""
Optimized Indicator Base with Numba JIT
All indicators use compiled functions for speed
"""

import numpy as np
import pandas as pd
from numba import jit, prange
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

@dataclass
class IndicatorResult:
    """Result from indicator calculation"""
    name: str
    value: Any  # Single value or array
    params: Dict[str, Any]
    calculation_time_ms: float = 0.0

# ============================================================
# NUMBA-OPTIMIZED INDICATOR FUNCTIONS
# These run 10-100x faster than pure Python
# ============================================================

@jit(nopython=True, cache=True)
def sma_numba(prices: np.ndarray, period: int) -> np.ndarray:
    """Simple Moving Average - Numba optimized"""
    n = len(prices)
    result = np.full(n, np.nan, dtype=np.float64)
    
    for i in range(period - 1, n):
        result[i] = np.mean(prices[i - period + 1:i + 1])
    
    return result

@jit(nopython=True, cache=True)
def ema_numba(prices: np.ndarray, period: int) -> np.ndarray:
    """Exponential Moving Average - Numba optimized"""
    n = len(prices)
    result = np.full(n, np.nan, dtype=np.float64)
    
    if n < period:
        return result
    
    # Initial SMA
    result[period - 1] = np.mean(prices[:period])
    
    # EMA calculation
    multiplier = 2.0 / (period + 1.0)
    for i in range(period, n):
        result[i] = (prices[i] - result[i-1]) * multiplier + result[i-1]
    
    return result

@jit(nopython=True, cache=True)
def rsi_numba(prices: np.ndarray, period: int = 14) -> np.ndarray:
    """RSI - Numba optimized"""
    n = len(prices)
    result = np.full(n, np.nan, dtype=np.float64)
    
    if n < period + 1:
        return result
    
    # Calculate price changes
    deltas = np.diff(prices)
    
    # Separate gains and losses
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)
    
    # Calculate average gain/loss
    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])
    
    if avg_loss == 0:
        result[period] = 100.0
    else:
        rs = avg_gain / avg_loss
        result[period] = 100.0 - (100.0 / (1.0 + rs))
    
    # Smooth subsequent values
    for i in range(period + 1, n):
        gain = gains[i - 1]
        loss = losses[i - 1]
        
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period
        
        if avg_loss == 0:
            result[i] = 100.0
        else:
            rs = avg_gain / avg_loss
            result[i] = 100.0 - (100.0 / (1.0 + rs))
    
    return result

@jit(nopython=True, cache=True)
def bollinger_bands_numba(prices: np.ndarray, period: int = 20, std_dev: float = 2.0):
    """Bollinger Bands - Numba optimized"""
    n = len(prices)
    middle = np.full(n, np.nan, dtype=np.float64)
    upper = np.full(n, np.nan, dtype=np.float64)
    lower = np.full(n, np.nan, dtype=np.float64)
    
    for i in range(period - 1, n):
        window = prices[i - period + 1:i + 1]
        middle[i] = np.mean(window)
        std = np.std(window)
        upper[i] = middle[i] + (std * std_dev)
        lower[i] = middle[i] - (std * std_dev)
    
    return upper, middle, lower

@jit(nopython=True, cache=True)
def relative_volume_numba(volumes: np.ndarray, period: int = 20) -> np.ndarray:
    """Relative Volume - Numba optimized"""
    n = len(volumes)
    result = np.full(n, np.nan, dtype=np.float64)
    
    for i in range(period - 1, n):
        avg_vol = np.mean(volumes[i - period + 1:i + 1])
        if avg_vol > 0:
            result[i] = volumes[i] / avg_vol
        else:
            result[i] = 1.0
    
    return result

# ============================================================
# INDICATOR BASE CLASS - Maintains your modular architecture
# ============================================================

class IndicatorBase:
    """
    Base class for all indicators
    Provides both Numba-optimized and standard calculation paths
    """
    
    def __init__(self, name: str = "Indicator", use_numba: bool = True):
        self.name = name
        self.use_numba = use_numba
        self.dependencies: List[str] = []
        self.cache: Dict[str, Any] = {}
    
    def calculate(self, data: pd.DataFrame, **params) -> IndicatorResult:
        """
        Calculate indicator - override in subclasses
        """
        raise NotImplementedError(f"{self.name} must implement calculate()")
    
    def calculate_batch(self, data: pd.DataFrame, indicators: List[str]) -> Dict[str, IndicatorResult]:
        """
        Calculate multiple indicators at once (more efficient)
        """
        results = {}
        for indicator_name in indicators:
            # Call the appropriate calculation function
            results[indicator_name] = self.calculate(data, indicator=indicator_name)
        return results

# ============================================================
# BUILT-IN INDICATOR FUNCTIONS (with caching)
# ============================================================

def calculate_sma(data: pd.DataFrame, period: int = 20, use_numba: bool = True) -> np.ndarray:
    """Calculate SMA with optional Numba acceleration"""
    import time
    start = time.time()
    
    prices = data['close'].values.astype(np.float64)
    
    if use_numba:
        result = sma_numba(prices, period)
    else:
        result = data['close'].rolling(period).mean().values
    
    calc_time = (time.time() - start) * 1000
    return result

def calculate_ema(data: pd.DataFrame, period: int = 20, use_numba: bool = True) -> np.ndarray:
    """Calculate EMA with optional Numba acceleration"""
    prices = data['close'].values.astype(np.float64)
    
    if use_numba:
        result = ema_numba(prices, period)
    else:
        result = data['close'].ewm(span=period, adjust=False).mean().values
    
    return result

def calculate_rsi(data: pd.DataFrame, period: int = 14, use_numba: bool = True) -> np.ndarray:
    """Calculate RSI with optional Numba acceleration"""
    prices = data['close'].values.astype(np.float64)
    
    if use_numba:
        result = rsi_numba(prices, period)
    else:
        deltas = data['close'].diff()
        gain = deltas.where(deltas > 0, 0).rolling(period).mean()
        loss = (-deltas.where(deltas < 0, 0)).rolling(period).mean()
        rs = gain / loss
        result = (100 - (100 / (1 + rs))).values
    
    return result

def calculate_bollinger_bands(data: pd.DataFrame, period: int = 20, std_dev: float = 2.0, use_numba: bool = True):
    """Calculate Bollinger Bands with optional Numba acceleration"""
    prices = data['close'].values.astype(np.float64)
    
    if use_numba:
        upper, middle, lower = bollinger_bands_numba(prices, period, std_dev)
    else:
        middle = data['close'].rolling(period).mean()
        std = data['close'].rolling(period).std()
        upper = (middle + (std * std_dev)).values
        middle = middle.values
        lower = (middle - (std * std_dev)).values
    
    return upper, middle, lower

def calculate_relative_volume(data: pd.DataFrame, period: int = 20, use_numba: bool = True) -> np.ndarray:
    """Calculate relative volume with optional Numba acceleration"""
    volumes = data['volume'].values.astype(np.float64)
    
    if use_numba:
        result = relative_volume_numba(volumes, period)
    else:
        avg_volume = data['volume'].rolling(period).mean()
        result = (data['volume'] / avg_volume).values
    
    return result

# ============================================================
# BUILT-IN FUNCTIONS REGISTRY
# ============================================================

BUILTIN_FUNCTIONS = {
    'sma': calculate_sma,
    'ema': calculate_ema,
    'rsi': calculate_rsi,
    'bollinger_bands': calculate_bollinger_bands,
    'relative_volume': calculate_relative_volume,
}

BUILTIN_CLASSES = {}  # For class-based indicators
```

---

### STEP 3: Update `simulator.py` - Add Pre-computation and Parallel Processing

**Goal**: Pre-compute indicators once, parallelize strategy execution

Add this at the top of your `simulator.py`:

```python
"""
Optimized Simulator with Pre-computation and Parallel Processing
Maintains bar-by-bar simulation (no look-ahead bias) while optimizing hot paths
"""

import numpy as np
import pandas as pd
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import Dict, List, Tuple
import time
from tqdm import tqdm

# ============================================================
# INDICATOR PRE-COMPUTATION
# ============================================================

def precompute_indicators_for_symbol(symbol: str, 
                                     data: pd.DataFrame,
                                     indicator_library,
                                     required_indicators: List[str]) -> pd.DataFrame:
    """
    Pre-compute all indicators for a symbol ONCE
    This is the key optimization - calculate before simulation loop
    """
    print(f"  Pre-computing {len(required_indicators)} indicators for {symbol}...")
    start_time = time.time()
    
    # Calculate all indicators in batch
    for indicator_name in required_indicators:
        if indicator_name in indicator_library._functions:
            # Call the function
            result = indicator_library._functions[indicator_name](data)
            
            # Add to dataframe
            if isinstance(result, tuple):
                # Multiple outputs (like Bollinger Bands)
                data[f'{indicator_name}_upper'] = result[0]
                data[f'{indicator_name}_middle'] = result[1]
                data[f'{indicator_name}_lower'] = result[2]
            else:
                data[indicator_name] = result
    
    elapsed = (time.time() - start_time) * 1000
    print(f"  âœ… {symbol} indicators computed in {elapsed:.1f}ms")
    
    return data

# ============================================================
# OPTIMIZED SIMULATION FUNCTION
# ============================================================

def run_single_strategy_on_symbol(strategy, 
                                  symbol: str,
                                  stock_data: pd.DataFrame,
                                  spy_data: pd.DataFrame,
                                  args) -> Dict:
    """
    Run a single strategy on a single symbol
    This function is parallelized across all strategy/symbol combinations
    """
    try:
        # Create strategy tracker
        tracker = StrategyTracker(
            strategy.name,
            initial_cash=strategy.initial_capital,
            position_size_pct=strategy.position_size_pct,
            max_positions=strategy.max_positions
        )
        
        # Bar-by-bar iteration (maintains no look-ahead bias)
        for i in range(len(stock_data)):
            current_date = stock_data.index[i]
            current_price = stock_data['close'].iloc[i]
            
            # Get historical data up to current bar (no future data!)
            historical_data = stock_data.iloc[:i+1]
            historical_spy = spy_data.iloc[:i+1] if i < len(spy_data) else spy_data
            
            # Strategy generates signal (with pre-computed indicators)
            signal = strategy.generate_signal(
                symbol=symbol,
                data=historical_data,
                spy_data=historical_spy,
                bar_index=i
            )
            
            # Execute trade
            if signal in ['BUY', 'SELL']:
                volume = stock_data['volume'].iloc[i] if 'volume' in stock_data.columns else 0
                tracker.execute_trade(
                    symbol, signal, current_price, current_date,
                    volume=volume
                )
            
            # Update portfolio value
            current_prices = {symbol: current_price}
            tracker.update_portfolio_value(current_date, current_prices)
        
        # Force liquidation if configured
        if args.force_liquidate:
            final_prices = {symbol: stock_data['close'].iloc[-1]}
            tracker.force_liquidate_all(stock_data.index[-1], final_prices)
        
        return {
            'strategy': strategy.name,
            'symbol': symbol,
            'tracker': tracker,
            'success': True
        }
        
    except Exception as e:
        print(f"âŒ Error: {strategy.name} on {symbol}: {e}")
        return {
            'strategy': strategy.name,
            'symbol': symbol,
            'error': str(e),
            'success': False
        }
```

Then update your main `run_simulation` function:

```python
def run_simulation(strategies, symbols, data_manager, universe_manager, args):
    """
    Main simulation with pre-computation and parallel processing
    """
    from indicator_loader import get_indicator_library
    from simulation_telemetry import SimulationTelemetry, BatchBuffer
    import multiprocessing as mp
    
    # Initialize
    indicator_library = get_indicator_library()
    telemetry = SimulationTelemetry()
    
    print(f"\n{'='*70}")
    print("OPTIMIZED SIMULATION ENGINE")
    print(f"{'='*70}")
    print(f"Strategies: {len(strategies)}")
    print(f"Symbols: {len(symbols)}")
    print(f"Numba JIT: Enabled")
    print(f"Parallel Workers: {mp.cpu_count() - 1}")
    print(f"{'='*70}\n")
    
    # STEP 1: Load all data in batch (already optimized)
    print("📥 Loading market data...")
    start_date = pd.Timestamp.now() - pd.Timedelta(days=180)
    end_date = pd.Timestamp.now()
    
    data_dict = data_manager.load_multiple_symbols_batch(
        symbols, start_date, end_date
    )
    
    spy_data = data_manager.get_stock_data('SPY', days=180)
    print(f"âœ… Loaded {len(data_dict)} symbols\n")
    
    # STEP 2: Pre-compute all indicators for all symbols
    print("🔧 Pre-computing indicators...")
    
    # Collect all required indicators from all strategies
    all_required_indicators = set()
    for strategy in strategies:
        if hasattr(strategy, 'required_indicators'):
            all_required_indicators.update(strategy.required_indicators)
    
    print(f"  Total unique indicators: {len(all_required_indicators)}")
    
    # Pre-compute for each symbol
    for symbol in tqdm(data_dict.keys(), desc="Pre-computing"):
        data_dict[symbol] = precompute_indicators_for_symbol(
            symbol,
            data_dict[symbol],
            indicator_library,
            list(all_required_indicators)
        )
    
    print("âœ… All indicators pre-computed\n")
    
    # STEP 3: Run simulations in parallel
    print("⚡ Running simulations...")
    
    # Create all strategy/symbol combinations
    tasks = []
    for strategy in strategies:
        for symbol in symbols:
            if symbol in data_dict:
                tasks.append((strategy, symbol))
    
    print(f"  Total simulations: {len(tasks)}")
    
    # Process in parallel
    results = {}
    with ProcessPoolExecutor(max_workers=mp.cpu_count() - 1) as executor:
        # Submit all tasks
        futures = {
            executor.submit(
                run_single_strategy_on_symbol,
                strategy, symbol, data_dict[symbol], spy_data, args
            ): (strategy.name, symbol)
            for strategy, symbol in tasks
        }
        
        # Collect results with progress bar
        with tqdm(total=len(futures), desc="Simulating") as pbar:
            for future in as_completed(futures):
                strategy_name, symbol = futures[future]
                result = future.result()
                
                if result['success']:
                    if strategy_name not in results:
                        results[strategy_name] = {}
                    results[strategy_name][symbol] = result['tracker']
                
                pbar.update(1)
    
    print("âœ… Simulations complete\n")
    
    # STEP 4: Record telemetry (existing code continues here...)
    # ... rest of your telemetry code ...
    
    return telemetry.db_path
```

---

### STEP 4: Update Strategy Base Class

Add this property to `strategy_base.py`:

```python
class StrategyBase:
    def __init__(self, color='blue', initial_capital=100000, 
                 position_size_pct=0.10, max_positions=10):
        self.name = "Strategy"
        self.color = color
        self.initial_capital = initial_capital
        self.position_size_pct = position_size_pct
        self.max_positions = max_positions
        
        # NEW: Declare required indicators
        self.required_indicators = []
    
    def generate_signal(self, symbol, data, spy_data, bar_index):
        """
        Generate trading signal for current bar
        
        Args:
            symbol: Stock symbol
            data: Historical data up to current bar (includes pre-computed indicators)
            spy_data: SPY historical data
            bar_index: Current bar index
            
        Returns:
            'BUY', 'SELL', or 'HOLD'
        """
        raise NotImplementedError("Strategy must implement generate_signal()")
```

---

### STEP 5: Update an Example Strategy to Use Pre-computed Indicators

Update your strategies to use pre-computed indicators:

```python
# strategies/strategy_momentum.py

from strategy_base import StrategyBase

class Strategy(StrategyBase):
    def __init__(self, fast_ma=20, slow_ma=50, rsi_period=14, **kwargs):
        super().__init__(**kwargs)
        self.name = "Momentum Strategy"
        
        # Strategy parameters
        self.fast_ma = fast_ma
        self.slow_ma = slow_ma
        self.rsi_period = rsi_period
        
        # NEW: Declare what indicators this strategy needs
        self.required_indicators = [
            f'sma_{fast_ma}',
            f'sma_{slow_ma}',
            f'rsi_{rsi_period}'
        ]
    
    def generate_signal(self, symbol, data, spy_data, bar_index):
        """
        Generate signal using pre-computed indicators
        """
        # Need minimum bars
        if len(data) < self.slow_ma + 1:
            return 'HOLD'
        
        # Access pre-computed indicators (NO calculation needed!)
        current_idx = -1  # Current bar
        prev_idx = -2     # Previous bar
        
        # Get indicator values (already computed!)
        fast_ma_current = data[f'sma_{self.fast_ma}'].iloc[current_idx]
        fast_ma_prev = data[f'sma_{self.fast_ma}'].iloc[prev_idx]
        
        slow_ma_current = data[f'sma_{self.slow_ma}'].iloc[current_idx]
        slow_ma_prev = data[f'sma_{self.slow_ma}'].iloc[prev_idx]
        
        rsi_current = data[f'rsi_{self.rsi_period}'].iloc[current_idx]
        
        # Check for NaN
        if pd.isna(fast_ma_current) or pd.isna(slow_ma_current) or pd.isna(rsi_current):
            return 'HOLD'
        
        # Golden Cross: Fast MA crosses above Slow MA
        if (fast_ma_current > slow_ma_current and 
            fast_ma_prev <= slow_ma_prev and
            rsi_current < 70):
            return 'BUY'
        
        # Death Cross: Fast MA crosses below Slow MA
        elif (fast_ma_current < slow_ma_current and 
              fast_ma_prev >= slow_ma_prev):
            return 'SELL'
        
        return 'HOLD'
```

---

### STEP 6: Add Configuration File for Auto-Optimization

Create `optimization_config.json`:

```json
{
  "use_numba": true,
  "parallel_workers": "auto",
  "precompute_indicators": true,
  "batch_database_operations": true,
  "memory_optimization": {
    "use_float32": false,
    "aggressive_gc": false
  },
  "profiling": {
    "enabled": false,
    "output_dir": "./profiling"
  }
}
```

---

## 📊 Expected Performance Improvements

| Optimization | Speedup | Notes |
|--------------|---------|-------|
| **Numba JIT on Indicators** | 10-100x | One-time compilation cost |
| **Pre-computation** | 3-10x | Calculate once, use many times |
| **Parallel Processing** | 2-8x | Depends on CPU cores |
| **Batch Database Loading** | 5-50x | Already implemented |
| **Overall** | **10-50x** | Combined effect |

**Example**: 
- Before: 9,000 calculations/second
- After: 90,000 - 450,000 calculations/second

---

## ✅ Verification Steps

### 1. Create a test script:

```python
# test_performance.py

import time
import numpy as np
from indicator_base import calculate_rsi, calculate_sma

# Generate test data
prices = np.random.randn(10000).cumsum() + 100

# Test without Numba
start = time.time()
for _ in range(100):
    result = calculate_rsi(pd.DataFrame({'close': prices}), use_numba=False)
python_time = time.time() - start

# Test with Numba
start = time.time()
for _ in range(100):
    result = calculate_rsi(pd.DataFrame({'close': prices}), use_numba=True)
numba_time = time.time() - start

print(f"Python: {python_time:.3f}s")
print(f"Numba:  {numba_time:.3f}s")
print(f"Speedup: {python_time/numba_time:.1f}x")
```

### 2. Run before/after benchmarks:

```bash
# Before optimization
time python main.py --universe sp500

# After optimization
time python main.py --universe sp500
```

---

## 🎓 Key Principles Maintained

✅ **Modularity**: Strategies and indicators remain separate files  
✅ **No Look-Ahead Bias**: Bar-by-bar iteration preserved  
✅ **Telemetry**: All data still recorded  
✅ **Flexibility**: Users can still configure everything  
✅ **Community Development**: Easy to add new strategies/indicators

---

## 🚀 Next Steps

1. **Implement Step 2** (indicator_base.py) first
2. **Test one strategy** with new indicators
3. **Implement Step 3** (simulator.py changes)
4. **Benchmark** and measure improvement
5. **Gradually migrate** other strategies

**Questions? Need help with a specific step? Let me know!**