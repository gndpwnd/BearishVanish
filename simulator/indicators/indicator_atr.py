"""
Average True Range (ATR) Indicator
Measures market volatility for stop-loss placement and position sizing

ATR is a volatility indicator that shows how much an asset moves on average
during a given time period. It's commonly used for:
- Volatility-based stop losses
- Position sizing
- Identifying breakout potential
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
def atr_core(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int) -> np.ndarray:
    """
    Core ATR calculation optimized with Numba

    True Range = max(
        High - Low,
        abs(High - Previous Close),
        abs(Low - Previous Close)
    )

    ATR = Simple Moving Average of True Range over period
    """
    n = len(close)
    result = np.full(n, np.nan, dtype=np.float64)

    if n < period:
        return result

    # Calculate True Range
    tr = np.zeros(n, dtype=np.float64)
    tr[0] = high[0] - low[0]

    for i in range(1, n):
        hl = high[i] - low[i]
        hc = abs(high[i] - close[i-1])
        lc = abs(low[i] - close[i-1])
        tr[i] = max(hl, hc, lc)

    # Calculate ATR as SMA of True Range
    for i in range(period - 1, n):
        result[i] = np.mean(tr[i - period + 1:i + 1])

    return result


@jit(nopython=True, cache=True)
def atr_wilder(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int) -> np.ndarray:
    """
    Wilder's smoothed ATR (original method)
    Uses exponential smoothing instead of simple average
    """
    n = len(close)
    result = np.full(n, np.nan, dtype=np.float64)

    if n < period:
        return result

    # Calculate True Range
    tr = np.zeros(n, dtype=np.float64)
    tr[0] = high[0] - low[0]

    for i in range(1, n):
        hl = high[i] - low[i]
        hc = abs(high[i] - close[i-1])
        lc = abs(low[i] - close[i-1])
        tr[i] = max(hl, hc, lc)

    # First ATR is SMA of True Range
    result[period - 1] = np.mean(tr[:period])

    # Subsequent values use Wilder's smoothing
    for i in range(period, n):
        result[i] = (result[i-1] * (period - 1) + tr[i]) / period

    return result


class Indicator(IndicatorBase):
    """
    Average True Range (ATR) Indicator

    Measures market volatility by calculating the average of true ranges
    over a specified period. True range accounts for gaps between sessions.

    Usage:
        - Volatility-based stop losses: Stop at entry - (ATR * multiplier)
        - Position sizing: Risk per share = ATR * multiplier
        - Breakout detection: Large move > ATR indicates significant move

    Parameters:
        period (int): Lookback period for ATR calculation (default: 14)
        smoothing (str): 'sma' for simple average, 'wilder' for Wilder's smoothing (default: 'sma')

    Returns:
        Single array of ATR values
    """

    def __init__(self):
        super().__init__(name="ATR", use_numba=NUMBA_AVAILABLE)
        self.version = "1.0"
        self.dependencies = []

    def calculate(self, data: pd.DataFrame, **params) -> IndicatorResult:
        """
        Calculate Average True Range

        Args:
            data: DataFrame with 'high', 'low', 'close' columns
            **params:
                period (int): ATR period (default: 14)
                smoothing (str): 'sma' or 'wilder' (default: 'sma')

        Returns:
            IndicatorResult with ATR values
        """
        period = params.get('period', 14)
        smoothing = params.get('smoothing', 'sma')

        # Validate data
        if len(data) < period:
            return self._error(f"Need at least {period} bars, got {len(data)}")

        required_columns = ['high', 'low', 'close']
        for col in required_columns:
            if col not in data.columns:
                return self._error(f"Missing required column: {col}")

        # Extract price data
        high = data['high'].values.astype(np.float64)
        low = data['low'].values.astype(np.float64)
        close = data['close'].values.astype(np.float64)

        # Calculate ATR
        if smoothing == 'wilder':
            atr_values = atr_wilder(high, low, close, period)
        else:
            atr_values = atr_core(high, low, close, period)

        # Handle NaN values
        atr_values = np.nan_to_num(atr_values, nan=0.0)

        return IndicatorResult(
            name=f"{self.name}_{period}",
            value=atr_values,
            params={'period': period, 'smoothing': smoothing},
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

    def get_stop_loss(self, data: pd.DataFrame, entry_price: float,
                      direction: str = 'long', multiplier: float = 2.0,
                      period: int = 14) -> float:
        """
        Calculate volatility-based stop loss price

        Args:
            data: DataFrame with OHLC data
            entry_price: Entry price of the trade
            direction: 'long' or 'short'
            multiplier: ATR multiplier for stop distance
            period: ATR period

        Returns:
            Stop loss price
        """
        result = self.calculate(data, period=period)

        if not result.success or result.value is None:
            return 0.0

        current_atr = result.value[-1]
        stop_distance = current_atr * multiplier

        if direction == 'long':
            return entry_price - stop_distance
        else:
            return entry_price + stop_distance

    def get_position_size(self, data: pd.DataFrame, account_value: float,
                          risk_percent: float = 0.02, multiplier: float = 2.0,
                          period: int = 14) -> int:
        """
        Calculate position size based on ATR-based risk

        Args:
            data: DataFrame with OHLC data
            account_value: Total account value
            risk_percent: Percentage of account to risk (default: 2%)
            multiplier: ATR multiplier for stop distance
            period: ATR period

        Returns:
            Number of shares to buy
        """
        result = self.calculate(data, period=period)

        if not result.success or result.value is None:
            return 0

        current_atr = result.value[-1]

        if current_atr <= 0:
            return 0

        risk_amount = account_value * risk_percent
        risk_per_share = current_atr * multiplier

        return int(risk_amount / risk_per_share)


# Standalone function for quick calculations
def calculate_atr(data: pd.DataFrame, period: int = 14, smoothing: str = 'sma') -> np.ndarray:
    """
    Quick ATR calculation without indicator class

    Args:
        data: DataFrame with 'high', 'low', 'close' columns
        period: ATR period (default: 14)
        smoothing: 'sma' or 'wilder' (default: 'sma')

    Returns:
        numpy array of ATR values
    """
    indicator = Indicator()
    result = indicator.calculate(data, period=period, smoothing=smoothing)
    return result.value if result.success else np.array([])
