"""
Data Manager for offline stock data caching with SQLite
Handles downloading, storing, and retrieving stock data with gap filling
Uses SQLite for fast access to thousands of stocks

# NOTE TO AI/DEVELOPERS:
# This file is an OLD / OUTDATED version kept for reference and style only.
# Do NOT use this file as the source of truth for logic or implementation.
# Current, active code exists in the newer versioned files.
# Only reuse formatting or stylistic patterns from here if needed.

"""

import os
import pandas as pd
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame

OFFLINE_DATA_DIR = Path('./offline_data')
DB_PATH = OFFLINE_DATA_DIR / 'stock_data.db'

class DataManager:
    def __init__(self, api_key, secret_key, offline_mode=False):
        self.data_client = StockHistoricalDataClient(api_key, secret_key)
        self.offline_mode = offline_mode
        self.offline_data_dir = OFFLINE_DATA_DIR
        self.offline_data_dir.mkdir(exist_ok=True)
        self.db_path = DB_PATH
        self._init_database()
        
    def _init_database(self):
        """Initialize SQLite database with optimized schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create table with indexed columns for fast queries
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS stock_bars (
                symbol TEXT NOT NULL,
                timestamp INTEGER NOT NULL,
                open REAL NOT NULL,
                high REAL NOT NULL,
                low REAL NOT NULL,
                close REAL NOT NULL,
                volume INTEGER NOT NULL,
                trade_count INTEGER,
                vwap REAL,
                PRIMARY KEY (symbol, timestamp)
            )
        ''')
        
        # Create indexes for fast lookups
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_symbol 
            ON stock_bars(symbol)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_symbol_timestamp 
            ON stock_bars(symbol, timestamp)
        ''')
        
        # Metadata table to track data ranges per symbol
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS symbol_metadata (
                symbol TEXT PRIMARY KEY,
                earliest_timestamp INTEGER,
                latest_timestamp INTEGER,
                bar_count INTEGER,
                last_updated INTEGER
            )
        ''')
        
        conn.commit()
        conn.close()
        
    def _update_metadata(self, symbol, conn):
        """Update metadata for a symbol"""
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT MIN(timestamp), MAX(timestamp), COUNT(*)
            FROM stock_bars
            WHERE symbol = ?
        ''', (symbol,))
        
        row = cursor.fetchone()
        if row and row[0]:
            cursor.execute('''
                INSERT OR REPLACE INTO symbol_metadata 
                (symbol, earliest_timestamp, latest_timestamp, bar_count, last_updated)
                VALUES (?, ?, ?, ?, ?)
            ''', (symbol, row[0], row[1], row[2], int(datetime.now().timestamp())))
            
    def load_offline_data(self, symbol, start_date=None, end_date=None):
        """Load cached data for a symbol from SQLite"""
        conn = sqlite3.connect(self.db_path)
        
        query = 'SELECT timestamp, open, high, low, close, volume, trade_count, vwap FROM stock_bars WHERE symbol = ?'
        params = [symbol.upper()]
        
        if start_date and end_date:
            start_ts = int(start_date.timestamp())
            end_ts = int(end_date.timestamp())
            query += ' AND timestamp >= ? AND timestamp <= ?'
            params.extend([start_ts, end_ts])
        
        query += ' ORDER BY timestamp'
        
        try:
            df = pd.read_sql_query(query, conn, params=params)
            
            if df.empty:
                conn.close()
                return None
            
            # Convert timestamp back to datetime index
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
            df.set_index('timestamp', inplace=True)
            
            print(f"Loaded offline data for {symbol}: {len(df)} bars")
            conn.close()
            return df
            
        except Exception as e:
            print(f"Error loading offline data for {symbol}: {e}")
            conn.close()
            return None
    
    def save_offline_data(self, symbol, df):
        """Save data to SQLite database"""
        try:
            symbol = symbol.upper()
            conn = sqlite3.connect(self.db_path)
            
            # Prepare dataframe for insertion
            df_to_save = df.copy()
            df_to_save['symbol'] = symbol
            df_to_save['timestamp'] = df_to_save.index.astype('int64') // 10**9  # Convert to Unix timestamp
            
            # Ensure we have all required columns
            required_cols = ['symbol', 'timestamp', 'open', 'high', 'low', 'close', 'volume']
            optional_cols = ['trade_count', 'vwap']
            
            for col in optional_cols:
                if col not in df_to_save.columns:
                    df_to_save[col] = None
            
            # Select only the columns we need
            cols_to_save = required_cols + optional_cols
            df_to_save = df_to_save[cols_to_save]
            
            # Use INSERT OR REPLACE to handle duplicates
            df_to_save.to_sql('stock_bars', conn, if_exists='append', index=False, method='multi')
            
            # Update metadata
            self._update_metadata(symbol, conn)
            
            conn.commit()
            conn.close()
            
            print(f"Saved offline data for {symbol}: {len(df)} bars")
            return True
            
        except sqlite3.IntegrityError:
            # Handle duplicate keys by updating existing records
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            for idx, row in df.iterrows():
                timestamp = int(idx.timestamp())
                cursor.execute('''
                    INSERT OR REPLACE INTO stock_bars 
                    (symbol, timestamp, open, high, low, close, volume, trade_count, vwap)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    symbol.upper(),
                    timestamp,
                    row['open'],
                    row['high'],
                    row['low'],
                    row['close'],
                    row['volume'],
                    row.get('trade_count'),
                    row.get('vwap')
                ))
            
            self._update_metadata(symbol, conn)
            conn.commit()
            conn.close()
            
            print(f"Updated offline data for {symbol}: {len(df)} bars")
            return True
            
        except Exception as e:
            print(f"Error saving offline data for {symbol}: {e}")
            return False
    
    def fetch_from_api(self, symbol, start_date, end_date):
        """Fetch data from Alpaca API"""
        symbol = symbol.upper()
        
        # Ensure timezone-naive dates for API
        if isinstance(start_date, pd.Timestamp) and start_date.tz is not None:
            start_date = start_date.tz_localize(None)
        if isinstance(end_date, pd.Timestamp) and end_date.tz is not None:
            end_date = end_date.tz_localize(None)
        
        request_params = StockBarsRequest(
            symbol_or_symbols=symbol,
            timeframe=TimeFrame.Hour,
            start=start_date,
            end=end_date
        )
        
        bars = self.data_client.get_stock_bars(request_params)
        df = bars.df
        
        if df.empty:
            raise ValueError(f"No data returned from API for {symbol}")
        
        if isinstance(df.index, pd.MultiIndex):
            df = df.xs(symbol, level=0)
        
        # Convert to timezone-naive
        df.index = pd.to_datetime(df.index)
        if df.index.tz is not None:
            df.index = df.index.tz_localize(None)
        
        return df
    
    def get_data_range(self, symbol):
        """Get the date range of cached data for a symbol"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT earliest_timestamp, latest_timestamp, bar_count
            FROM symbol_metadata
            WHERE symbol = ?
        ''', (symbol.upper(),))
        
        row = cursor.fetchone()
        conn.close()
        
        if row and row[0]:
            return {
                'start': datetime.fromtimestamp(row[0]),
                'end': datetime.fromtimestamp(row[1]),
                'count': row[2]
            }
        return None
    
    def find_gaps(self, symbol, start_date, end_date):
        """Identify gaps in the data using metadata (very fast)"""
        # Ensure timezone-naive dates
        if isinstance(start_date, pd.Timestamp) and start_date.tz is not None:
            start_date = start_date.tz_localize(None)
        if isinstance(end_date, pd.Timestamp) and end_date.tz is not None:
            end_date = end_date.tz_localize(None)
        
        data_range = self.get_data_range(symbol)
        
        if not data_range:
            return [(start_date, end_date)]
        
        gaps = []
        df_start = data_range['start']
        df_end = data_range['end']
        
        # Gap before existing data (only if significant - more than 1 day)
        if start_date < df_start - timedelta(days=1):
            gap_end = df_start - timedelta(hours=1)
            if gap_end > start_date:
                gaps.append((start_date, gap_end))
        
        # Gap after existing data (only if significant - more than 1 day)
        if end_date > df_end + timedelta(days=1):
            gap_start = df_end + timedelta(hours=1)
            if end_date > gap_start:
                gaps.append((gap_start, end_date))
        
        return gaps
    
    def get_stock_data(self, symbol, days=180):
        """
        Main method to get stock data
        - Checks SQLite cache first
        - Identifies gaps using metadata (fast)
        - Fills gaps from API if not in offline mode
        - Saves new data to cache
        """
        symbol = symbol.upper()
        end_date = datetime.now().replace(tzinfo=None)
        start_date = (end_date - timedelta(days=days)).replace(tzinfo=None)
        
        print(f"\n{'='*60}")
        print(f"Fetching data for {symbol} ({days} days)")
        print(f"Date range: {start_date.date()} to {end_date.date()}")
        print(f"{'='*60}")
        
        # Check if we have complete data using metadata (very fast)
        data_range = self.get_data_range(symbol)
        
        if data_range:
            # Use a 3-day buffer to account for weekends/holidays
            buffer = timedelta(days=3)
            coverage_start = data_range['start'] - buffer
            coverage_end = data_range['end'] + buffer
            
            if coverage_start <= start_date and coverage_end >= end_date:
                print(f"✓ Using complete offline data for {symbol}")
                return self.load_offline_data(symbol, start_date, end_date)
        
        # Find gaps that need to be filled
        gaps = self.find_gaps(symbol, start_date, end_date)
        
        if not gaps:
            print(f"✓ No gaps found for {symbol}")
            return self.load_offline_data(symbol, start_date, end_date)
        
        # In offline mode, raise error if gaps exist
        if self.offline_mode:
            raise ValueError(
                f"OFFLINE MODE: Missing data for {symbol}. "
                f"Run without --offline flag to download missing data.\n"
                f"Gaps: {[(g[0].date(), g[1].date()) for g in gaps]}"
            )
        
        # Fill gaps from API
        print(f"⚠ Found {len(gaps)} gap(s) in offline data")
        
        for gap_start, gap_end in gaps:
            # Skip if gap is less than 2 hours
            if (gap_end - gap_start).total_seconds() < 7200:
                print(f"  ⓘ Skipping tiny gap: {gap_start.date()} to {gap_end.date()}")
                continue
                
            print(f"  Downloading gap: {gap_start.date()} to {gap_end.date()}")
            try:
                gap_data = self.fetch_from_api(symbol, gap_start, gap_end)
                self.save_offline_data(symbol, gap_data)
                print(f"  ✓ Downloaded {len(gap_data)} bars")
            except Exception as e:
                print(f"  ✗ Error downloading gap: {e}")
        
        # Load and return the complete data
        return self.load_offline_data(symbol, start_date, end_date)
    
    def download_all_data(self, symbols, days=180):
        """
        Convenience method to download data for multiple symbols
        Useful for pre-downloading before going offline
        """
        print(f"\n{'='*60}")
        print(f"DOWNLOADING DATA FOR {len(symbols)} SYMBOLS")
        print(f"{'='*60}\n")
        
        results = {}
        for symbol in symbols:
            try:
                df = self.get_stock_data(symbol, days)
                results[symbol] = df
                print(f"✓ {symbol}: {len(df)} bars downloaded")
            except Exception as e:
                print(f"✗ {symbol}: Error - {e}")
                results[symbol] = None
        
        print(f"\n{'='*60}")
        print(f"DOWNLOAD COMPLETE")
        print(f"Successful: {sum(1 for v in results.values() if v is not None)}/{len(symbols)}")
        print(f"{'='*60}\n")
        
        return results
    
    def list_cached_symbols(self):
        """List all symbols with cached data"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT symbol, earliest_timestamp, latest_timestamp, bar_count
            FROM symbol_metadata
            ORDER BY symbol
        ''')
        
        cached = []
        for row in cursor.fetchall():
            start_date = datetime.fromtimestamp(row[1]).date()
            end_date = datetime.fromtimestamp(row[2]).date()
            cached.append({
                'symbol': row[0],
                'bars': row[3],
                'date_range': f"{start_date} to {end_date}"
            })
        
        conn.close()
        return cached
    
    def print_cache_status(self):
        """Print status of offline cache"""
        cached = self.list_cached_symbols()
        
        # Get database size
        db_size_mb = self.db_path.stat().st_size / (1024 * 1024) if self.db_path.exists() else 0
        
        print(f"\n{'='*60}")
        print(f"OFFLINE CACHE STATUS (SQLite)")
        print(f"{'='*60}")
        print(f"Location: {self.db_path.absolute()}")
        print(f"Database size: {db_size_mb:.2f} MB")
        print(f"Total symbols: {len(cached)}")
        print(f"{'='*60}\n")
        
        if cached:
            print(f"{'Symbol':<10} {'Bars':<10} {'Date Range'}")
            print(f"{'-'*60}")
            for item in cached:
                print(f"{item['symbol']:<10} {item['bars']:<10} {item['date_range']}")
        else:
            print("No cached data found.")
        
        print()
    
    def vacuum_database(self):
        """Optimize database (reclaim space and improve performance)"""
        print("Optimizing database...")
        conn = sqlite3.connect(self.db_path)
        conn.execute('VACUUM')
        conn.execute('ANALYZE')
        conn.close()
        print("✓ Database optimized")