"""
Advanced World-Class Indicators for Institutional Trading
Includes VWAP, Money Flow Index, ADX, Ichimoku, OBV, and more
All optimized with Numba JIT for maximum performance
"""

import numpy as np
import pandas as pd
from numba import jit
from typing import Tuple

# Type definitions
FloatArray = np.ndarray


# ============================================================
# VOLUME-BASED INDICATORS
# ============================================================

@jit(nopython=True, cache=True)
def vwap_numba(high: FloatArray, low: FloatArray, close: FloatArray, volume: FloatArray) -> FloatArray:
    """
    Volume-Weighted Average Price (VWAP)
    Used by institutions to assess trade quality and identify support/resistance

    VWAP = Cumulative(Typical Price × Volume) / Cumulative(Volume)
    """
    n = len(close)
    result = np.full(n, np.nan, dtype=np.float64)

    # Calculate typical price
    typical_price = (high + low + close) / 3.0

    # Cumulative calculation
    cumulative_tpv = 0.0  # Typical Price × Volume
    cumulative_volume = 0.0

    for i in range(n):
        if volume[i] > 0:
            cumulative_tpv += typical_price[i] * volume[i]
            cumulative_volume += volume[i]

            if cumulative_volume > 0:
                result[i] = cumulative_tpv / cumulative_volume

    return result


@jit(nopython=True, cache=True)
def mfi_numba(high: FloatArray, low: FloatArray, close: FloatArray, volume: FloatArray, period: int = 14) -> FloatArray:
    """
    Money Flow Index (MFI)
    Volume-weighted RSI - shows money flow into/out of asset

    Range: 0-100
    < 20: Oversold
    > 80: Overbought
    """
    n = len(close)
    result = np.full(n, np.nan, dtype=np.float64)

    if n < period + 1:
        return result

    # Calculate typical price
    typical_price = (high + low + close) / 3.0

    # Calculate money flow
    money_flow = typical_price * volume

    # Calculate positive and negative money flow
    for i in range(period, n):
        positive_flow = 0.0
        negative_flow = 0.0

        for j in range(i - period + 1, i + 1):
            if j > 0:
                if typical_price[j] > typical_price[j-1]:
                    positive_flow += money_flow[j]
                elif typical_price[j] < typical_price[j-1]:
                    negative_flow += money_flow[j]

        if negative_flow == 0:
            result[i] = 100.0
        else:
            money_ratio = positive_flow / negative_flow
            result[i] = 100.0 - (100.0 / (1.0 + money_ratio))

    return result


@jit(nopython=True, cache=True)
def obv_numba(close: FloatArray, volume: FloatArray) -> FloatArray:
    """
    On-Balance Volume (OBV)
    Cumulative volume indicator that adds volume on up days, subtracts on down days

    Used to confirm trends:
    - Rising OBV + Rising Price = Strong uptrend
    - Falling OBV + Rising Price = Weak uptrend (divergence)
    """
    n = len(close)
    result = np.zeros(n, dtype=np.float64)

    if n < 2:
        return result

    result[0] = volume[0]

    for i in range(1, n):
        if close[i] > close[i-1]:
            result[i] = result[i-1] + volume[i]
        elif close[i] < close[i-1]:
            result[i] = result[i-1] - volume[i]
        else:
            result[i] = result[i-1]

    return result


# ============================================================
# TREND STRENGTH INDICATORS
# ============================================================

@jit(nopython=True, cache=True)
def adx_numba(high: FloatArray, low: FloatArray, close: FloatArray, period: int = 14) -> Tuple[FloatArray, FloatArray, FloatArray]:
    """
    Average Directional Index (ADX)
    Measures trend strength (not direction)

    Returns: (ADX, +DI, -DI)

    ADX Values:
    < 20: Weak or no trend
    20-25: Emerging trend
    25-50: Strong trend
    > 50: Very strong trend

    +DI > -DI: Uptrend
    -DI > +DI: Downtrend
    """
    n = len(close)
    adx = np.full(n, np.nan, dtype=np.float64)
    plus_di = np.full(n, np.nan, dtype=np.float64)
    minus_di = np.full(n, np.nan, dtype=np.float64)

    if n < period * 2:
        return adx, plus_di, minus_di

    # Calculate True Range and Directional Movement
    tr = np.zeros(n)
    plus_dm = np.zeros(n)
    minus_dm = np.zeros(n)

    for i in range(1, n):
        # True Range
        hl = high[i] - low[i]
        hc = abs(high[i] - close[i-1])
        lc = abs(low[i] - close[i-1])
        tr[i] = max(hl, hc, lc)

        # Directional Movement
        high_diff = high[i] - high[i-1]
        low_diff = low[i-1] - low[i]

        if high_diff > low_diff and high_diff > 0:
            plus_dm[i] = high_diff
        if low_diff > high_diff and low_diff > 0:
            minus_dm[i] = low_diff

    # Smooth TR and DM using Wilder's smoothing (EMA-like)
    smoothed_tr = np.zeros(n)
    smoothed_plus_dm = np.zeros(n)
    smoothed_minus_dm = np.zeros(n)

    # Initial values (sum of first period)
    smoothed_tr[period] = np.sum(tr[1:period+1])
    smoothed_plus_dm[period] = np.sum(plus_dm[1:period+1])
    smoothed_minus_dm[period] = np.sum(minus_dm[1:period+1])

    # Wilder's smoothing
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

    # Calculate ADX (smoothed DX)
    adx[period * 2 - 1] = np.mean(dx[period:period * 2])

    for i in range(period * 2, n):
        adx[i] = ((adx[i-1] * (period - 1)) + dx[i]) / period

    return adx, plus_di, minus_di


@jit(nopython=True, cache=True)
def supertrend_numba(high: FloatArray, low: FloatArray, close: FloatArray, period: int = 10, multiplier: float = 3.0) -> Tuple[FloatArray, FloatArray]:
    """
    Supertrend Indicator
    Trend-following indicator that provides buy/sell signals

    Returns: (supertrend, direction)
    direction: 1 = uptrend, -1 = downtrend

    Used for:
    - Trend identification
    - Stop-loss placement
    - Entry/exit signals
    """
    n = len(close)
    supertrend = np.full(n, np.nan, dtype=np.float64)
    direction = np.full(n, np.nan, dtype=np.float64)

    if n < period:
        return supertrend, direction

    # Calculate ATR
    tr = np.zeros(n)
    tr[0] = high[0] - low[0]

    for i in range(1, n):
        hl = high[i] - low[i]
        hc = abs(high[i] - close[i-1])
        lc = abs(low[i] - close[i-1])
        tr[i] = max(hl, hc, lc)

    # ATR
    atr = np.full(n, np.nan, dtype=np.float64)
    for i in range(period - 1, n):
        atr[i] = np.mean(tr[i - period + 1:i + 1])

    # Calculate basic bands
    hl_avg = (high + low) / 2.0

    # Upper and lower bands
    upper_band = hl_avg + (multiplier * atr)
    lower_band = hl_avg - (multiplier * atr)

    # Initialize
    direction[0] = 1.0
    supertrend[0] = lower_band[0]

    # Calculate supertrend
    for i in range(1, n):
        if np.isnan(atr[i]):
            continue

        # Adjust bands based on previous values
        if lower_band[i] > lower_band[i-1] or close[i-1] < lower_band[i-1]:
            final_lower = lower_band[i]
        else:
            final_lower = lower_band[i-1]

        if upper_band[i] < upper_band[i-1] or close[i-1] > upper_band[i-1]:
            final_upper = upper_band[i]
        else:
            final_upper = upper_band[i-1]

        # Determine direction
        if close[i] <= final_upper:
            supertrend[i] = final_upper
            direction[i] = -1.0
        else:
            supertrend[i] = final_lower
            direction[i] = 1.0

    return supertrend, direction


# ============================================================
# ICHIMOKU CLOUD COMPONENTS
# ============================================================

@jit(nopython=True, cache=True)
def ichimoku_numba(high: FloatArray, low: FloatArray, close: FloatArray) -> Tuple[FloatArray, FloatArray, FloatArray, FloatArray, FloatArray]:
    """
    Ichimoku Cloud (Ichimoku Kinko Hyo)
    Comprehensive indicator showing support/resistance, trend, and momentum

    Returns: (tenkan_sen, kijun_sen, senkou_span_a, senkou_span_b, chikou_span)

    Components:
    - Tenkan-sen (Conversion Line): (9-period high + 9-period low) / 2
    - Kijun-sen (Base Line): (26-period high + 26-period low) / 2
    - Senkou Span A (Leading Span A): (Tenkan-sen + Kijun-sen) / 2, shifted +26
    - Senkou Span B (Leading Span B): (52-period high + 52-period low) / 2, shifted +26
    - Chikou Span (Lagging Span): Close price shifted -26

    Signals:
    - Price above cloud: Bullish
    - Price below cloud: Bearish
    - Tenkan crosses Kijun above: Buy signal
    - Tenkan crosses Kijun below: Sell signal
    """
    n = len(close)

    tenkan_sen = np.full(n, np.nan, dtype=np.float64)
    kijun_sen = np.full(n, np.nan, dtype=np.float64)
    senkou_span_a = np.full(n, np.nan, dtype=np.float64)
    senkou_span_b = np.full(n, np.nan, dtype=np.float64)
    chikou_span = np.full(n, np.nan, dtype=np.float64)

    # Calculate Tenkan-sen (9-period)
    for i in range(8, n):
        period_high = np.max(high[i-8:i+1])
        period_low = np.min(low[i-8:i+1])
        tenkan_sen[i] = (period_high + period_low) / 2.0

    # Calculate Kijun-sen (26-period)
    for i in range(25, n):
        period_high = np.max(high[i-25:i+1])
        period_low = np.min(low[i-25:i+1])
        kijun_sen[i] = (period_high + period_low) / 2.0

    # Calculate Senkou Span A (shifted +26)
    for i in range(n):
        if not np.isnan(tenkan_sen[i]) and not np.isnan(kijun_sen[i]):
            value = (tenkan_sen[i] + kijun_sen[i]) / 2.0
            if i + 26 < n:
                senkou_span_a[i + 26] = value

    # Calculate Senkou Span B (52-period, shifted +26)
    for i in range(51, n):
        period_high = np.max(high[i-51:i+1])
        period_low = np.min(low[i-51:i+1])
        value = (period_high + period_low) / 2.0
        if i + 26 < n:
            senkou_span_b[i + 26] = value

    # Calculate Chikou Span (shifted -26)
    for i in range(26, n):
        chikou_span[i - 26] = close[i]

    return tenkan_sen, kijun_sen, senkou_span_a, senkou_span_b, chikou_span


# ============================================================
# VOLATILITY INDICATORS
# ============================================================

@jit(nopython=True, cache=True)
def keltner_channels_numba(high: FloatArray, low: FloatArray, close: FloatArray, ema_period: int = 20, atr_period: int = 10, multiplier: float = 2.0) -> Tuple[FloatArray, FloatArray, FloatArray]:
    """
    Keltner Channels
    Similar to Bollinger Bands but uses ATR instead of standard deviation

    Returns: (upper, middle, lower)

    Middle = EMA(close, ema_period)
    Upper = Middle + (multiplier × ATR)
    Lower = Middle - (multiplier × ATR)

    Used for:
    - Breakout detection
    - Overbought/oversold conditions
    - Trend strength
    """
    n = len(close)

    # Calculate EMA (middle line)
    middle = np.full(n, np.nan, dtype=np.float64)
    middle[ema_period - 1] = np.mean(close[:ema_period])

    multiplier_ema = 2.0 / (ema_period + 1.0)
    for i in range(ema_period, n):
        middle[i] = (close[i] - middle[i-1]) * multiplier_ema + middle[i-1]

    # Calculate ATR
    tr = np.zeros(n)
    tr[0] = high[0] - low[0]

    for i in range(1, n):
        hl = high[i] - low[i]
        hc = abs(high[i] - close[i-1])
        lc = abs(low[i] - close[i-1])
        tr[i] = max(hl, hc, lc)

    atr = np.full(n, np.nan, dtype=np.float64)
    for i in range(atr_period - 1, n):
        atr[i] = np.mean(tr[i - atr_period + 1:i + 1])

    # Calculate channels
    upper = middle + (multiplier * atr)
    lower = middle - (multiplier * atr)

    return upper, middle, lower


@jit(nopython=True, cache=True)
def historical_volatility_numba(close: FloatArray, period: int = 20) -> FloatArray:
    """
    Historical Volatility (Standard Deviation of Returns)
    Annualized volatility

    Higher values = More volatile
    Lower values = Less volatile

    Used for:
    - Option pricing
    - Risk assessment
    - Position sizing
    """
    n = len(close)
    result = np.full(n, np.nan, dtype=np.float64)

    if n < period + 1:
        return result

    # Calculate log returns
    log_returns = np.zeros(n - 1)
    for i in range(1, n):
        if close[i-1] > 0 and close[i] > 0:
            log_returns[i-1] = np.log(close[i] / close[i-1])

    # Calculate rolling standard deviation
    for i in range(period, n):
        returns_window = log_returns[i-period:i]
        result[i] = np.std(returns_window) * np.sqrt(252) * 100  # Annualized %

    return result


# ============================================================
# PYTHON WRAPPER FUNCTIONS
# ============================================================

def calculate_vwap(data: pd.DataFrame) -> FloatArray:
    """Calculate VWAP"""
    high = data['high'].values.astype(np.float64)
    low = data['low'].values.astype(np.float64)
    close = data['close'].values.astype(np.float64)
    volume = data['volume'].values.astype(np.float64)
    return vwap_numba(high, low, close, volume)


def calculate_mfi(data: pd.DataFrame, period: int = 14) -> FloatArray:
    """Calculate Money Flow Index"""
    high = data['high'].values.astype(np.float64)
    low = data['low'].values.astype(np.float64)
    close = data['close'].values.astype(np.float64)
    volume = data['volume'].values.astype(np.float64)
    return mfi_numba(high, low, close, volume, period)


def calculate_obv(data: pd.DataFrame) -> FloatArray:
    """Calculate On-Balance Volume"""
    close = data['close'].values.astype(np.float64)
    volume = data['volume'].values.astype(np.float64)
    return obv_numba(close, volume)


def calculate_adx(data: pd.DataFrame, period: int = 14) -> Tuple[FloatArray, FloatArray, FloatArray]:
    """Calculate ADX, +DI, -DI"""
    high = data['high'].values.astype(np.float64)
    low = data['low'].values.astype(np.float64)
    close = data['close'].values.astype(np.float64)
    return adx_numba(high, low, close, period)


def calculate_supertrend(data: pd.DataFrame, period: int = 10, multiplier: float = 3.0) -> Tuple[FloatArray, FloatArray]:
    """Calculate Supertrend"""
    high = data['high'].values.astype(np.float64)
    low = data['low'].values.astype(np.float64)
    close = data['close'].values.astype(np.float64)
    return supertrend_numba(high, low, close, period, multiplier)


def calculate_ichimoku(data: pd.DataFrame) -> Tuple[FloatArray, FloatArray, FloatArray, FloatArray, FloatArray]:
    """Calculate Ichimoku Cloud"""
    high = data['high'].values.astype(np.float64)
    low = data['low'].values.astype(np.float64)
    close = data['close'].values.astype(np.float64)
    return ichimoku_numba(high, low, close)


def calculate_keltner_channels(data: pd.DataFrame, ema_period: int = 20, atr_period: int = 10, multiplier: float = 2.0) -> Tuple[FloatArray, FloatArray, FloatArray]:
    """Calculate Keltner Channels"""
    high = data['high'].values.astype(np.float64)
    low = data['low'].values.astype(np.float64)
    close = data['close'].values.astype(np.float64)
    return keltner_channels_numba(high, low, close, ema_period, atr_period, multiplier)


def calculate_historical_volatility(data: pd.DataFrame, period: int = 20) -> FloatArray:
    """Calculate Historical Volatility"""
    close = data['close'].values.astype(np.float64)
    return historical_volatility_numba(close, period)
