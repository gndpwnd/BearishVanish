"""
Debug Script: Investigate why Breakout, Trend Following, 500 Intersection, and SP500 Slope v2
have 0 trades.

This script loads actual data directly from SQLite and checks indicator values.
"""

import pandas as pd
import numpy as np
import sys
import sqlite3
from pathlib import Path
from datetime import datetime

# Add simulator to path
sys.path.insert(0, str(Path(__file__).parent))

from indicator_base import (
    calculate_ema, calculate_atr, calculate_relative_volume
)
from indicator_advanced import calculate_adx, calculate_supertrend

DB_PATH = Path(__file__).parent / 'offline_data' / 'stock_data.db'


def get_symbols():
    """Get all available symbols"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('SELECT DISTINCT symbol FROM stock_bars')
    symbols = [r[0] for r in cur.fetchall()]
    conn.close()
    return symbols


def get_data_for_symbol(symbol):
    """Load data for a symbol from SQLite"""
    conn = sqlite3.connect(DB_PATH)

    query = f"""
    SELECT timestamp, open, high, low, close, volume
    FROM stock_bars
    WHERE symbol = ?
    ORDER BY timestamp
    """

    df = pd.read_sql_query(query, conn, params=(symbol,))
    conn.close()

    if len(df) == 0:
        return None

    # Convert timestamp to datetime index
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
    df.set_index('timestamp', inplace=True)

    return df


def analyze_indicator_distributions():
    """Analyze the distribution of key indicators across all symbols"""

    print("=" * 60)
    print("DIAGNOSTIC: Zero-Trade Strategy Investigation")
    print("=" * 60)

    symbols = get_symbols()
    print(f"\nFound {len(symbols)} symbols: {symbols}")

    # Collect statistics across all symbols
    adx_values = []
    ema_aligned_count = 0
    breakout_count = 0
    total_bars = 0

    for symbol in symbols:
        data = get_data_for_symbol(symbol)
        if data is None or len(data) < 50:
            continue

        total_bars += len(data)
        print(f"\n--- {symbol}: {len(data)} bars ---")
        print(f"  Date range: {data.index[0]} to {data.index[-1]}")

        # Calculate ADX
        try:
            adx, plus_di, minus_di = calculate_adx(data, period=14)
            valid_adx = adx[~np.isnan(adx)]
            if len(valid_adx) > 0:
                adx_values.extend(valid_adx.tolist())
                print(f"  ADX: min={valid_adx.min():.1f}, max={valid_adx.max():.1f}, mean={valid_adx.mean():.1f}")
                print(f"  ADX >= 20: {(valid_adx >= 20).sum()} / {len(valid_adx)} ({(valid_adx >= 20).mean()*100:.1f}%)")
        except Exception as e:
            print(f"  Error calculating ADX: {e}")
            continue

        # Calculate EMAs
        try:
            ema_20 = calculate_ema(data, period=20)
            ema_50 = calculate_ema(data, period=50)

            aligned = 0
            for i in range(50, len(data)):
                if not np.isnan(ema_20[i]) and not np.isnan(ema_50[i]):
                    if ema_20[i] > ema_50[i]:
                        aligned += 1
            ema_aligned_count += aligned
            print(f"  EMA20 > EMA50: {aligned} bars ({aligned/(len(data)-50)*100:.1f}%)")
        except Exception as e:
            print(f"  Error calculating EMAs: {e}")

        # Check for 20-day high breakouts
        try:
            breakouts = 0
            for i in range(20, len(data)):
                high_20d = data['high'].iloc[i-20:i].max()
                current_high = data['high'].iloc[i]
                prev_high = data['high'].iloc[i-1]
                if current_high > high_20d and prev_high <= high_20d:
                    breakouts += 1
            breakout_count += breakouts
            print(f"  New 20-day breakouts: {breakouts}")
        except Exception as e:
            print(f"  Error checking breakouts: {e}")

    # Report aggregate findings
    print("\n" + "=" * 60)
    print("AGGREGATE INDICATOR STATISTICS")
    print("=" * 60)

    if adx_values:
        adx_array = np.array(adx_values)
        print(f"\nADX Statistics ({len(adx_values)} data points from {len(symbols)} symbols):")
        print(f"  Min:     {adx_array.min():.2f}")
        print(f"  Max:     {adx_array.max():.2f}")
        print(f"  Mean:    {adx_array.mean():.2f}")
        print(f"  Median:  {np.median(adx_array):.2f}")

        print(f"\n  ADX Distribution:")
        print(f"    ADX < 15:  {(adx_array < 15).sum()} ({(adx_array < 15).mean()*100:.1f}%)")
        print(f"    ADX < 20:  {(adx_array < 20).sum()} ({(adx_array < 20).mean()*100:.1f}%)")
        print(f"    ADX >= 20: {(adx_array >= 20).sum()} ({(adx_array >= 20).mean()*100:.1f}%)")
        print(f"    ADX >= 25: {(adx_array >= 25).sum()} ({(adx_array >= 25).mean()*100:.1f}%)")

    print(f"\nEMA Alignment (EMA20 > EMA50):")
    print(f"  Total aligned bars: {ema_aligned_count} / {total_bars}")

    print(f"\n20-Day High Breakouts:")
    print(f"  Total new breakouts: {breakout_count}")

    return adx_values


def analyze_strategy_conditions_detailed():
    """Check specific strategy entry conditions bar by bar"""

    print("\n" + "=" * 60)
    print("DETAILED STRATEGY CONDITION ANALYSIS")
    print("=" * 60)

    symbols = get_symbols()

    # Track when ALL conditions are met simultaneously
    trend_following_matches = []
    breakout_matches = []

    for symbol in symbols:
        data = get_data_for_symbol(symbol)
        if data is None or len(data) < 60:
            continue

        # Calculate indicators
        try:
            adx, plus_di, minus_di = calculate_adx(data, period=14)
            ema_20 = calculate_ema(data, period=20)
            ema_50 = calculate_ema(data, period=50)
            rel_vol = calculate_relative_volume(data, period=20)
            supertrend, supertrend_dir = calculate_supertrend(data, period=10, multiplier=3.0)
        except Exception as e:
            print(f"Error calculating indicators for {symbol}: {e}")
            continue

        for i in range(50, len(data)):
            current_price = data['close'].iloc[i]
            current_high = data['high'].iloc[i]
            current_adx = adx[i] if not np.isnan(adx[i]) else 0
            current_ema_20 = ema_20[i] if not np.isnan(ema_20[i]) else 0
            current_ema_50 = ema_50[i] if not np.isnan(ema_50[i]) else 0
            current_rel_vol = rel_vol[i] if not np.isnan(rel_vol[i]) else 1.0
            current_supertrend_dir = supertrend_dir[i] if not np.isnan(supertrend_dir[i]) else 0

            # TREND FOLLOWING: Check all conditions
            adx_ok = current_adx > 20
            emas_ok = current_ema_20 > current_ema_50
            price_ok = current_price > current_ema_20
            supertrend_ok = current_supertrend_dir > 0

            if adx_ok and emas_ok and price_ok:
                trend_following_matches.append({
                    'symbol': symbol,
                    'date': data.index[i],
                    'adx': current_adx,
                    'ema_20': current_ema_20,
                    'ema_50': current_ema_50,
                    'price': current_price,
                    'supertrend_dir': current_supertrend_dir
                })

            # BREAKOUT: Check conditions
            if i >= 20:
                high_20d = data['high'].iloc[i-20:i].max()
                prev_high = data['high'].iloc[i-1]
                is_breakout = current_high > high_20d
                is_new = prev_high <= high_20d
                vol_ok = current_rel_vol > 1.2

                if is_breakout and is_new and (vol_ok or adx_ok):
                    breakout_matches.append({
                        'symbol': symbol,
                        'date': data.index[i],
                        'high': current_high,
                        'high_20d': high_20d,
                        'rel_vol': current_rel_vol,
                        'adx': current_adx
                    })

    print(f"\nTREND FOLLOWING - All Conditions Met: {len(trend_following_matches)} bars")
    if trend_following_matches:
        print("  Sample matches:")
        for m in trend_following_matches[:5]:
            print(f"    {m['symbol']} @ {m['date']}: ADX={m['adx']:.1f}, Price={m['price']:.2f}, "
                  f"EMA20={m['ema_20']:.2f}, EMA50={m['ema_50']:.2f}, ST_dir={m['supertrend_dir']:.0f}")

    print(f"\nBREAKOUT - All Conditions Met: {len(breakout_matches)} bars")
    if breakout_matches:
        print("  Sample matches:")
        for m in breakout_matches[:5]:
            print(f"    {m['symbol']} @ {m['date']}: High={m['high']:.2f}, 20d_High={m['high_20d']:.2f}, "
                  f"RelVol={m['rel_vol']:.2f}, ADX={m['adx']:.1f}")

    return trend_following_matches, breakout_matches


def check_spy_relative_strength():
    """Check SPY comparison logic"""

    print("\n" + "=" * 60)
    print("SPY RELATIVE STRENGTH CHECK")
    print("=" * 60)

    spy_data = get_data_for_symbol('SPY')

    if spy_data is None:
        print("ERROR: SPY data is NOT available!")
        return False

    print(f"\nSPY data found:")
    print(f"  Date range: {spy_data.index[0]} to {spy_data.index[-1]}")
    print(f"  Total bars: {len(spy_data)}")

    # Calculate SPY cumulative returns
    spy_returns = spy_data['close'].pct_change().fillna(0)
    spy_cum = (spy_returns.cumsum() * 100).values

    print(f"  SPY cumulative return: {spy_cum[-1]:.2f}%")

    # Check alignment with each stock
    symbols = get_symbols()
    for symbol in symbols:
        if symbol == 'SPY':
            continue

        stock_data = get_data_for_symbol(symbol)
        if stock_data is None:
            continue

        # Find overlapping indices
        spy_dates = set(spy_data.index)
        stock_dates = set(stock_data.index)
        overlap = spy_dates.intersection(stock_dates)

        print(f"\n  {symbol}:")
        print(f"    Stock bars: {len(stock_data)}")
        print(f"    Overlapping dates with SPY: {len(overlap)} ({len(overlap)/len(stock_dates)*100:.1f}%)")

        # Calculate relative strength
        if len(overlap) > 50:
            stock_returns = stock_data['close'].pct_change().fillna(0)
            stock_cum = (stock_returns.cumsum() * 100).values

            # Count bars where stock is below SPY
            below_spy_count = 0
            above_spy_count = 0
            for i in range(min(len(stock_cum), len(spy_cum))):
                if stock_cum[i] < spy_cum[i]:
                    below_spy_count += 1
                else:
                    above_spy_count += 1

            print(f"    Below SPY: {below_spy_count} bars")
            print(f"    Above SPY: {above_spy_count} bars")

    return True


def main():
    """Run all diagnostic checks"""
    print("\n" + "=" * 60)
    print("PHASE 3 DIAGNOSTIC: Why 4 Strategies Have 0 Trades")
    print("=" * 60)

    # Check indicator values
    analyze_indicator_distributions()

    # Detailed strategy condition analysis
    tf_matches, bo_matches = analyze_strategy_conditions_detailed()

    # Check SPY data
    check_spy_relative_strength()

    print("\n" + "=" * 60)
    print("DIAGNOSIS & RECOMMENDATIONS")
    print("=" * 60)

    if tf_matches:
        print(f"""
TREND FOLLOWING: Found {len(tf_matches)} potential entry points!
  -> The strategy SHOULD be generating trades.
  -> Issue may be in the strategy's state tracking or position management.
  -> Recommend: Check if supertrend_direction is being passed correctly.
""")
    else:
        print("""
TREND FOLLOWING: No entry conditions met.
  -> The conditions may be too strict for this data period.
  -> Recommend: Lower ADX threshold to 15, remove supertrend requirement.
""")

    if bo_matches:
        print(f"""
BREAKOUT: Found {len(bo_matches)} potential entry points!
  -> The strategy SHOULD be generating trades.
  -> Issue may be in the strategy's state tracking or indicator access.
  -> Recommend: Debug the indicator column names in the strategy.
""")
    else:
        print("""
BREAKOUT: No valid breakouts with confirmation.
  -> Breakouts may be rare in this data period.
  -> Recommend: Reduce lookback to 10 days, lower volume threshold.
""")


if __name__ == "__main__":
    main()
