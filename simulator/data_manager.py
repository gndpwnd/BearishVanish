"""
Enhanced Data Manager with Hybrid Download Model and Smart Retry Logic
Automatically switches to trickle mode when rate limited
Provides methods for both single and batch downloads
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

OFFLINE_DATA_DIR = Path('./offline_data')
DB_PATH = OFFLINE_DATA_DIR / 'stock_data.db'
PROGRESS_FILE = OFFLINE_DATA_DIR / 'download_progress.json'

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
        self.retry_count = 3
        self.retry_delay = 2
        
        # 🆕 TRICKLE MODE SETTINGS
        self.trickle_mode = False
        self.trickle_delay = 8  # seconds between requests in trickle mode
        self.rate_limit_cooldown = 60  # wait 60s after hitting rate limit
        self.rate_limit_errors = 0
        self.max_rate_limit_errors = 3  # switch to trickle after 3 rate limit errors
        
        # 🆕 BATCH DOWNLOAD SETTINGS
        self.max_parallel_workers = 4
        self.download_progress = {}
        
    def _init_database(self):
        """Initialize SQLite database with optimized schema"""
        conn = sqlite3.connect(self.db_path)
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
            
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
            df.set_index('timestamp', inplace=True)
            
            return df
            
        except Exception as e:
            print(f"❌ Database error loading {symbol}: {e}")
            if 'conn' in locals():
                conn.close()
            return None

    def save_offline_data(self, symbol, df):
        """Save data to SQLite database"""
        try:
            symbol = symbol.upper()
            conn = sqlite3.connect(self.db_path)
            
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
            conn.close()
            
            return True
            
        except sqlite3.IntegrityError:
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
        """
        Fetch data from Alpaca API with rate limit detection and retry logic
        
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
        
        # 🆕 Apply trickle delay if in trickle mode
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
                
                # 🆕 Success! Reset rate limit counter if we were having issues
                if self.rate_limit_errors > 0:
                    self.rate_limit_errors = max(0, self.rate_limit_errors - 1)
                
                return df
                
            except Exception as e:
                error_msg = str(e)
                
                # 🆕 Check if this is a rate limit error
                if self._is_rate_limit_error(error_msg):
                    self.rate_limit_errors += 1
                    print(f"⚠️  Rate limit hit for {symbol} (error #{self.rate_limit_errors})")
                    
                    if self.rate_limit_errors >= self.max_rate_limit_errors:
                        self._activate_trickle_mode()
                    
                    # Wait longer for rate limit errors
                    wait_time = self.rate_limit_cooldown if not self.trickle_mode else self.trickle_delay
                    if attempt < retry_count - 1:
                        print(f"   ⏳ Waiting {wait_time}s before retry...")
                        time.sleep(wait_time)
                        continue
                
                # Regular error handling
                if attempt < retry_count - 1:
                    if not self.quiet:
                        print(f"⚠️  API error for {symbol} (attempt {attempt + 1}/{retry_count}): {error_msg}, retrying...")
                    time.sleep(self.retry_delay * (attempt + 1))
                else:
                    print(f"❌ API error for {symbol} (attempt {attempt + 1}/{retry_count}): {error_msg}")
                    self.api_errors.append({
                        'symbol': symbol,
                        'error': error_msg,
                        'timestamp': datetime.now()
                    })
                    self.failed_symbols.add(symbol)
                    return None
        
        return None
    
    # 🆕 NEW HYBRID DOWNLOAD METHODS
    
    def download_symbols_with_hybrid_mode(self, symbols, days=180, max_workers=None, 
                                          trickle_only=False, session_id=None):
        """
        Download multiple symbols with automatic trickle mode switching
        
        Args:
            symbols: List of symbols to download
            days: Number of days of historical data
            max_workers: Maximum parallel workers (default: self.max_parallel_workers)
            trickle_only: If True, use trickle mode from start
            session_id: Optional session ID for progress tracking
        
        Returns:
            dict: {symbol: DataFrame or None}
        """
        if max_workers is None:
            max_workers = self.max_parallel_workers
        
        if trickle_only:
            # Force trickle mode from start
            self._activate_trickle_mode()
            return self._download_in_trickle_mode(symbols, days, session_id)
        else:
            # Try parallel first, fall back to trickle if rate limited
            return self._download_with_parallel_fallback(symbols, days, max_workers, session_id)
    
    def _download_with_parallel_fallback(self, symbols, days, max_workers, session_id=None):
        """
        Download with parallel execution, automatically falling back to trickle mode
        """
        results = {}
        
        print(f"\n🚀 Starting parallel download with {max_workers} workers...")
        print(f"📊 Total symbols: {len(symbols)}\n")
        
        def download_symbol(symbol):
            """Download a single symbol with smart gap detection"""
            try:
                df = self.get_stock_data(symbol, days=days)
                
                if df is not None and not df.empty:
                    actual_days = (df.index[-1] - df.index[0]).days
                    expected_days = days
                    
                    if actual_days < expected_days * 0.8:  # Got less than 80% of requested data
                        return (symbol, df, f"Partial data ({actual_days}/{expected_days} days)")
                    
                    return (symbol, df, None)
                else:
                    return (symbol, None, "No data available")
                    
            except Exception as e:
                return (symbol, None, str(e))
        
        # Use tqdm for progress bar
        with ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix='Downloader') as executor:
            futures = {executor.submit(download_symbol, sym): sym for sym in symbols}
            
            with tqdm(total=len(symbols), desc="Downloading", unit="stock") as pbar:
                for future in as_completed(futures):
                    symbol, df, error = future.result()
                    
                    if error or df is None:
                        if error and self._is_rate_limit_error(error):
                            # Rate limit hit! Cancel remaining futures and switch to trickle
                            tqdm.write(f"\n⚠️  RATE LIMIT DETECTED! Cancelling parallel downloads...")
                            
                            # Cancel remaining futures
                            for f in futures:
                                f.cancel()
                            
                            # Break out of this loop
                            pbar.close()
                            
                            # Get list of symbols that weren't completed
                            completed_symbols = set(results.keys())
                            remaining_symbols = [s for s in symbols if s not in completed_symbols]
                            
                            print(f"🐢 Switching to trickle mode for remaining {len(remaining_symbols)} symbols...")
                            
                            # Switch to trickle mode
                            self._activate_trickle_mode()
                            
                            # Download remaining in trickle mode
                            trickle_results = self._download_in_trickle_mode(
                                remaining_symbols, 
                                days, 
                                session_id
                            )
                            results.update(trickle_results)
                            break
                        else:
                            # Regular error, not rate limit
                            error_msg = error if error else "No data returned"
                            tqdm.write(f"  ❌ {symbol}: {error_msg}")
                            results[symbol] = None
                    else:
                        # Success!
                        results[symbol] = df
                        
                        # Show data range if we got partial data
                        if "Partial data" in (error or ""):
                            actual_days = (df.index[-1] - df.index[0]).days
                            tqdm.write(f"  ⚠️  {symbol}: {actual_days}/{days} days (partial)")
                        else:
                            tqdm.write(f"  ✅ {symbol}: {len(df)} bars ({days} days)")
                    
                    pbar.update(1)
        
        return results
    
    def _download_in_trickle_mode(self, symbols, days, session_id=None):
        """
        Download in trickle mode (sequential with delays)
        """
        results = {}
        
        print(f"\n🐢 TRICKLE MODE ACTIVE")
        print(f"   Downloading {len(symbols)} symbols sequentially")
        print(f"   Delay: {self.trickle_delay}s between requests\n")
        
        with tqdm(total=len(symbols), desc="Trickle download", unit="stock") as pbar:
            for symbol in symbols:
                try:
                    df = self.get_stock_data(symbol, days=days)
                    
                    if df is not None and not df.empty:
                        actual_days = (df.index[-1] - df.index[0]).days
                        
                        if actual_days < days * 0.8:  # Got less than 80% of requested data
                            tqdm.write(f"  ⚠️  {symbol}: {actual_days}/{days} days (partial)")
                        else:
                            tqdm.write(f"  ✅ {symbol}: {len(df)} bars ({days} days)")
                        
                        results[symbol] = df
                    else:
                        tqdm.write(f"  ❌ {symbol}: No data available")
                        results[symbol] = None
                
                except Exception as e:
                    error_msg = str(e)
                    tqdm.write(f"  ❌ {symbol}: {error_msg}")
                    results[symbol] = None
                
                pbar.update(1)
        
        return results
    
    def save_download_progress(self, symbols, days, results, filename='download_progress.json'):
        """Save download progress to file"""
        progress = {
            'symbols': symbols,
            'days': days,
            'results': {k: (v is not None) for k, v in results.items()},
            'timestamp': datetime.now().isoformat(),
            'successful': sum(1 for v in results.values() if v is not None),
            'total': len(symbols)
        }
        
        progress_file = self.offline_data_dir / filename
        with open(progress_file, 'w') as f:
            json.dump(progress, f, indent=2)
        
        return progress_file
    
    # EXISTING METHODS (keep as is, just adding new functionality)
    
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
        """Identify gaps in the data using metadata"""
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
        """
        Main method to get stock data with automatic trickle mode
        
        Returns:
            DataFrame if successful
            None if data unavailable
        """
        try:
            symbol = symbol.upper()
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

    # Keep all other methods (list_cached_symbols, print_cache_status, etc.)
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
                for item in cached[:20]:
                    print(f"{item['symbol']:<10} {item['bars']:<10} {item['date_range']}")
                
                if len(cached) > 20:
                    print(f"... and {len(cached) - 20} more")
            else:
                print("No cached data found.")
            
            print()
        except Exception as e:
            print(f"❌ Error printing cache status: {e}")
    
    def vacuum_database(self):
        """Optimize database"""
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
        
        for error in self.api_errors[-10:]:
            print(f"  {error['timestamp'].strftime('%H:%M:%S')} - {error['symbol']}: {error['error'][:50]}")
        
        print(f"\n{'='*60}\n")