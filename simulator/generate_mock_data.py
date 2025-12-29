#!/usr/bin/env python3
"""
Generate realistic mock market data for local testing without API keys.
Creates 1 year of synthetic OHLCV data for specified symbols.
"""

import sqlite3
import random
import math
from datetime import datetime, timedelta
from pathlib import Path


def generate_price_series(start_price: float, num_days: int, volatility: float = 0.02, trend: float = 0.0001):
    """Generate realistic price series using geometric Brownian motion"""
    prices = [start_price]
    for _ in range(num_days - 1):
        daily_return = random.gauss(trend, volatility)
        new_price = prices[-1] * (1 + daily_return)
        prices.append(max(new_price, 0.01))  # Ensure positive
    return prices


def generate_ohlcv_from_close(closes: list, base_volume: int = 10_000_000):
    """Generate OHLCV data from close prices"""
    data = []
    for i, close in enumerate(closes):
        # Generate realistic open, high, low
        daily_range = close * random.uniform(0.01, 0.03)
        open_price = close + random.uniform(-daily_range/2, daily_range/2)

        high = max(open_price, close) + random.uniform(0, daily_range/2)
        low = min(open_price, close) - random.uniform(0, daily_range/2)

        # Volume with some randomness
        volume = int(base_volume * random.uniform(0.5, 2.0))
        trade_count = int(volume / random.uniform(100, 500))

        data.append({
            'open': round(open_price, 2),
            'high': round(high, 2),
            'low': round(low, 2),
            'close': round(close, 2),
            'volume': volume,
            'trade_count': trade_count
        })
    return data


def create_mock_database(db_path: Path, symbols: list, days: int = 365):
    """Create SQLite database with mock market data"""

    print(f"Creating mock data database: {db_path}")
    print(f"Symbols: {len(symbols)}")
    print(f"Days: {days}")

    # Create database
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # Create table matching data_manager.py schema (stock_bars, not stock_data)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS stock_bars (
            symbol TEXT,
            timestamp INTEGER,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume INTEGER,
            trade_count INTEGER,
            vwap REAL,
            PRIMARY KEY (symbol, timestamp)
        )
    ''')

    # Create symbol_metadata table - REQUIRED by data_manager.get_data_range()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS symbol_metadata (
            symbol TEXT PRIMARY KEY,
            earliest_timestamp INTEGER,
            latest_timestamp INTEGER,
            bar_count INTEGER,
            last_updated INTEGER
        )
    ''')

    # Generate dates (trading days only - exclude weekends)
    # End date is today, work backwards to ensure coverage
    end_date = datetime.now()
    dates = []
    current_date = end_date
    while len(dates) < days:
        if current_date.weekday() < 5:  # Monday = 0, Friday = 4
            dates.insert(0, current_date)  # Insert at beginning to keep chronological order
        current_date -= timedelta(days=1)

    # Stock profiles (starting price, volatility, trend)
    stock_profiles = {
        'AAPL': (175, 0.018, 0.0002),
        'MSFT': (380, 0.016, 0.0002),
        'GOOGL': (140, 0.020, 0.0001),
        'AMZN': (170, 0.022, 0.0001),
        'NVDA': (480, 0.035, 0.0005),
        'TSLA': (250, 0.045, 0.0000),
        'META': (350, 0.028, 0.0003),
        'JPM': (180, 0.015, 0.0001),
        'V': (270, 0.014, 0.0001),
        'JNJ': (160, 0.010, 0.0001),
        'WMT': (165, 0.012, 0.0001),
        'PG': (155, 0.010, 0.0001),
        'UNH': (520, 0.016, 0.0002),
        'HD': (340, 0.018, 0.0001),
        'MA': (420, 0.015, 0.0001),
        'DIS': (95, 0.022, -0.0001),
        'NFLX': (450, 0.030, 0.0002),
        'ADBE': (530, 0.024, 0.0001),
        'CRM': (260, 0.025, 0.0001),
        'AMD': (140, 0.038, 0.0003),
        'INTC': (45, 0.028, -0.0001),
        'SPY': (470, 0.012, 0.0001),  # S&P 500 ETF for benchmark
    }

    # Default profile for unknown symbols
    default_profile = (100, 0.025, 0.0001)

    total_rows = 0

    for symbol in symbols:
        profile = stock_profiles.get(symbol, default_profile)
        start_price, volatility, trend = profile

        # Generate price series
        closes = generate_price_series(start_price, days, volatility, trend)
        ohlcv_data = generate_ohlcv_from_close(closes)

        # Insert into database
        for i, (date, bar) in enumerate(zip(dates, ohlcv_data)):
            # Convert to Unix timestamp (integer) as expected by data_manager
            timestamp = int(date.timestamp())
            # Calculate VWAP as average of (open + high + low + close) / 4
            vwap = round((bar['open'] + bar['high'] + bar['low'] + bar['close']) / 4, 2)
            cursor.execute('''
                INSERT OR REPLACE INTO stock_bars
                (symbol, timestamp, open, high, low, close, volume, trade_count, vwap)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (symbol, timestamp, bar['open'], bar['high'], bar['low'],
                  bar['close'], bar['volume'], bar['trade_count'], vwap))

        # Add symbol metadata - REQUIRED for data_manager.get_data_range()
        min_ts = int(dates[0].timestamp())
        max_ts = int(dates[-1].timestamp())
        cursor.execute('''
            INSERT OR REPLACE INTO symbol_metadata
            (symbol, earliest_timestamp, latest_timestamp, bar_count, last_updated)
            VALUES (?, ?, ?, ?, ?)
        ''', (symbol, min_ts, max_ts, days, int(datetime.now().timestamp())))

        total_rows += days
        print(f"  Generated {days} bars for {symbol}")

    conn.commit()

    # Create index for faster queries
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_symbol ON stock_bars(symbol)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON stock_bars(timestamp)')

    conn.commit()
    conn.close()

    print(f"\n✅ Created {total_rows:,} total rows")
    print(f"   Database size: {db_path.stat().st_size / 1024 / 1024:.1f} MB")


def create_universe_database(db_path: Path, symbols: list, universe_name: str = 'test'):
    """Create universe database with symbols - matches stock_universe.py schema EXACTLY"""
    import json

    print(f"\nCreating universe database: {db_path}")

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # Create tables matching stock_universe.py schema EXACTLY
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS universe_constituents (
            symbol TEXT NOT NULL,
            universe_name TEXT NOT NULL,
            date_added DATE NOT NULL,
            date_removed DATE,
            last_verified DATE,
            is_tradable_alpaca BOOLEAN,
            PRIMARY KEY (symbol, universe_name, date_added)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS daily_snapshots (
            date DATE NOT NULL,
            universe_name TEXT NOT NULL,
            tickers_json TEXT NOT NULL,
            ticker_count INTEGER NOT NULL,
            PRIMARY KEY (date, universe_name)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS change_log (
            timestamp INTEGER NOT NULL,
            date DATE NOT NULL,
            universe_name TEXT NOT NULL,
            symbol TEXT NOT NULL,
            action TEXT NOT NULL,
            reason TEXT,
            PRIMARY KEY (timestamp, symbol, universe_name, action)
        )
    ''')

    # Create indexes matching stock_universe.py
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_constituents_symbol ON universe_constituents(symbol)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_constituents_universe_date ON universe_constituents(universe_name, date_removed)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_snapshots_date ON daily_snapshots(date, universe_name)')

    # Insert symbols
    today = datetime.now().strftime('%Y-%m-%d')
    for symbol in symbols:
        cursor.execute('''
            INSERT OR REPLACE INTO universe_constituents
            (symbol, universe_name, date_added, date_removed, last_verified, is_tradable_alpaca)
            VALUES (?, ?, ?, NULL, ?, 1)
        ''', (symbol, universe_name, today, today))

    # Add daily snapshot with tickers_json (required for get_approved_tickers)
    tickers_json = json.dumps(sorted(symbols))
    cursor.execute('''
        INSERT OR REPLACE INTO daily_snapshots
        (date, universe_name, tickers_json, ticker_count)
        VALUES (?, ?, ?, ?)
    ''', (today, universe_name, tickers_json, len(symbols)))

    conn.commit()
    conn.close()

    print(f"✅ Added {len(symbols)} symbols to '{universe_name}' universe")


def main():
    """Generate mock data for testing"""
    import argparse

    parser = argparse.ArgumentParser(description='Generate mock market data for testing')
    parser.add_argument('--symbols', '-s', type=str, default='AAPL,MSFT,GOOGL,AMZN,NVDA,TSLA,META,JPM,V,JNJ',
                       help='Comma-separated list of symbols')
    parser.add_argument('--days', '-d', type=int, default=365,
                       help='Number of trading days to generate (default: 365)')
    parser.add_argument('--universe', '-u', type=str, default='test',
                       help='Universe name (default: test)')
    parser.add_argument('--sp500', action='store_true',
                       help='Generate data for 20 major SP500 stocks')

    args = parser.parse_args()

    # Determine symbols
    if args.sp500:
        symbols = [
            'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'TSLA', 'META', 'JPM', 'V', 'JNJ',
            'WMT', 'PG', 'UNH', 'HD', 'MA', 'DIS', 'NFLX', 'ADBE', 'CRM', 'AMD', 'SPY'
        ]
        universe_name = 'sp500'
    else:
        symbols = [s.strip().upper() for s in args.symbols.split(',')]
        universe_name = args.universe

    # Paths
    base_dir = Path(__file__).parent
    offline_dir = base_dir / 'offline_data'
    universe_dir = base_dir / 'universes'

    offline_dir.mkdir(exist_ok=True)
    universe_dir.mkdir(exist_ok=True)

    stock_db = offline_dir / 'stock_data.db'
    universe_db = universe_dir / 'stock_universe.db'

    print("=" * 60)
    print("BearishVanish Mock Data Generator")
    print("=" * 60)
    print()

    # Generate stock data
    create_mock_database(stock_db, symbols, args.days)

    # Generate universe
    create_universe_database(universe_db, symbols, universe_name)

    print()
    print("=" * 60)
    print("✅ Mock data generation complete!")
    print("=" * 60)
    print()
    print("You can now run the simulator with:")
    print(f"  python3 main.py --offline {universe_name}")
    print()
    print("Or with specific tickers:")
    print(f"  python3 main.py --offline --tickers {','.join(symbols[:3])}")
    print()


if __name__ == '__main__':
    main()
