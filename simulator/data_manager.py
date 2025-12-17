"""
OPTIMIZED Data Manager with FAST Batch Loading - UTF-8 SAFE VERSION
Key improvements:
1. Batch loading - load all symbols in 1-2 queries instead of 500+
2. Connection pooling - reuse connections instead of creating new ones
3. Optimal worker count - 2-4 workers max for SQLite
4. UTF-8 safety for all database operations
"""

import os
import pandas as pd
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
import time
import json
import threading

# Import shared UTF-8 utilities
from utilities.utf8_helpers import ensure_utf8, get_utf8_connection, clean_ticker

OFFLINE_DATA_DIR = Path('./offline_data')
DB_PATH = OFFLINE_DATA_DIR / 'stock_data.db'
PROGRESS_FILE = OFFLINE_DATA_DIR / 'download_progress.json'

class DataManager:
    def __init__(self, api_key, secret_key, offline_mode=False, quiet=True):
        """Initialize DataManager with optimized settings"""
        self.data_client = StockHistoricalDataClient(api_key, secret_key)
        self.offline_mode = offline_mode
        self.quiet = quiet
        self.offline_data_dir = OFFLINE_DATA_DIR
        self.offline_data_dir.mkdir(exist_ok=True)
        self.db_path = DB_PATH
        self._init_database()
        
        # Connection pool for better performance
        self._connection_lock = threading.Lock()
        self._connection_pool = []
        self._max_pool_size = 5
        
        # Error tracking
        self.api_errors = []
        self.failed_symbols = set()
        self.retry_count = 3
        self.retry_delay = 2
        
        # Trickle mode settings
        self.trickle_mode = False
        self.trickle_delay = 8
        self.rate_limit_cooldown = 60
        self.rate_limit_errors = 0
        self.max_rate_limit_errors = 3
        
        # Batch download settings - OPTIMIZED FOR SQLITE
        self.max_parallel_workers = 3  # Reduced from 4 - SQLite works best with 2-4
        self.download_progress = {}
    
    def _get_connection(self):
        """Get a connection from the pool or create new one with UTF-8 encoding"""
        with self._connection_lock:
            if self._connection_pool:
                return self._connection_pool.pop()
            else:
                # Use shared utility with SQLite optimization pragmas
                conn = get_utf8_connection(
                    self.db_path,
                    journal_mode='WAL',
                    synchronous='NORMAL',
                    cache_size=10000,
                    temp_store='MEMORY'
                )
                return conn
    
    def _return_connection(self, conn):
        """Return connection to pool"""
        with self._connection_lock:
            if len(self._connection_pool) < self._max_pool_size:
                self._connection_pool.append(conn)
            else:
                conn.close()
    
    def _init_database(self):
        """Initialize SQLite database with UTF-8 encoding"""
        conn = get_utf8_connection(
            self.db_path,
            journal_mode='WAL',
            synchronous='NORMAL',
            cache_size=10000,
            temp_store='MEMORY'
        )
        
        cursor = conn.cursor()
        
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
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_symbol 
            ON stock_bars(symbol)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_symbol_timestamp 
            ON stock_bars(symbol, timestamp)
        ''')
        
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
    
    # ============================================================
    # 🚀 FAST BATCH LOADING - UTF-8 SAFE
    # ============================================================
    
    def load_multiple_symbols_batch(self, symbols, start_date=None, end_date=None):
        """
        🚀 FAST: Load multiple symbols in a single query with UTF-8 safety
        This is 10-50x faster than loading symbols individually
        """
        if not symbols:
            return {}
        
        # Clean all symbols
        symbols_clean = [clean_ticker(s) for s in symbols]
        symbols_clean = [s for s in symbols_clean if s]  # Remove None values
        
        if not symbols_clean:
            return {}
        
        conn = self._get_connection()
        
        try:
            # Build query with date filtering if provided
            query = 'SELECT symbol, timestamp, open, high, low, close, volume, trade_count, vwap FROM stock_bars WHERE symbol IN ('
            query += ','.join('?' * len(symbols_clean))
            query += ')'
            
            params = symbols_clean.copy()
            
            if start_date and end_date:
                start_ts = int(start_date.timestamp())
                end_ts = int(end_date.timestamp())
                query += ' AND timestamp >= ? AND timestamp <= ?'
                params.extend([start_ts, end_ts])
            
            query += ' ORDER BY symbol, timestamp'
            
            # Execute single query for all symbols
            df_all = pd.read_sql_query(query, conn, params=params)
            
            self._return_connection(conn)
            
            if df_all.empty:
                return {}
            
            # Convert timestamps
            df_all['timestamp'] = pd.to_datetime(df_all['timestamp'], unit='s')
            
            # Split by symbol
            result = {}
            
            # Add progress bar for symbol processing
            if not self.quiet and len(symbols_clean) > 10:
                from tqdm import tqdm
                symbol_iterator = tqdm(symbols_clean, desc="Processing symbols", unit="sym", 
                                    bar_format='{desc}: {percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt}')
            else:
                symbol_iterator = symbols_clean
            
            for symbol in symbol_iterator:
                df_symbol = df_all[df_all['symbol'] == symbol].copy()
                if not df_symbol.empty:
                    df_symbol.set_index('timestamp', inplace=True)
                    df_symbol.drop('symbol', axis=1, inplace=True)
                    result[symbol] = df_symbol
            
            return result
            
        except Exception as e:
            print(f"❌ Batch load error: {e}")
            self._return_connection(conn)
            return {}
    
    def load_offline_data(self, symbol, start_date=None, end_date=None):
        """Load cached data for a single symbol with UTF-8 safety"""
        try:
            # Clean symbol
            symbol = clean_ticker(symbol)
            if not symbol:
                return None
            
            conn = self._get_connection()
            
            query = 'SELECT timestamp, open, high, low, close, volume, trade_count, vwap FROM stock_bars WHERE symbol = ?'
            params = [symbol]
            
            if start_date and end_date:
                start_ts = int(start_date.timestamp())
                end_ts = int(end_date.timestamp())
                query += ' AND timestamp >= ? AND timestamp <= ?'
                params.extend([start_ts, end_ts])
            
            query += ' ORDER BY timestamp'
            
            df = pd.read_sql_query(query, conn, params=params)
            
            self._return_connection(conn)
            
            if df.empty:
                return None
            
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
            df.set_index('timestamp', inplace=True)
            
            return df
            
        except Exception as e:
            print(f"❌ Database error loading {symbol}: {e}")
            if 'conn' in locals():
                self._return_connection(conn)
            return None
    
    def save_offline_data(self, symbol, df):
        """Save data to SQLite database with UTF-8 safety"""
        try:
            # Clean symbol
            symbol = clean_ticker(symbol)
            if not symbol:
                return False
            
            conn = self._get_connection()
            
            df_to_save = df.copy()
            df_to_save['symbol'] = symbol
            df_to_save['timestamp'] = df_to_save.index.astype('int64') // 10**9
            
            required_cols = ['symbol', 'timestamp', 'open', 'high', 'low', 'close', 'volume']
            optional_cols = ['trade_count', 'vwap']
            
            for col in optional_cols:
                if col not in df_to_save.columns:
                    df_to_save[col] = None
            
            cols_to_save = required_cols + optional_cols
            df_to_save = df_to_save[cols_to_save]
            
            df_to_save.to_sql('stock_bars', conn, if_exists='append', index=False, method='multi')
            
            self._update_metadata(symbol, conn)
            
            conn.commit()
            self._return_connection(conn)
            
            return True
            
        except sqlite3.IntegrityError:
            try:
                cursor = conn.cursor()
                
                for idx, row in df.iterrows():
                    timestamp = int(idx.timestamp())
                    cursor.execute('''
                        INSERT OR REPLACE INTO stock_bars 
                        (symbol, timestamp, open, high, low, close, volume, trade_count, vwap)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        symbol,
                        timestamp,
                        float(row['open']),
                        float(row['high']),
                        float(row['low']),
                        float(row['close']),
                        int(row['volume']),
                        row.get('trade_count'),
                        row.get('vwap')
                    ))
                
                self._update_metadata(symbol, conn)
                conn.commit()
                self._return_connection(conn)
                
                return True
            except Exception as e:
                print(f"❌ Error saving {symbol} (retry): {e}")
                if 'conn' in locals():
                    self._return_connection(conn)
                return False
            
        except Exception as e:
            print(f"❌ Error saving {symbol}: {e}")
            if 'conn' in locals():
                self._return_connection(conn)
            return False
    
    def _update_metadata(self, symbol, conn):
        """Update metadata for a symbol with UTF-8 safety"""
        # Ensure symbol is clean
        symbol = clean_ticker(symbol)
        if not symbol:
            return
        
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
    
    # ============================================================
    # API FETCHING METHODS
    # ============================================================
    
    def _is_rate_limit_error(self, error_msg):
        """Check if error is a rate limit error"""
        error_str = str(error_msg).lower()
        return 'too many requests' in error_str or 'rate limit' in error_str or '429' in error_str
    
    def _activate_trickle_mode(self):
        """Activate trickle mode when rate limited"""
        if not self.trickle_mode:
            print(f"\n⚠️  RATE LIMIT DETECTED - Activating Trickle Mode")
            print(f"   Switching to sequential downloads with {self.trickle_delay}s delays")
            print(f"   Cooling down for {self.rate_limit_cooldown}s first...")
            time.sleep(self.rate_limit_cooldown)
            self.trickle_mode = True
    
    def fetch_from_api(self, symbol, start_date, end_date, retry_count=None):
        """Fetch data from Alpaca API with rate limit detection and UTF-8 safety"""
        if retry_count is None:
            retry_count = self.retry_count
        
        # Clean symbol
        symbol = clean_ticker(symbol)
        if not symbol:
            return None
        
        if isinstance(start_date, pd.Timestamp) and start_date.tz is not None:
            start_date = start_date.tz_localize(None)
        if isinstance(end_date, pd.Timestamp) and end_date.tz is not None:
            end_date = end_date.tz_localize(None)
        
        if self.trickle_mode:
            time.sleep(self.trickle_delay)
        
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
                        days_diff = (end_date - start_date).days
                        if days_diff > 30:
                            end_date = start_date + timedelta(days=30)
                            time.sleep(self.retry_delay)
                            continue
                    raise ValueError(f"No data returned from API for {symbol}")
                
                if isinstance(df.index, pd.MultiIndex):
                    df = df.xs(symbol, level=0)
                
                df.index = pd.to_datetime(df.index)
                if df.index.tz is not None:
                    df.index = df.index.tz_localize(None)
                
                if self.rate_limit_errors > 0:
                    self.rate_limit_errors = max(0, self.rate_limit_errors - 1)
                
                return df
                
            except Exception as e:
                error_msg = str(e)
                
                if self._is_rate_limit_error(error_msg):
                    self.rate_limit_errors += 1
                    print(f"⚠️  Rate limit hit for {symbol} (error #{self.rate_limit_errors})")
                    
                    if self.rate_limit_errors >= self.max_rate_limit_errors:
                        self._activate_trickle_mode()
                    
                    wait_time = self.rate_limit_cooldown if not self.trickle_mode else self.trickle_delay
                    if attempt < retry_count - 1:
                        print(f"   ⏳ Waiting {wait_time}s before retry...")
                        time.sleep(wait_time)
                        continue
                
                if attempt < retry_count - 1:
                    if not self.quiet:
                        print(f"⚠️  API error for {symbol} (attempt {attempt + 1}/{retry_count}): {error_msg}, retrying...")
                    time.sleep(self.retry_delay * (attempt + 1))
                else:
                    print(f"❌ API error for {symbol} (attempt {attempt + 1}/{retry_count}): {error_msg}")
                    self.api_errors.append({
                        'symbol': symbol,
                        'error': ensure_utf8(error_msg),
                        'timestamp': datetime.now()
                    })
                    self.failed_symbols.add(symbol)
                    return None
        
        return None
    
    def get_data_range(self, symbol):
        """Get the date range of cached data for a symbol with UTF-8 safety"""
        try:
            # Clean symbol
            symbol = clean_ticker(symbol)
            if not symbol:
                return None
            
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT earliest_timestamp, latest_timestamp, bar_count
                FROM symbol_metadata
                WHERE symbol = ?
            ''', (symbol,))
            
            row = cursor.fetchone()
            self._return_connection(conn)
            
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
        """Identify gaps in the data with UTF-8 safety"""
        # Clean symbol
        symbol = clean_ticker(symbol)
        if not symbol:
            return []
        
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
        
        if start_date < df_start - timedelta(days=1):
            gap_end = df_start - timedelta(hours=1)
            if gap_end > start_date:
                gaps.append((start_date, gap_end))
        
        if end_date > df_end + timedelta(days=1):
            gap_start = df_end + timedelta(hours=1)
            if end_date > gap_start:
                gaps.append((gap_start, end_date))
        
        return gaps
    
    def get_stock_data(self, symbol, days=180):
        """Main method to get stock data with UTF-8 safety"""
        try:
            # Clean symbol
            symbol = clean_ticker(symbol)
            if not symbol:
                print(f"❌ Invalid symbol provided")
                return None
            
            end_date = datetime.now().replace(tzinfo=None)
            start_date = (end_date - timedelta(days=days)).replace(tzinfo=None)
            
            data_range = self.get_data_range(symbol)
            
            if data_range:
                buffer = timedelta(days=3)
                coverage_start = data_range['start'] - buffer
                coverage_end = data_range['end'] + buffer
                
                if coverage_start <= start_date and coverage_end >= end_date:
                    return self.load_offline_data(symbol, start_date, end_date)
            
            gaps = self.find_gaps(symbol, start_date, end_date)
            
            if not gaps:
                return self.load_offline_data(symbol, start_date, end_date)
            
            if self.offline_mode:
                print(f"⚠️  {symbol}: Missing data in offline mode")
                return None
            
            if not self.quiet and not self.trickle_mode:
                print(f"📥 {symbol}: Downloading {len(gaps)} gap(s)...")
            
            for gap_start, gap_end in gaps:
                if (gap_end - gap_start).total_seconds() < 7200:
                    continue
                    
                gap_data = self.fetch_from_api(symbol, gap_start, gap_end)
                if gap_data is not None:
                    self.save_offline_data(symbol, gap_data)
                else:
                    print(f"⚠️  {symbol}: Partial data available")
            
            return self.load_offline_data(symbol, start_date, end_date)
            
        except Exception as e:
            print(f"❌ Unexpected error for {symbol}: {e}")
            return None
    
    def list_cached_symbols(self):
        """List all symbols with cached data with UTF-8 safety"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT symbol, earliest_timestamp, latest_timestamp, bar_count
                FROM symbol_metadata
                ORDER BY symbol
            ''')
            
            cached = []
            for row in cursor.fetchall():
                # Ensure symbol is UTF-8 clean
                symbol = ensure_utf8(row[0])
                start_date = datetime.fromtimestamp(row[1]).date()
                end_date = datetime.fromtimestamp(row[2]).date()
                cached.append({
                    'symbol': symbol,
                    'bars': row[3],
                    'date_range': f"{start_date} to {end_date}"
                })
            
            self._return_connection(conn)
            return cached
        except Exception as e:
            print(f"❌ Error listing cached symbols: {e}")
            return []
    
    def print_cache_status(self):
        """Print status of offline cache with UTF-8 safety"""
        try:
            cached = self.list_cached_symbols()
            
            db_size_mb = self.db_path.stat().st_size / (1024 * 1024) if self.db_path.exists() else 0
            
            print(f"\n{'='*60}")
            print(f"OFFLINE CACHE STATUS (SQLite) - UTF-8 SAFE")
            print(f"{'='*60}")
            print(f"Location: {self.db_path.absolute()}")
            print(f"Database size: {db_size_mb:.2f} MB")
            print(f"Total symbols: {len(cached)}")
            print(f"{'='*60}\n")
            
            if cached:
                print(f"{'Symbol':<10} {'Bars':<10} {'Date Range'}")
                print(f"{'-'*60}")
                for item in cached[:20]:
                    symbol = ensure_utf8(item['symbol'])
                    print(f"{symbol:<10} {item['bars']:<10} {item['date_range']}")
                
                if len(cached) > 20:
                    print(f"... and {len(cached) - 20} more")
            else:
                print("No cached data found.")
            
            print()
        except Exception as e:
            print(f"❌ Error printing cache status: {e}")
    
    def vacuum_database(self):
        """Optimize database with UTF-8 safety"""
        try:
            print("Optimizing database...")
            conn = get_utf8_connection_data(self.db_path)
            conn.execute('VACUUM')
            conn.execute('ANALYZE')
            conn.close()
            print("✅ Database optimized")
        except Exception as e:
            print(f"❌ Error optimizing database: {e}")
    
    def close_all_connections(self):
        """Clean up connection pool"""
        with self._connection_lock:
            for conn in self._connection_pool:
                try:
                    conn.close()
                except:
                    pass
            self._connection_pool.clear()

    def __del__(self):
        """Cleanup connection pool on exit"""
        self.close_all_connections()