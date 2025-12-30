"""
Average Directional Index (ADX) Indicator
Measures trend strength for filtering trades and timing entries

ADX measures the strength of a trend regardless of direction. It's commonly used for:
- Trend strength filtering (only trade when ADX > 25)
- Identifying trending vs ranging markets
- Timing trend-following entries

Returns multiple values:
- ADX: Trend strength (0-100)
- +DI: Positive Directional Indicator (upward pressure)
- -DI: Negative Directional Indicator (downward pressure)
"""

import numpy as np
import pandas as pd
import sys
from pathlib import Path

# Add simulator directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from indicator_base import IndicatorBase, IndicatorResult

# Try to import numba for optimization
try:
    from numba import jit
    NUMBA_AVAILABLE = True
except ImportError:
    NUMBA_AVAILABLE = False
    def jit(*args, **kwargs):
        """Dummy decorator when numba not available"""
        def decorator(func):
            return func
        return decorator


@jit(nopython=True, cache=True)
def adx_core(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int) -> tuple:
    """
    Core ADX calculation optimized with Numba

    Algorithm:
    1. Calculate True Range (TR)
    2. Calculate +DM (Positive Directional Movement)
    3. Calculate -DM (Negative Directional Movement)
    4. Smooth TR, +DM, -DM using Wilder's method
    5. Calculate +DI = 100 * smoothed(+DM) / smoothed(TR)
    6. Calculate -DI = 100 * smoothed(-DM) / smoothed(TR)
    7. Calculate DX = 100 * |+DI - -DI| / (+DI + -DI)
    8. ADX = smoothed average of DX

    Returns: (adx, plus_di, minus_di)
    """
    n = len(close)
    adx = np.full(n, np.nan, dtype=np.float64)
    plus_di = np.full(n, np.nan, dtype=np.float64)
    minus_di = np.full(n, np.nan, dtype=np.float64)

    if n < period * 2:
        return adx, plus_di, minus_di

    # Calculate True Range and Directional Movement
    tr = np.zeros(n, dtype=np.float64)
    plus_dm = np.zeros(n, dtype=np.float64)
    minus_dm = np.zeros(n, dtype=np.float64)

    for i in range(1, n):
        # True Range: max(H-L, |H-Prev_C|, |L-Prev_C|)
        hl = high[i] - low[i]
        hc = abs(high[i] - close[i-1])
        lc = abs(low[i] - close[i-1])
        tr[i] = max(hl, hc, lc)

        # Directional Movement
        high_diff = high[i] - high[i-1]
        low_diff = low[i-1] - low[i]

        # +DM: If high_diff > low_diff and high_diff > 0
        if high_diff > low_diff and high_diff > 0:
            plus_dm[i] = high_diff
        # -DM: If low_diff > high_diff and low_diff > 0
        if low_diff > high_diff and low_diff > 0:
            minus_dm[i] = low_diff

    # Smooth TR, +DM, -DM using Wilder's smoothing method
    smoothed_tr = np.zeros(n, dtype=np.float64)
    smoothed_plus_dm = np.zeros(n, dtype=np.float64)
    smoothed_minus_dm = np.zeros(n, dtype=np.float64)

    # Initial values (sum of first period)
    smoothed_tr[period] = np.sum(tr[1:period+1])
    smoothed_plus_dm[period] = np.sum(plus_dm[1:period+1])
    smoothed_minus_dm[period] = np.sum(minus_dm[1:period+1])

    # Apply Wilder's smoothing: smooth[i] = smooth[i-1] - (smooth[i-1]/period) + value[i]
    for i in range(period + 1, n):
        smoothed_tr[i] = smoothed_tr[i-1] - (smoothed_tr[i-1] / period) + tr[i]
        smoothed_plus_dm[i] = smoothed_plus_dm[i-1] - (smoothed_plus_dm[i-1] / period) + plus_dm[i]
        smoothed_minus_dm[i] = smoothed_minus_dm[i-1] - (smoothed_minus_dm[i-1] / period) + minus_dm[i]

    # Calculate +DI and -DI
    for i in range(period, n):
        if smoothed_tr[i] > 0:
            plus_di[i] = 100.0 * (smoothed_plus_dm[i] / smoothed_tr[i])
            minus_di[i] = 100.0 * (smoothed_minus_dm[i] / smoothed_tr[i])

    # Calculate DX (Directional Index)
    dx = np.full(n, np.nan, dtype=np.float64)
    for i in range(period, n):
        di_sum = plus_di[i] + minus_di[i]
        if di_sum > 0:
            di_diff = abs(plus_di[i] - minus_di[i])
            dx[i] = 100.0 * (di_diff / di_sum)

    # Calculate ADX (smoothed average of DX)
    # First ADX value is average of first 'period' DX values
    first_adx_index = period * 2 - 1
    if first_adx_index < n:
        # Average of DX values from period to first_adx_index
        dx_sum = 0.0
        count = 0
        for i in range(period, first_adx_index + 1):
            if not np.isnan(dx[i]):
                dx_sum += dx[i]
                count += 1
        if count > 0:
            adx[first_adx_index] = dx_sum / count

    # Subsequent ADX values use Wilder's smoothing
    for i in range(first_adx_index + 1, n):
        if not np.isnan(adx[i-1]) and not np.isnan(dx[i]):
            adx[i] = ((adx[i-1] * (period - 1)) + dx[i]) / period

    return adx, plus_di, minus_di


class Indicator(IndicatorBase):
    """
    Average Directional Index (ADX) Indicator

    Measures trend strength (not direction) on a scale of 0-100.
    Also returns +DI and -DI for trend direction analysis.

    ADX Interpretation:
        0-20:   Weak or no trend (ranging market)
        20-25:  Emerging trend
        25-50:  Strong trend
        50-75:  Very strong trend
        75-100: Extremely strong trend (rare)

    +DI/-DI Interpretation:
        +DI > -DI: Uptrend (bullish)
        -DI > +DI: Downtrend (bearish)
        DI crossovers: Potential trend change signals

    Parameters:
        period (int): Lookback period (default: 14)

    Returns:
        Multi-value result with 'adx', 'plus_di', 'minus_di'
    """

    def __init__(self):
        super().__init__(name="ADX", use_numba=NUMBA_AVAILABLE)
        self.version = "1.0"
        self.dependencies = []

    def calculate(self, data: pd.DataFrame, **params) -> IndicatorResult:
        """
        Calculate ADX, +DI, and -DI

        Args:
            data: DataFrame with 'high', 'low', 'close' columns
            **params:
                period (int): ADX period (default: 14)

        Returns:
            IndicatorResult with multi-value dict containing:
                - 'adx': Average Directional Index values
                - 'plus_di': Positive Directional Indicator values
                - 'minus_di': Negative Directional Indicator values
        """
        period = params.get('period', 14)

        # Validate data
        min_required = period * 2
        if len(data) < min_required:
            return self._error(f"Need at least {min_required} bars, got {len(data)}")

        required_columns = ['high', 'low', 'close']
        for col in required_columns:
            if col not in data.columns:
                return self._error(f"Missing required column: {col}")

        # Extract price data
        high = data['high'].values.astype(np.float64)
        low = data['low'].values.astype(np.float64)
        close = data['close'].values.astype(np.float64)

        # Calculate ADX components
        adx_values, plus_di_values, minus_di_values = adx_core(high, low, close, period)

        # Handle NaN values - fill with neutral values
        adx_values = np.nan_to_num(adx_values, nan=0.0)
        plus_di_values = np.nan_to_num(plus_di_values, nan=25.0)
        minus_di_values = np.nan_to_num(minus_di_values, nan=25.0)

        # Return as multi-value result
        result_dict = {
            'adx': adx_values,
            'plus_di': plus_di_values,
            'minus_di': minus_di_values
        }

        return IndicatorResult(
            name=f"{self.name}_{period}",
            value=result_dict,
            params={'period': period},
            success=True
        )

    def _error(self, message: str) -> IndicatorResult:
        """Create error result"""
        return IndicatorResult(
            name=self.name,
            value=None,
            params={},
            success=False,
            error=message
        )

    def is_trending(self, data: pd.DataFrame, threshold: float = 25.0,
                    period: int = 14) -> bool:
        """
        Check if market is currently trending

        Args:
            data: DataFrame with OHLC data
            threshold: ADX threshold for trending (default: 25)
            period: ADX period

        Returns:
            True if ADX > threshold (trending), False otherwise
        """
        result = self.calculate(data, period=period)

        if not result.success or result.value is None:
            return False

        current_adx = result.value['adx'][-1]
        return current_adx > threshold

    def get_trend_direction(self, data: pd.DataFrame, period: int = 14) -> str:
        """
        Get current trend direction based on DI crossover

        Args:
            data: DataFrame with OHLC data
            period: ADX period

        Returns:
            'bullish', 'bearish', or 'neutral'
        """
        result = self.calculate(data, period=period)

        if not result.success or result.value is None:
            return 'neutral'

        plus_di = result.value['plus_di'][-1]
        minus_di = result.value['minus_di'][-1]

        if plus_di > minus_di:
            return 'bullish'
        elif minus_di > plus_di:
            return 'bearish'
        else:
            return 'neutral'

    def get_trend_strength(self, data: pd.DataFrame, period: int = 14) -> str:
        """
        Get qualitative trend strength

        Args:
            data: DataFrame with OHLC data
            period: ADX period

        Returns:
            'none', 'weak', 'moderate', 'strong', or 'very_strong'
        """
        result = self.calculate(data, period=period)

        if not result.success or result.value is None:
            return 'none'

        current_adx = result.value['adx'][-1]

        if current_adx < 20:
            return 'none'
        elif current_adx < 25:
            return 'weak'
        elif current_adx < 40:
            return 'moderate'
        elif current_adx < 50:
            return 'strong'
        else:
            return 'very_strong'

    def get_signal(self, data: pd.DataFrame, adx_threshold: float = 25.0,
                   period: int = 14) -> dict:
        """
        Get comprehensive ADX signal analysis

        Args:
            data: DataFrame with OHLC data
            adx_threshold: Minimum ADX for trend confirmation
            period: ADX period

        Returns:
            dict with 'is_trending', 'direction', 'strength', 'adx', 'plus_di', 'minus_di'
        """
        result = self.calculate(data, period=period)

        if not result.success or result.value is None:
            return {
                'is_trending': False,
                'direction': 'neutral',
                'strength': 'none',
                'adx': 0.0,
                'plus_di': 0.0,
                'minus_di': 0.0
            }

        adx = result.value['adx'][-1]
        plus_di = result.value['plus_di'][-1]
        minus_di = result.value['minus_di'][-1]

        return {
            'is_trending': adx > adx_threshold,
            'direction': 'bullish' if plus_di > minus_di else ('bearish' if minus_di > plus_di else 'neutral'),
            'strength': self.get_trend_strength(data, period),
            'adx': adx,
            'plus_di': plus_di,
            'minus_di': minus_di
        }


# Standalone function for quick calculations
def calculate_adx(data: pd.DataFrame, period: int = 14) -> dict:
    """
    Quick ADX calculation without indicator class

    Args:
        data: DataFrame with 'high', 'low', 'close' columns
        period: ADX period (default: 14)

    Returns:
        dict with 'adx', 'plus_di', 'minus_di' arrays
    """
    indicator = Indicator()
    result = indicator.calculate(data, period=period)
    return result.value if result.success else {'adx': np.array([]), 'plus_di': np.array([]), 'minus_di': np.array([])}
