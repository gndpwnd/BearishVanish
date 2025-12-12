"""
Robust Data Manager with Comprehensive Error Handling
Gracefully handles API failures, missing data, and network issues
"""

import os
import pandas as pd
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
import time

OFFLINE_DATA_DIR = Path('./offline_data')
DB_PATH = OFFLINE_DATA_DIR / 'stock_data.db'

class DataManager:
    def __init__(self, api_key, secret_key, offline_mode=False, quiet=True):
        """
        Initialize DataManager with robust error handling
        
        Args:
            api_key: Alpaca API key
            secret_key: Alpaca secret key
            offline_mode: If True, only use cached data
            quiet: If True, suppress success messages (only show errors)
        """
        self.data_client = StockHistoricalDataClient(api_key, secret_key)
        self.offline_mode = offline_mode
        self.quiet = quiet
        self.offline_data_dir = OFFLINE_DATA_DIR
        self.offline_data_dir.mkdir(exist_ok=True)
        self.db_path = DB_PATH
        self._init_database()
        
        # Error tracking
        self.api_errors = []
        self.failed_symbols = set()
        self.retry_count = 3  # Number of retries for failed requests
        self.retry_delay = 2  # Seconds between retries
        
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
        """Load cached data for a symbol from SQLite - SILENT"""
        try:
            conn = sqlite3.connect(self.db_path)
            
            query = 'SELECT timestamp, open, high, low, close, volume, trade_count, vwap FROM stock_bars WHERE symbol = ?'
            params = [symbol.upper()]
            
            if start_date and end_date:
                start_ts = int(start_date.timestamp())
                end_ts = int(end_date.timestamp())
                query += ' AND timestamp >= ? AND timestamp <= ?'
                params.extend([start_ts, end_ts])
            
            query += ' ORDER BY timestamp'
            
            df = pd.read_sql_query(query, conn, params=params)
            conn.close()
            
            if df.empty:
                return None
            
            # Convert timestamp back to datetime index
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
            df.set_index('timestamp', inplace=True)
            
            return df
            
        except Exception as e:
            print(f"❌ Database error loading {symbol}: {e}")
            if 'conn' in locals():
                conn.close()
            return None

    def save_offline_data(self, symbol, df):
        """Save data to SQLite database - SILENT with error handling"""
        try:
            symbol = symbol.upper()
            conn = sqlite3.connect(self.db_path)
            
            # Prepare dataframe for insertion
            df_to_save = df.copy()
            df_to_save['symbol'] = symbol
            df_to_save['timestamp'] = df_to_save.index.astype('int64') // 10**9
            
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
            
            return True
            
        except sqlite3.IntegrityError:
            # Handle duplicate keys by updating existing records
            try:
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
                
                return True
            except Exception as e:
                print(f"❌ Error saving {symbol} (retry): {e}")
                if 'conn' in locals():
                    conn.close()
                return False
            
        except Exception as e:
            print(f"❌ Error saving {symbol}: {e}")
            if 'conn' in locals():
                conn.close()
            return False

    def fetch_from_api(self, symbol, start_date, end_date, retry_count=None):
        """
        Fetch data from Alpaca API with robust error handling and retries
        
        Args:
            symbol: Stock symbol
            start_date: Start date
            end_date: End date
            retry_count: Number of retries (uses self.retry_count if None)
        
        Returns:
            DataFrame or None if all retries fail
        """
        if retry_count is None:
            retry_count = self.retry_count
        
        symbol = symbol.upper()
        
        # Ensure timezone-naive dates for API
        if isinstance(start_date, pd.Timestamp) and start_date.tz is not None:
            start_date = start_date.tz_localize(None)
        if isinstance(end_date, pd.Timestamp) and end_date.tz is not None:
            end_date = end_date.tz_localize(None)
        
        for attempt in range(retry_count):
            try:
                request_params = StockBarsRequest(
                    symbol_or_symbols=symbol,
                    timeframe=TimeFrame.Hour,
                    start=start_date,
                    end=end_date
                )
                
                bars = self.data_client.get_stock_bars(request_params)
                df = bars.df
                
                if df.empty:
                    if attempt < retry_count - 1:
                        # Retry with shorter date range
                        days_diff = (end_date - start_date).days
                        if days_diff > 30:
                            # Try with smaller chunks
                            end_date = start_date + timedelta(days=30)
                            time.sleep(self.retry_delay)
                            continue
                    raise ValueError(f"No data returned from API for {symbol}")
                
                if isinstance(df.index, pd.MultiIndex):
                    df = df.xs(symbol, level=0)
                
                # Convert to timezone-naive
                df.index = pd.to_datetime(df.index)
                if df.index.tz is not None:
                    df.index = df.index.tz_localize(None)
                
                return df
                
            except Exception as e:
                error_msg = f"API error for {symbol} (attempt {attempt + 1}/{retry_count}): {str(e)}"
                
                if attempt < retry_count - 1:
                    # Log but continue to next retry
                    if not self.quiet:
                        print(f"⚠️  {error_msg}, retrying...")
                    time.sleep(self.retry_delay * (attempt + 1))  # Exponential backoff
                else:
                    # Final attempt failed
                    print(f"❌ {error_msg}")
                    self.api_errors.append({
                        'symbol': symbol,
                        'error': str(e),
                        'timestamp': datetime.now()
                    })
                    self.failed_symbols.add(symbol)
                    return None
        
        return None
    
    def get_data_range(self, symbol):
        """Get the date range of cached data for a symbol"""
        try:
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
        except Exception as e:
            print(f"❌ Error getting data range for {symbol}: {e}")
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
        Main method to get stock data - SILENT MODE with robust error handling
        
        Returns:
            DataFrame if successful
            None if data unavailable (graceful failure)
        """
        try:
            symbol = symbol.upper()
            end_date = datetime.now().replace(tzinfo=None)
            start_date = (end_date - timedelta(days=days)).replace(tzinfo=None)
            
            # Check if we have complete data using metadata (very fast)
            data_range = self.get_data_range(symbol)
            
            if data_range:
                # Use a 3-day buffer to account for weekends/holidays
                buffer = timedelta(days=3)
                coverage_start = data_range['start'] - buffer
                coverage_end = data_range['end'] + buffer
                
                if coverage_start <= start_date and coverage_end >= end_date:
                    return self.load_offline_data(symbol, start_date, end_date)
            
            # Find gaps that need to be filled
            gaps = self.find_gaps(symbol, start_date, end_date)
            
            if not gaps:
                return self.load_offline_data(symbol, start_date, end_date)
            
            # In offline mode, return None instead of raising
            if self.offline_mode:
                print(f"⚠️  {symbol}: Missing data in offline mode")
                return None
            
            # Download missing gaps
            if not self.quiet:
                print(f"📥 {symbol}: Downloading {len(gaps)} gap(s)...")
            
            for gap_start, gap_end in gaps:
                # Skip tiny gaps
                if (gap_end - gap_start).total_seconds() < 7200:
                    continue
                    
                gap_data = self.fetch_from_api(symbol, gap_start, gap_end)
                if gap_data is not None:
                    self.save_offline_data(symbol, gap_data)
                else:
                    # API failed but we can still try to use partial data
                    print(f"⚠️  {symbol}: Partial data available")
            
            # Load and return the complete data (or whatever we have)
            return self.load_offline_data(symbol, start_date, end_date)
            
        except Exception as e:
            print(f"❌ Unexpected error for {symbol}: {e}")
            return None

    def download_all_data(self, symbols, days=180):
        """
        Convenience method to download data for multiple symbols with error handling
        
        Returns:
            dict: {symbol: DataFrame or None}
        """
        print(f"\n{'='*60}")
        print(f"DOWNLOADING DATA FOR {len(symbols)} SYMBOLS")
        print(f"{'='*60}\n")
        
        results = {}
        successful = 0
        failed = 0
        
        for symbol in symbols:
            try:
                df = self.get_stock_data(symbol, days)
                if df is not None:
                    results[symbol] = df
                    successful += 1
                    if not self.quiet:
                        print(f"✅ {symbol}: {len(df)} bars")
                else:
                    results[symbol] = None
                    failed += 1
                    print(f"⚠️  {symbol}: No data available")
            except Exception as e:
                print(f"❌ {symbol}: Error - {e}")
                results[symbol] = None
                failed += 1
        
        print(f"\n{'='*60}")
        print(f"DOWNLOAD COMPLETE")
        print(f"✅ Successful: {successful}/{len(symbols)}")
        if failed > 0:
            print(f"⚠️  Failed/Unavailable: {failed}/{len(symbols)}")
        print(f"{'='*60}\n")
        
        return results
    
    def list_cached_symbols(self):
        """List all symbols with cached data"""
        try:
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
        except Exception as e:
            print(f"❌ Error listing cached symbols: {e}")
            return []
    
    def print_cache_status(self):
        """Print status of offline cache"""
        try:
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
                for item in cached[:20]:  # Show first 20
                    print(f"{item['symbol']:<10} {item['bars']:<10} {item['date_range']}")
                
                if len(cached) > 20:
                    print(f"... and {len(cached) - 20} more")
            else:
                print("No cached data found.")
            
            print()
        except Exception as e:
            print(f"❌ Error printing cache status: {e}")
    
    def vacuum_database(self):
        """Optimize database (reclaim space and improve performance)"""
        try:
            print("Optimizing database...")
            conn = sqlite3.connect(self.db_path)
            conn.execute('VACUUM')
            conn.execute('ANALYZE')
            conn.close()
            print("✅ Database optimized")
        except Exception as e:
            print(f"❌ Error optimizing database: {e}")
    
    def get_error_summary(self):
        """Get summary of API errors"""
        if not self.api_errors:
            return "✅ No API errors"
        
        return f"⚠️  {len(self.api_errors)} API errors, {len(self.failed_symbols)} failed symbols"
    
    def print_error_summary(self):
        """Print detailed error summary"""
        if not self.api_errors:
            print("✅ No API errors during session")
            return
        
        print(f"\n{'='*60}")
        print(f"API ERROR SUMMARY")
        print(f"{'='*60}")
        print(f"Total errors: {len(self.api_errors)}")
        print(f"Failed symbols: {len(self.failed_symbols)}")
        print(f"\nRecent errors:")
        
        for error in self.api_errors[-10:]:  # Show last 10
            print(f"  {error['timestamp'].strftime('%H:%M:%S')} - {error['symbol']}: {error['error'][:50]}")
        
        print(f"\n{'='*60}\n")