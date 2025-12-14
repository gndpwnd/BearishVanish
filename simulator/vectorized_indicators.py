"""
Vectorized Indicator Library with Numba JIT Optimization
All indicators calculated in batch for entire time series
Expected speedup: 10-100x over bar-by-bar calculations
"""

import numpy as np
import pandas as pd
from numba import jit, prange, vectorize, float64, int64
from numba.typed import Dict
import numba
from typing import Dict as TypedDict, List, Tuple, Optional, Union
from dataclasses import dataclass
import time

# Type aliases
FloatArray = np.ndarray
BoolArray = np.ndarray
IntArray = np.ndarray


@dataclass
class IndicatorResult:
    """Container for indicator results with metadata"""
    values: FloatArray
    name: str
    params: dict
    calculation_time_ms: float


class VectorizedIndicators:
    """
    Main vectorized indicator calculator
    Pre-computes ALL indicators at once for maximum performance
    """
    
    def __init__(self, use_numba=True, cache_results=True):
        self.use_numba = use_numba
        self.cache_results = cache_results
        self.cache = {}
        self.dependency_graph = {}
        
        # Register all indicator functions
        self._register_indicators()
    
    def _register_indicators(self):
        """Register all available indicators"""
        self.indicators = {
            'sma': self.sma,
            'ema': self.ema,
            'rsi': self.rsi,
            'bollinger_bands': self.bollinger_bands,
            'macd': self.macd,
            'atr': self.atr,
            'stochastic': self.stochastic,
            'williams_r': self.williams_r,
            'volume_sma': self.volume_sma,
            'relative_volume': self.relative_volume,
            'vwap': self.vwap,
            'obv': self.obv,
            'adl': self.adl,
            'cci': self.cci,
            'roc': self.roc,
            'momentum': self.momentum,
            'volatility': self.volatility,
            'correlation': self.correlation,
            'beta': self.beta,
            'sharpe': self.sharpe,
            'sortino': self.sortino,
        }
        
        # Define dependencies
        self.dependency_graph = {
            'bollinger_bands': ['sma'],
            'macd': ['ema'],
            'rsi': ['momentum'],
            'stochastic': ['high', 'low', 'close'],
            'williams_r': ['high', 'low', 'close'],
            'relative_volume': ['volume_sma'],
            'atr': ['high', 'low', 'close'],
            'cci': ['sma', 'atr'],
            'sortino': ['returns', 'volatility']
        }
    
    def calculate_all(self, data: pd.DataFrame, indicators: List[str] = None) -> TypedDict[str, IndicatorResult]:
        """
        Calculate ALL indicators at once for maximum performance
        
        Args:
            data: DataFrame with OHLCV columns
            indicators: List of indicator names to calculate (None = all)
            
        Returns:
            Dict of indicator_name -> IndicatorResult
        """
        start_time = time.time()
        
        # Convert to numpy arrays for speed
        arrays = self._prepare_arrays(data)
        
        # Determine which indicators to calculate
        if indicators is None:
            indicators = list(self.indicators.keys())
        
        # Calculate in optimal order (respect dependencies)
        calculation_order = self._get_calculation_order(indicators)
        
        results = {}
        
        for indicator_name in calculation_order:
            cache_key = self._get_cache_key(indicator_name, arrays)
            
            if self.cache_results and cache_key in self.cache:
                results[indicator_name] = self.cache[cache_key]
                continue
            
            # Calculate indicator
            indicator_func = self.indicators[indicator_name]
            indicator_start = time.time()
            
            try:
                if indicator_name in ['sma', 'ema', 'rsi', 'volume_sma']:
                    # Standard indicators
                    result_values = indicator_func(
                        arrays['close'], 
                        **self._get_indicator_params(indicator_name)
                    )
                elif indicator_name in ['bollinger_bands', 'macd']:
                    # Multi-output indicators
                    result_values = indicator_func(
                        arrays['close'],
                        **self._get_indicator_params(indicator_name)
                    )
                elif indicator_name in ['atr', 'stochastic', 'williams_r']:
                    # OHLC-based indicators
                    result_values = indicator_func(
                        arrays['high'], arrays['low'], arrays['close'],
                        **self._get_indicator_params(indicator_name)
                    )
                elif indicator_name == 'relative_volume':
                    # Volume-based indicators
                    result_values = indicator_func(
                        arrays['volume'],
                        **self._get_indicator_params(indicator_name)
                    )
                else:
                    # Generic indicator
                    result_values = indicator_func(arrays, **self._get_indicator_params(indicator_name))
                
                # Create result object
                calculation_time = (time.time() - indicator_start) * 1000
                result = IndicatorResult(
                    values=result_values,
                    name=indicator_name,
                    params=self._get_indicator_params(indicator_name),
                    calculation_time_ms=calculation_time
                )
                
                results[indicator_name] = result
                
                # Cache result
                if self.cache_results:
                    self.cache[cache_key] = result
                    
            except Exception as e:
                print(f"⚠️  Error calculating {indicator_name}: {e}")
                # Fill with NaN
                results[indicator_name] = IndicatorResult(
                    values=np.full(len(data), np.nan),
                    name=indicator_name,
                    params={},
                    calculation_time_ms=0
                )
        
        total_time = (time.time() - start_time) * 1000
        
        if total_time > 100:
            print(f"📊 Calculated {len(results)} indicators in {total_time:.1f}ms "
                  f"({total_time/len(data):.3f}ms per bar)")
        
        return results
    
    def _prepare_arrays(self, data: pd.DataFrame) -> TypedDict[str, FloatArray]:
        """Convert DataFrame columns to optimized numpy arrays"""
        arrays = {
            'open': data['open'].values.astype(np.float32),
            'high': data['high'].values.astype(np.float32),
            'low': data['low'].values.astype(np.float32),
            'close': data['close'].values.astype(np.float32),
            'volume': data['volume'].values.astype(np.float64),  # Volume can be large
        }
        
        # Add returns if not present
        if 'returns' not in data.columns:
            arrays['returns'] = np.zeros_like(arrays['close'])
            arrays['returns'][1:] = np.diff(arrays['close']) / arrays['close'][:-1]
        else:
            arrays['returns'] = data['returns'].values.astype(np.float32)
        
        return arrays
    
    def _get_cache_key(self, indicator_name: str, arrays: TypedDict) -> str:
        """Generate cache key based on indicator and data"""
        # Use hash of first and last values for quick comparison
        data_hash = hash((
            arrays['close'][0], arrays['close'][-1], 
            len(arrays['close']),
            indicator_name
        ))
        return f"{indicator_name}_{data_hash}"
    
    def _get_calculation_order(self, indicators: List[str]) -> List[str]:
        """Get calculation order respecting dependencies"""
        # Simple topological sort (implement properly if complex)
        ordered = []
        remaining = set(indicators)
        
        while remaining:
            # Find indicators with no unmet dependencies
            for indicator in list(remaining):
                deps = self.dependency_graph.get(indicator, [])
                unmet_deps = [d for d in deps if d in remaining]
                
                if not unmet_deps:
                    ordered.append(indicator)
                    remaining.remove(indicator)
            
            if not ordered and remaining:
                # Circular dependency or missing dep, just add remaining
                ordered.extend(remaining)
                break
        
        return ordered
    
    def _get_indicator_params(self, indicator_name: str) -> dict:
        """Get default parameters for each indicator"""
        params = {
            'sma': {'period': 20},
            'ema': {'period': 12},
            'rsi': {'period': 14},
            'bollinger_bands': {'period': 20, 'std_dev': 2},
            'macd': {'fast': 12, 'slow': 26, 'signal': 9},
            'atr': {'period': 14},
            'stochastic': {'k_period': 14, 'd_period': 3},
            'williams_r': {'period': 14},
            'volume_sma': {'period': 20},
            'relative_volume': {'period': 20},
            'vwap': {},  # Uses entire series
            'obv': {},
            'adl': {},
            'cci': {'period': 20},
            'roc': {'period': 12},
            'momentum': {'period': 10},
            'volatility': {'period': 20},
            'correlation': {'period': 20},
            'beta': {'period': 20},
            'sharpe': {'period': 20, 'risk_free': 0.02},
            'sortino': {'period': 20, 'risk_free': 0.02},
        }
        return params.get(indicator_name, {})
    
    # ============================================================
    # NUMBA-OPTIMIZED INDICATOR FUNCTIONS
    # ============================================================
    
    @staticmethod
    @jit(nopython=True, cache=True, parallel=False)
    def sma(prices: FloatArray, period: int = 20) -> FloatArray:
        """Simple Moving Average - Numba optimized"""
        n = len(prices)
        sma_values = np.full(n, np.nan, dtype=np.float32)
        
        if n < period:
            return sma_values
        
        # Initial window sum
        window_sum = 0.0
        for i in range(period):
            window_sum += prices[i]
        
        sma_values[period-1] = window_sum / period
        
        # Sliding window
        for i in range(period, n):
            window_sum = window_sum - prices[i-period] + prices[i]
            sma_values[i] = window_sum / period
        
        return sma_values
    
    @staticmethod
    @jit(nopython=True, cache=True)
    def ema(prices: FloatArray, period: int = 12) -> FloatArray:
        """Exponential Moving Average - Numba optimized"""
        n = len(prices)
        ema_values = np.full(n, np.nan, dtype=np.float32)
        
        if n < period:
            return ema_values
        
        # SMA as first EMA
        sma_init = 0.0
        for i in range(period):
            sma_init += prices[i]
        ema_values[period-1] = sma_init / period
        
        # EMA multiplier
        multiplier = 2.0 / (period + 1)
        
        # Calculate EMA
        for i in range(period, n):
            ema_values[i] = (prices[i] - ema_values[i-1]) * multiplier + ema_values[i-1]
        
        return ema_values
    
    @staticmethod
    @jit(nopython=True, cache=True, parallel=True)
    def rsi(prices: FloatArray, period: int = 14) -> FloatArray:
        """Relative Strength Index - Numba optimized with parallel processing"""
        n = len(prices)
        rsi_values = np.full(n, 50.0, dtype=np.float32)  # Default to 50
        
        if n <= period:
            return rsi_values
        
        # Calculate price changes
        deltas = np.zeros(n, dtype=np.float32)
        for i in prange(1, n):
            deltas[i] = prices[i] - prices[i-1]
        
        # Calculate gains and losses
        gains = np.zeros(n, dtype=np.float32)
        losses = np.zeros(n, dtype=np.float32)
        
        for i in prange(n):
            if deltas[i] > 0:
                gains[i] = deltas[i]
            else:
                losses[i] = -deltas[i]
        
        # Calculate first average gains/losses
        avg_gain = 0.0
        avg_loss = 0.0
        
        for i in range(1, period + 1):
            avg_gain += gains[i]
            avg_loss += losses[i]
        
        avg_gain /= period
        avg_loss /= period
        
        # First RSI value
        if avg_loss == 0:
            rsi_values[period] = 100.0
        else:
            rs = avg_gain / avg_loss
            rsi_values[period] = 100.0 - (100.0 / (1.0 + rs))
        
        # Calculate remaining RSI values
        for i in range(period + 1, n):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period
            
            if avg_loss == 0:
                rsi_values[i] = 100.0
            else:
                rs = avg_gain / avg_loss
                rsi_values[i] = 100.0 - (100.0 / (1.0 + rs))
        
        return rsi_values
    
    @staticmethod
    @jit(nopython=True, cache=True)
    def bollinger_bands(prices: FloatArray, period: int = 20, std_dev: float = 2.0) -> Tuple[FloatArray, FloatArray, FloatArray]:
        """Bollinger Bands - Returns (upper, middle, lower)"""
        n = len(prices)
        
        # Calculate SMA (middle band)
        middle = VectorizedIndicators.sma(prices, period)
        
        # Initialize bands
        upper = np.full(n, np.nan, dtype=np.float32)
        lower = np.full(n, np.nan, dtype=np.float32)
        
        # Calculate standard deviation and bands
        for i in range(period-1, n):
            if np.isnan(middle[i]):
                continue
            
            # Calculate standard deviation for the window
            window_start = i - period + 1
            window_end = i + 1
            
            window_prices = prices[window_start:window_end]
            window_std = np.std(window_prices)
            
            upper[i] = middle[i] + (std_dev * window_std)
            lower[i] = middle[i] - (std_dev * window_std)
        
        return upper, middle, lower
    
    @staticmethod
    @jit(nopython=True, cache=True)
    def macd(prices: FloatArray, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[FloatArray, FloatArray, FloatArray]:
        """MACD - Returns (macd_line, signal_line, histogram)"""
        # Calculate EMAs
        ema_fast = VectorizedIndicators.ema(prices, fast)
        ema_slow = VectorizedIndicators.ema(prices, slow)
        
        # MACD line
        macd_line = ema_fast - ema_slow
        
        # Signal line (EMA of MACD line)
        signal_line = VectorizedIndicators.ema(macd_line, signal)
        
        # Histogram
        histogram = macd_line - signal_line
        
        return macd_line, signal_line, histogram
    
    @staticmethod
    @jit(nopython=True, cache=True)
    def atr(high: FloatArray, low: FloatArray, close: FloatArray, period: int = 14) -> FloatArray:
        """Average True Range"""
        n = len(high)
        atr_values = np.full(n, np.nan, dtype=np.float32)
        
        if n < period:
            return atr_values
        
        # Calculate True Range
        tr = np.zeros(n, dtype=np.float32)
        
        for i in range(n):
            if i == 0:
                tr[i] = high[i] - low[i]
            else:
                hl = high[i] - low[i]
                hc = abs(high[i] - close[i-1])
                lc = abs(low[i] - close[i-1])
                tr[i] = max(hl, hc, lc)
        
        # First ATR is simple average of first period TRs
        atr_sum = 0.0
        for i in range(period):
            atr_sum += tr[i]
        
        atr_values[period-1] = atr_sum / period
        
        # Wilder's smoothing method
        for i in range(period, n):
            atr_values[i] = (atr_values[i-1] * (period - 1) + tr[i]) / period
        
        return atr_values
    
    @staticmethod
    @jit(nopython=True, cache=True, parallel=True)
    def volume_sma(volume: FloatArray, period: int = 20) -> FloatArray:
        """Volume Simple Moving Average"""
        n = len(volume)
        sma_values = np.full(n, np.nan, dtype=np.float64)
        
        if n < period:
            return sma_values
        
        # Use parallel processing for volume (often large arrays)
        for i in prange(period-1, n):
            window_sum = 0.0
            for j in range(i-period+1, i+1):
                window_sum += volume[j]
            sma_values[i] = window_sum / period
        
        return sma_values
    
    @staticmethod
    @jit(nopynumber=True, cache=True)
    def relative_volume(volume: FloatArray, period: int = 20) -> FloatArray:
        """Relative Volume (current volume / average volume)"""
        n = len(volume)
        rvol_values = np.ones(n, dtype=np.float32)
        
        if n < period:
            return rvol_values
        
        # Calculate volume SMA
        volume_sma = VectorizedIndicators.volume_sma(volume, period)
        
        # Calculate relative volume
        for i in range(period-1, n):
            if volume_sma[i] > 0:
                rvol_values[i] = volume[i] / volume_sma[i]
            else:
                rvol_values[i] = 1.0
        
        return rvol_values
    
    @staticmethod
    @jit(nopython=True, cache=True, parallel=True)
    def stochastic(high: FloatArray, low: FloatArray, close: FloatArray, 
                   k_period: int = 14, d_period: int = 3) -> Tuple[FloatArray, FloatArray]:
        """Stochastic Oscillator - Returns (%K, %D)"""
        n = len(close)
        
        %K = np.full(n, np.nan, dtype=np.float32)
        %D = np.full(n, np.nan, dtype=np.float32)
        
        if n < k_period:
            return %K, %D
        
        # Calculate %K
        for i in prange(k_period-1, n):
            window_high = high[i-k_period+1:i+1].max()
            window_low = low[i-k_period+1:i+1].min()
            
            if window_high != window_low:
                %K[i] = ((close[i] - window_low) / (window_high - window_low)) * 100
            else:
                %K[i] = 50.0  # Neutral
        
        # Calculate %D (SMA of %K)
        for i in range(k_period + d_period - 2, n):
            %D[i] = np.mean(%K[i-d_period+1:i+1])
        
        return %K, %D
    
    # Additional indicator methods would follow similar pattern...
    
    def calculate_returns(self, prices: FloatArray) -> FloatArray:
        """Calculate percentage returns"""
        returns = np.zeros_like(prices)
        returns[1:] = np.diff(prices) / prices[:-1]
        return returns
    
    def calculate_volatility(self, returns: FloatArray, period: int = 20) -> FloatArray:
        """Calculate rolling volatility (standard deviation of returns)"""
        n = len(returns)
        volatility = np.full(n, np.nan, dtype=np.float32)
        
        if n < period:
            return volatility
        
        for i in range(period-1, n):
            window = returns[i-period+1:i+1]
            volatility[i] = np.std(window) * np.sqrt(252)  # Annualized
        
        return volatility


# Global instance for easy access
_indicator_library = None

def get_indicator_library(use_numba=True, cache_results=True):
    """Get or create global indicator library"""
    global _indicator_library
    if _indicator_library is None:
        _indicator_library = VectorizedIndicators(
            use_numba=use_numba,
            cache_results=cache_results
        )
    return _indicator_library


# Performance test function
def benchmark_indicators():
    """Benchmark indicator performance"""
    import time
    
    # Create test data
    np.random.seed(42)
    n_points = 10000
    test_data = pd.DataFrame({
        'open': np.random.randn(n_points).cumsum() + 100,
        'high': np.random.randn(n_points).cumsum() + 105,
        'low': np.random.randn(n_points).cumsum() + 95,
        'close': np.random.randn(n_points).cumsum() + 100,
        'volume': np.random.randint(100000, 1000000, n_points)
    })
    
    # Test vectorized vs sequential
    library = get_indicator_library()
    
    print(f"📊 Benchmarking indicators on {n_points:,} data points")
    
    # Test 1: Vectorized batch calculation
    start = time.time()
    results = library.calculate_all(test_data, ['sma', 'rsi', 'bollinger_bands', 'macd', 'atr'])
    vectorized_time = time.time() - start
    
    print(f"✅ Vectorized: {len(results)} indicators in {vectorized_time*1000:.1f}ms")
    print(f"   Speed: {n_points/vectorized_time:,.0f} bars/second")
    
    # Test 2: Individual sequential (simulated)
    start = time.time()
    for i in range(len(test_data)):
        if i >= 20:
            # Simulate SMA calculation
            window = test_data['close'].iloc[i-19:i+1]
            _ = window.mean()
    sequential_time = time.time() - start
    
    print(f"⚠️  Sequential: {sequential_time*1000:.1f}ms (simulated)")
    print(f"   Speedup: {sequential_time/vectorized_time:.1f}x")
    
    return results