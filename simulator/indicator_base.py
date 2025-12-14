"""
Optimized Indicator Base with Numba JIT
All indicators use compiled functions for speed
Maintains compatibility with existing indicator system
"""

import numpy as np
import pandas as pd
from numba import jit, prange
from typing import Dict, Any, Optional, List, Union, Tuple
from dataclasses import dataclass
import time
import warnings

# Type definitions
FloatArray = np.ndarray

@dataclass
class IndicatorResult:
    """Result from indicator calculation"""
    name: str
    value: Any  # Single value or array
    params: Dict[str, Any]
    calculation_time_ms: float = 0.0
    success: bool = True
    error: Optional[str] = None

# ============================================================
# NUMBA-OPTIMIZED INDICATOR FUNCTIONS
# These run 10-100x faster than pure Python
# ============================================================

@jit(nopython=True, cache=True, parallel=False)
def sma_numba(prices: FloatArray, period: int) -> FloatArray:
    """Simple Moving Average - Numba optimized"""
    n = len(prices)
    result = np.full(n, np.nan, dtype=np.float64)
    
    for i in range(period - 1, n):
        result[i] = np.mean(prices[i - period + 1:i + 1])
    
    return result

@jit(nopython=True, cache=True, parallel=False)
def ema_numba(prices: FloatArray, period: int) -> FloatArray:
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

@jit(nopython=True, cache=True, parallel=False)
def rsi_numba(prices: FloatArray, period: int = 14) -> FloatArray:
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
    
    # Calculate initial average gain/loss
    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])
    
    # First RSI value
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

@jit(nopython=True, cache=True, parallel=False)
def macd_numba(prices: FloatArray, fast_period: int = 12, slow_period: int = 26, signal_period: int = 9) -> Tuple[FloatArray, FloatArray, FloatArray]:
    """MACD - Numba optimized"""
    n = len(prices)
    
    # Calculate EMAs
    fast_ema = ema_numba(prices, fast_period)
    slow_ema = ema_numba(prices, slow_period)
    
    # MACD line
    macd_line = fast_ema - slow_ema
    
    # Signal line (EMA of MACD line)
    signal_line = ema_numba(macd_line, signal_period)
    
    # Histogram
    histogram = macd_line - signal_line
    
    return macd_line, signal_line, histogram

@jit(nopython=True, cache=True, parallel=False)
def bollinger_bands_numba(prices: FloatArray, period: int = 20, std_dev: float = 2.0) -> Tuple[FloatArray, FloatArray, FloatArray]:
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

@jit(nopython=True, cache=True, parallel=False)
def atr_numba(high: FloatArray, low: FloatArray, close: FloatArray, period: int = 14) -> FloatArray:
    """Average True Range - Numba optimized"""
    n = len(close)
    result = np.full(n, np.nan, dtype=np.float64)
    
    if n < period:
        return result
    
    # Calculate True Range
    tr = np.zeros(n)
    tr[0] = high[0] - low[0]
    
    for i in range(1, n):
        hl = high[i] - low[i]
        hc = abs(high[i] - close[i-1])
        lc = abs(low[i] - close[i-1])
        tr[i] = max(hl, hc, lc)
    
    # Simple moving average of TR
    for i in range(period - 1, n):
        result[i] = np.mean(tr[i - period + 1:i + 1])
    
    return result

@jit(nopython=True, cache=True, parallel=False)
def relative_volume_numba(volumes: FloatArray, period: int = 20) -> FloatArray:
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

@jit(nopython=True, cache=True, parallel=False)
def stochastic_numba(high: FloatArray, low: FloatArray, close: FloatArray, period: int = 14, smooth_k: int = 3, smooth_d: int = 3) -> Tuple[FloatArray, FloatArray]:
    """Stochastic Oscillator - Numba optimized"""
    n = len(close)
    k_line = np.full(n, np.nan, dtype=np.float64)
    d_line = np.full(n, np.nan, dtype=np.float64)
    
    # Calculate %K
    for i in range(period - 1, n):
        highest_high = np.max(high[i - period + 1:i + 1])
        lowest_low = np.min(low[i - period + 1:i + 1])
        
        if highest_high != lowest_low:
            k_line[i] = 100 * (close[i] - lowest_low) / (highest_high - lowest_low)
        else:
            k_line[i] = 50.0
    
    # Smooth %K (if needed)
    if smooth_k > 1:
        smoothed_k = np.full(n, np.nan, dtype=np.float64)
        for i in range(period + smooth_k - 2, n):
            smoothed_k[i] = np.mean(k_line[i - smooth_k + 1:i + 1])
        k_line = smoothed_k
    
    # Calculate %D (smooth_k period moving average of %K)
    for i in range(period + smooth_d - 2, n):
        d_line[i] = np.mean(k_line[i - smooth_d + 1:i + 1])
    
    return k_line, d_line

# ============================================================
# INDICATOR BASE CLASS
# ============================================================

class IndicatorBase:
    """
    Base class for all indicators
    Maintains modular architecture while providing optimized calculations
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
            results[indicator_name] = self._calculate_single(data, indicator_name)
        return results
    
    def _calculate_single(self, data: pd.DataFrame, indicator_name: str) -> IndicatorResult:
        """Calculate a single indicator"""
        # This would dispatch to the appropriate function
        pass

# ============================================================
# OPTIMIZED INDICATOR FUNCTIONS (with caching)
# ============================================================

def calculate_sma(data: pd.DataFrame, period: int = 20, use_numba: bool = True) -> FloatArray:
    """Calculate SMA with optional Numba acceleration"""
    start_time = time.time()
    
    prices = data['close'].values.astype(np.float64)
    
    if use_numba:
        result = sma_numba(prices, period)
    else:
        result = data['close'].rolling(period, min_periods=1).mean().values
    
    calc_time = (time.time() - start_time) * 1000
    
    if np.any(np.isnan(result)):
        # Fill NaN values
        result = np.nan_to_num(result, nan=0.0)
    
    return result

def calculate_ema(data: pd.DataFrame, period: int = 20, use_numba: bool = True) -> FloatArray:
    """Calculate EMA with optional Numba acceleration"""
    prices = data['close'].values.astype(np.float64)
    
    if use_numba:
        result = ema_numba(prices, period)
    else:
        result = data['close'].ewm(span=period, adjust=False, min_periods=1).mean().values
    
    return result

def calculate_rsi(data: pd.DataFrame, period: int = 14, use_numba: bool = True) -> FloatArray:
    """Calculate RSI with optional Numba acceleration"""
    prices = data['close'].values.astype(np.float64)
    
    if use_numba:
        result = rsi_numba(prices, period)
    else:
        deltas = data['close'].diff()
        gain = deltas.where(deltas > 0, 0).rolling(period, min_periods=1).mean()
        loss = (-deltas.where(deltas < 0, 0)).rolling(period, min_periods=1).mean()
        rs = gain / loss
        result = (100 - (100 / (1 + rs))).values
        result = np.nan_to_num(result, nan=50.0)
    
    return result

def calculate_macd(data: pd.DataFrame, fast_period: int = 12, slow_period: int = 26, signal_period: int = 9, use_numba: bool = True) -> Tuple[FloatArray, FloatArray, FloatArray]:
    """Calculate MACD with optional Numba acceleration"""
    prices = data['close'].values.astype(np.float64)
    
    if use_numba:
        macd_line, signal_line, histogram = macd_numba(prices, fast_period, slow_period, signal_period)
    else:
        # Fallback to pandas
        exp1 = data['close'].ewm(span=fast_period, adjust=False).mean()
        exp2 = data['close'].ewm(span=slow_period, adjust=False).mean()
        macd_line = (exp1 - exp2).values
        signal_line = pd.Series(macd_line).ewm(span=signal_period, adjust=False).mean().values
        histogram = macd_line - signal_line
    
    return macd_line, signal_line, histogram

def calculate_bollinger_bands(data: pd.DataFrame, period: int = 20, std_dev: float = 2.0, use_numba: bool = True) -> Tuple[FloatArray, FloatArray, FloatArray]:
    """Calculate Bollinger Bands with optional Numba acceleration"""
    prices = data['close'].values.astype(np.float64)
    
    if use_numba:
        upper, middle, lower = bollinger_bands_numba(prices, period, std_dev)
    else:
        middle = data['close'].rolling(period, min_periods=1).mean()
        std = data['close'].rolling(period, min_periods=1).std()
        upper = (middle + (std * std_dev)).values
        middle = middle.values
        lower = (middle - (std * std_dev)).values
    
    return upper, middle, lower

def calculate_atr(data: pd.DataFrame, period: int = 14, use_numba: bool = True) -> FloatArray:
    """Calculate Average True Range with optional Numba acceleration"""
    high = data['high'].values.astype(np.float64)
    low = data['low'].values.astype(np.float64)
    close = data['close'].values.astype(np.float64)
    
    if use_numba:
        result = atr_numba(high, low, close, period)
    else:
        # Fallback to pandas
        tr1 = data['high'] - data['low']
        tr2 = abs(data['high'] - data['close'].shift())
        tr3 = abs(data['low'] - data['close'].shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        result = tr.rolling(period, min_periods=1).mean().values
    
    return result

def calculate_relative_volume(data: pd.DataFrame, period: int = 20, use_numba: bool = True) -> FloatArray:
    """Calculate relative volume with optional Numba acceleration"""
    volumes = data['volume'].values.astype(np.float64)
    
    if use_numba:
        result = relative_volume_numba(volumes, period)
    else:
        avg_volume = data['volume'].rolling(period, min_periods=1).mean()
        result = (data['volume'] / avg_volume).values
        result = np.nan_to_num(result, nan=1.0)
    
    return result

def calculate_stochastic(data: pd.DataFrame, period: int = 14, smooth_k: int = 3, smooth_d: int = 3, use_numba: bool = True) -> Tuple[FloatArray, FloatArray]:
    """Calculate Stochastic Oscillator with optional Numba acceleration"""
    high = data['high'].values.astype(np.float64)
    low = data['low'].values.astype(np.float64)
    close = data['close'].values.astype(np.float64)
    
    if use_numba:
        k_line, d_line = stochastic_numba(high, low, close, period, smooth_k, smooth_d)
    else:
        # Fallback to pandas
        low_min = data['low'].rolling(period, min_periods=1).min()
        high_max = data['high'].rolling(period, min_periods=1).max()
        k_line = 100 * ((data['close'] - low_min) / (high_max - low_min))
        k_line = k_line.rolling(smooth_k, min_periods=1).mean()
        d_line = k_line.rolling(smooth_d, min_periods=1).mean()
        k_line = k_line.values
        d_line = d_line.values
    
    k_line = np.nan_to_num(k_line, nan=50.0)
    d_line = np.nan_to_num(d_line, nan=50.0)
    
    return k_line, d_line

# ============================================================
# INDICATOR REGISTRY
# ============================================================

BUILTIN_FUNCTIONS = {
    'sma': calculate_sma,
    'ema': calculate_ema,
    'rsi': calculate_rsi,
    'macd': calculate_macd,
    'bollinger_bands': calculate_bollinger_bands,
    'atr': calculate_atr,
    'relative_volume': calculate_relative_volume,
    'stochastic': calculate_stochastic,
}

BUILTIN_CLASSES = {}  # For class-based indicators

# ============================================================
# HELPER FUNCTIONS
# ============================================================

def create_indicator_dataframe(data: pd.DataFrame, indicators_config: Dict[str, Dict]) -> pd.DataFrame:
    """
    Create a dataframe with pre-computed indicators
    This is the key optimization for simulation
    
    Args:
        data: Raw OHLCV data
        indicators_config: Dict of {indicator_name: parameters}
        
    Returns:
        DataFrame with original data + indicator columns
    """
    result_df = data.copy()
    
    print(f"📊 Pre-computing {len(indicators_config)} indicators...")
    start_time = time.time()
    
    for indicator_name, params in indicators_config.items():
        if indicator_name in BUILTIN_FUNCTIONS:
            try:
                # Call the indicator function
                indicator_func = BUILTIN_FUNCTIONS[indicator_name]
                indicator_result = indicator_func(data, **params)
                
                # Add to dataframe
                if isinstance(indicator_result, tuple):
                    # Multiple outputs (like Bollinger Bands, MACD)
                    for i, arr in enumerate(indicator_result):
                        suffix = ['', '_signal', '_hist'][i] if indicator_name == 'macd' else ['_upper', '_middle', '_lower'][i]
                        col_name = f"{indicator_name}{suffix}"
                        result_df[col_name] = arr
                else:
                    # Single output
                    result_df[indicator_name] = indicator_result
                    
            except Exception as e:
                print(f"⚠️  Error computing {indicator_name}: {e}")
                # Add NaN column as fallback
                result_df[indicator_name] = np.nan
    
    elapsed = (time.time() - start_time) * 1000
    print(f"✅ Indicators computed in {elapsed:.1f}ms")
    
    # Fill NaN values
    result_df = result_df.fillna(method='ffill').fillna(method='bfill')
    
    return result_df

def benchmark_indicator_performance(data: pd.DataFrame, num_runs: int = 10) -> Dict[str, float]:
    """
    Benchmark indicator performance with and without Numba
    """
    results = {}
    
    # Test each indicator
    for indicator_name, func in BUILTIN_FUNCTIONS.items():
        # Test without Numba
        start = time.time()
        for _ in range(num_runs):
            try:
                func(data, use_numba=False)
            except:
                pass
        python_time = time.time() - start
        
        # Test with Numba
        start = time.time()
        for _ in range(num_runs):
            try:
                func(data, use_numba=True)
            except:
                pass
        numba_time = time.time() - start
        
        if python_time > 0 and numba_time > 0:
            speedup = python_time / numba_time
            results[indicator_name] = {
                'python_ms': python_time * 1000 / num_runs,
                'numba_ms': numba_time * 1000 / num_runs,
                'speedup': speedup
            }
    
    return results


# Line 604 in indicator_base.py - replace this function:
def precompute_all_indicators(data: pd.DataFrame, 
                              required_indicators: List[str],
                              use_numba: bool = True) -> pd.DataFrame:
    """
    Pre-compute all indicators ONCE before simulation starts
    This is the #1 performance optimization
    
    Args:
        data: OHLCV DataFrame
        required_indicators: List like ['sma_20', 'rsi_14', 'macd_12_26_9']
        use_numba: Enable Numba JIT compilation
        
    Returns:
        DataFrame with all indicator columns added
    """
    enriched_data = data.copy()
    
    print(f"  📊 Pre-computing {len(required_indicators)} indicators...")
    start_time = time.time()
    
    # Parse indicator specifications
    for indicator_spec in required_indicators:
        parts = indicator_spec.split('_')
        indicator_name = parts[0]
        
        # Extract parameters from name (e.g., 'sma_20' → period=20)
        params = {}
        if len(parts) > 1:
            try:
                params['period'] = int(parts[1])
            except ValueError:
                pass
        
        # Handle specific parameter extraction for different indicators
        if indicator_name == 'macd' and len(parts) >= 4:
            try:
                params['fast_period'] = int(parts[1])
                params['slow_period'] = int(parts[2])
                params['signal_period'] = int(parts[3])
            except:
                pass
        elif indicator_name == 'stochastic' and len(parts) >= 4:
            try:
                params['period'] = int(parts[1])
                params['smooth_k'] = int(parts[2])
                params['smooth_d'] = int(parts[3])
            except:
                pass
        elif indicator_name == 'bollinger' and len(parts) >= 2:
            try:
                params['period'] = int(parts[1])
                if len(parts) >= 3:
                    params['std_dev'] = float(parts[2])
                else:
                    params['std_dev'] = 2.0
            except:
                pass
        
        # Call appropriate indicator function
        if indicator_name == 'sma':
            enriched_data[indicator_spec] = calculate_sma(
                data, params.get('period', 20), use_numba
            )
        elif indicator_name == 'ema':
            enriched_data[indicator_spec] = calculate_ema(
                data, params.get('period', 20), use_numba
            )
        elif indicator_name == 'rsi':
            enriched_data[indicator_spec] = calculate_rsi(
                data, params.get('period', 14), use_numba
            )
        elif indicator_name == 'macd':
            macd_line, signal_line, histogram = calculate_macd(
                data, 
                params.get('fast_period', 12),
                params.get('slow_period', 26),
                params.get('signal_period', 9),
                use_numba
            )
            enriched_data[f'{indicator_spec}_line'] = macd_line
            enriched_data[f'{indicator_spec}_signal'] = signal_line
            enriched_data[f'{indicator_spec}_hist'] = histogram
        elif indicator_name == 'bollinger' or indicator_name == 'bollinger_bands':
            upper, middle, lower = calculate_bollinger_bands(
                data,
                params.get('period', 20),
                params.get('std_dev', 2.0),
                use_numba
            )
            enriched_data[f'{indicator_spec}_upper'] = upper
            enriched_data[f'{indicator_spec}_middle'] = middle
            enriched_data[f'{indicator_spec}_lower'] = lower
        elif indicator_name == 'atr':
            enriched_data[indicator_spec] = calculate_atr(
                data, params.get('period', 14), use_numba
            )
        elif indicator_name == 'relative_volume':
            enriched_data[indicator_spec] = calculate_relative_volume(
                data, params.get('period', 20), use_numba
            )
        elif indicator_name == 'stochastic':
            k_line, d_line = calculate_stochastic(
                data,
                params.get('period', 14),
                params.get('smooth_k', 3),
                params.get('smooth_d', 3),
                use_numba
            )
            enriched_data[f'{indicator_spec}_k'] = k_line
            enriched_data[f'{indicator_spec}_d'] = d_line
    
    elapsed = (time.time() - start_time) * 1000
    print(f"  ✅ Indicators computed in {elapsed:.1f}ms")
    
    # Fill NaN values - FIXED: Use ffill() and bfill() instead of fillna(method=...)
    enriched_data = enriched_data.ffill().bfill()
    
    return enriched_data