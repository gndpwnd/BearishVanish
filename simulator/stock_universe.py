"""
Stock Universe Manager (Modular Version) - UTF-8 SAFE VERSION
Core functionality: Fetching and storing stock universes
Reporting/diagnostics delegated to helper modules
"""

import os
import sqlite3
import json
import pandas as pd
import requests
from datetime import datetime, date, timedelta
from pathlib import Path
from io import StringIO
from ticker_validation import TickerValidator

UNIVERSE_DIR = Path('./universes')
UNIVERSE_DB_PATH = UNIVERSE_DIR / 'stock_universe.db'

# ============================================================
# UTF-8 SAFETY HELPERS
# ============================================================

def ensure_utf8_universe(text):
    """Ensure text is valid UTF-8"""
    if text is None:
        return None
    
    if isinstance(text, bytes):
        try:
            return text.decode('utf-8', errors='replace')
        except:
            return text.decode('latin-1', errors='replace')
    
    if not isinstance(text, str):
        text = str(text)
    
    try:
        text.encode('utf-8')
        return text
    except UnicodeEncodeError:
        return text.encode('utf-8', errors='replace').decode('utf-8')

def get_utf8_connection_universe(db_path):
    """Create SQLite connection with UTF-8 encoding"""
    conn = sqlite3.connect(db_path)
    conn.text_factory = str
    conn.execute("PRAGMA encoding = 'UTF-8'")
    return conn

def clean_ticker_utf8(ticker):
    """Clean ticker symbol and ensure UTF-8/ASCII compatibility"""
    if not ticker:
        return None
    
    # Ensure UTF-8
    ticker = ensure_utf8_universe(ticker)
    
    # Strip whitespace and convert to uppercase
    ticker = ticker.strip().upper()
    
    # Remove any non-ASCII characters (ticker symbols should be ASCII)
    ticker = ''.join(c for c in ticker if ord(c) < 128)
    
    return ticker if ticker else None

def sanitize_json_utf8(data):
    """Sanitize data before JSON serialization"""
    if data is None:
        return None
    
    if isinstance(data, dict):
        sanitized = {
            ensure_utf8_universe(k): ensure_utf8_universe(v) if isinstance(v, str) else v
            for k, v in data.items()
        }
        return json.dumps(sanitized, ensure_ascii=False)
    elif isinstance(data, list):
        sanitized = [
            ensure_utf8_universe(item) if isinstance(item, str) else item
            for item in data
        ]
        return json.dumps(sanitized, ensure_ascii=False)
    else:
        return json.dumps(ensure_utf8_universe(str(data)), ensure_ascii=False)

class UniverseManager:
    def __init__(self, api_key=None, secret_key=None):
        """Initialize Universe Manager with SQLite storage"""
        self.universe_dir = UNIVERSE_DIR
        self.universe_dir.mkdir(exist_ok=True)
        self.db_path = UNIVERSE_DB_PATH
        self.api_key = api_key
        self.secret_key = secret_key
        self._init_database()
        
        # Initialize helper modules (lazy loading)
        self._diagnostics = None
        self._reporter = None
    
    @property
    def diagnostics(self):
        """Lazy load diagnostics module"""
        if self._diagnostics is None:
            from universe_diagnostics import UniverseDiagnostics
            self._diagnostics = UniverseDiagnostics(self)
        return self._diagnostics
    
    @property
    def reporter(self):
        """Lazy load reporter module"""
        if self._reporter is None:
            from universe_reporting import UniverseReporter
            self._reporter = UniverseReporter(self)
        return self._reporter
    
    def _init_database(self):
        """Initialize SQLite database with UTF-8 encoding"""
        conn = get_utf8_connection_universe(self.db_path)
        cursor = conn.cursor()
        
        # Set UTF-8 encoding explicitly
        cursor.execute("PRAGMA encoding = 'UTF-8'")
        
        # Table 1: Current and historical constituents
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
        
        # Table 2: Daily snapshots for fast queries
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_snapshots (
                date DATE NOT NULL,
                universe_name TEXT NOT NULL,
                tickers_json TEXT NOT NULL,
                ticker_count INTEGER NOT NULL,
                PRIMARY KEY (date, universe_name)
            )
        ''')
        
        # Table 3: Change log
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
        
        # Indexes for fast lookups
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_constituents_symbol 
            ON universe_constituents(symbol)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_constituents_universe_date 
            ON universe_constituents(universe_name, date_removed)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_snapshots_date 
            ON daily_snapshots(date, universe_name)
        ''')
        
        conn.commit()
        conn.close()
    
    # ============================================================
    # FETCHING FUNCTIONS (Core Data Sources) - UTF-8 SAFE
    # ============================================================
    
    def _fetch_sp500(self):
        """Fetch S&P 500 from Wikipedia with UTF-8 safety"""
        try:
            url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            # Fetch with explicit encoding
            response = requests.get(url, headers=headers)
            response.encoding = 'utf-8'  # Explicitly set encoding
            response.raise_for_status()
            
            # Parse HTML with UTF-8
            tables = pd.read_html(StringIO(response.text), encoding='utf-8')
            df = tables[0]
            
            # Clean tickers with UTF-8 safety
            raw_tickers = df['Symbol'].astype(str).tolist()
            tickers = [clean_ticker_utf8(t) for t in raw_tickers]
            tickers = [t for t in tickers if t]  # Remove None values
            
            # Additional cleaning from ticker_validation
            try:
                from ticker_validation import clean_tickers
                cleaned_tickers = clean_tickers(tickers)
            except ImportError:
                cleaned_tickers = tickers  # Fallback
            
            if len(cleaned_tickers) < len(tickers):
                print(f"  ℹ️  Filtered out {len(tickers) - len(cleaned_tickers)} invalid entries")
            
            print(f"  ✅ Fetched {len(cleaned_tickers)} S&P 500 tickers from Wikipedia")
            
            return cleaned_tickers, df
            
        except Exception as e:
            print(f"  ❌ Error fetching S&P 500: {e}")
            return None, None
    
    def _fetch_nasdaq100(self):
        """Fetch NASDAQ 100 from Slickcharts with UTF-8 safety"""
        try:
            url = 'https://www.slickcharts.com/nasdaq100'
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            # Fetch with explicit encoding
            response = requests.get(url, headers=headers)
            response.encoding = 'utf-8'
            response.raise_for_status()
            
            # Parse HTML with UTF-8
            tables = pd.read_html(StringIO(response.text), encoding='utf-8')
            df = tables[0]
            
            # Clean tickers with UTF-8 safety
            raw_tickers = df['Symbol'].astype(str).tolist()
            tickers = [clean_ticker_utf8(t) for t in raw_tickers]
            tickers = [t for t in tickers if t]
            
            # Additional cleaning
            try:
                from ticker_validation import clean_tickers
                cleaned_tickers = clean_tickers(tickers)
            except ImportError:
                cleaned_tickers = tickers
            
            if len(cleaned_tickers) < len(tickers):
                print(f"  ℹ️  Filtered out {len(tickers) - len(cleaned_tickers)} invalid entries")
            
            print(f"  ✅ Fetched {len(cleaned_tickers)} NASDAQ 100 tickers from Slickcharts")
            
            return cleaned_tickers, df
            
        except Exception as e:
            print(f"  ❌ Error fetching NASDAQ 100: {e}")
            return None, None
    
    def _fetch_russell3000(self):
        """Fetch Russell 3000 with UTF-8 safety"""
        # Try multiple date formats for iShares
        attempts = [
            datetime.now().strftime('%Y%m%d'),
            (datetime.now() - timedelta(days=1)).strftime('%Y%m%d'),
            (datetime.now() - timedelta(days=7)).strftime('%Y%m%d'),
        ]
        
        for date_str in attempts:
            try:
                url = f'https://www.ishares.com/us/products/239714/ishares-russell-3000-etf/1467271812596.ajax?fileType=csv&fileName=IWV_holdings&dataType=fund&asOfDate={date_str}'
                
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
                
                response = requests.get(url, headers=headers, timeout=10)
                response.encoding = 'utf-8'  # Set encoding
                response.raise_for_status()
                
                # Save CSV for inspection
                csv_path = self.universe_dir / 'temp_russell3000.csv'
                with open(csv_path, 'wb') as f:
                    f.write(response.content)
                
                # Debug: Show file size
                file_size_kb = csv_path.stat().st_size / 1024
                print(f"  📁 Downloaded CSV: {file_size_kb:.1f} KB")
                
                # Try to read CSV with different skip rows
                for skip in [10, 9, 11, 12]:
                    try:
                        # Read with UTF-8 encoding
                        df = pd.read_csv(csv_path, skiprows=skip, encoding='utf-8')
                        
                        # Debug: Show columns found
                        if skip == 10:
                            print(f"  📋 Columns found: {df.columns.tolist()[:5]}...")
                        
                        # Try different column names
                        ticker_col = None
                        for col in ['Ticker', 'Symbol', 'ticker', 'symbol', 'TICKER']:
                            if col in df.columns:
                                ticker_col = col
                                break
                        
                        if ticker_col:
                            # Filter out empty and non-stock entries
                            df = df[df[ticker_col].notna()]
                            df = df[df[ticker_col].astype(str).str.strip() != '']
                            
                            # Remove common non-stock entries
                            df = df[~df[ticker_col].astype(str).str.contains('CASH|USD|Total', case=False, na=False)]
                            
                            # Clean tickers with UTF-8 safety
                            raw_tickers = df[ticker_col].astype(str).str.strip().tolist()
                            tickers = [clean_ticker_utf8(t) for t in raw_tickers]
                            tickers = [t for t in tickers if t]
                            
                            # Only accept if we got a reasonable number
                            if len(tickers) > 100:
                                # Additional cleaning
                                try:
                                    from ticker_validation import clean_tickers
                                    cleaned_tickers = clean_tickers(tickers)
                                except ImportError:
                                    cleaned_tickers = tickers
                                
                                # Clean up
                                csv_path.unlink()
                                
                                if len(cleaned_tickers) < len(tickers):
                                    print(f"  ℹ️  Filtered out {len(tickers) - len(cleaned_tickers)} invalid entries")
                                
                                print(f"  ✅ Fetched {len(cleaned_tickers)} Russell 3000 tickers from iShares IWV (date: {date_str})")
                                return cleaned_tickers, df
                            else:
                                print(f"  ⚠️  Only found {len(tickers)} tickers with skip={skip}, trying next...")
                    except Exception as e:
                        if skip == 10:
                            print(f"  ⚠️  Parse error with skip={skip}: {e}")
                        continue
                
                # If we got here, parsing failed - show first few lines for debugging
                print(f"\n  🔍 DEBUG: First 15 lines of CSV:")
                try:
                    with open(csv_path, 'r', encoding='utf-8', errors='ignore') as f:
                        for i, line in enumerate(f):
                            if i < 15:
                                print(f"    Line {i}: {ensure_utf8_universe(line[:80].strip())}")
                except Exception:
                    pass
                
                # Clean up failed attempt
                if csv_path.exists():
                    csv_path.unlink()
                    
            except Exception as e:
                print(f"  ⚠️  Attempt with date {date_str} failed: {e}")
                continue
        
        # All attempts failed - try GitHub fallback
        print(f"\n  ⚠️  iShares source unavailable, trying GitHub...")
        
        try:
            url = 'https://raw.githubusercontent.com/fja05680/sp500/master/data/russell3000.csv'
            df = pd.read_csv(url, encoding='utf-8')
            
            # Find ticker column
            ticker_col = None
            for col in df.columns:
                if 'ticker' in col.lower() or 'symbol' in col.lower():
                    ticker_col = col
                    break
            
            if ticker_col:
                raw_tickers = df[ticker_col].dropna().astype(str).str.strip().tolist()
                tickers = [clean_ticker_utf8(t) for t in raw_tickers]
                tickers = [t for t in tickers if t]
                print(f"  ✅ Fetched {len(tickers)} Russell 3000 tickers from GitHub")
                return tickers, df
        except Exception as e:
            print(f"  ⚠️  GitHub source also failed: {e}")
        
        # Final fallback - use S&P 500 as approximation
        print(f"\n  ℹ️  All Russell 3000 sources failed")
        print(f"  ℹ️  Using S&P 500 as approximation (will update when source available)")
        
        tickers, df = self._fetch_sp500()
        if tickers:
            print(f"  ⚠️  This is NOT real Russell 3000 - only {len(tickers)} stocks")
            return tickers, df
        
        return None, None
    
    # ============================================================
    # CORE UNIVERSE MANAGEMENT - UTF-8 SAFE
    # ============================================================
    
    def update_universe(self, universe_name):
        """Update a universe by fetching current constituents and detecting changes"""
        if universe_name == 'all':
            for name in ['sp500', 'nasdaq100', 'russell3000']:
                self.update_universe(name)
            return
        
        print(f"\n{'='*70}")
        print(f"UPDATING {universe_name.upper()} UNIVERSE")
        print(f"{'='*70}")
        
        # Clean universe name
        universe_name = ensure_utf8_universe(universe_name)
        
        # Fetch current tickers
        if universe_name == 'sp500':
            tickers, df = self._fetch_sp500()
        elif universe_name == 'nasdaq100':
            tickers, df = self._fetch_nasdaq100()
        elif universe_name == 'russell3000':
            tickers, df = self._fetch_russell3000()
        else:
            print(f"❌ Unknown universe: {universe_name}")
            return
        
        if not tickers:
            print(f"❌ Failed to fetch {universe_name}")
            return
        
        # Ensure all tickers are UTF-8 clean
        tickers = [clean_ticker_utf8(t) for t in tickers]
        tickers = [t for t in tickers if t]
        
        # Get previous constituents
        previous_tickers = self._get_current_constituents(universe_name)
        
        # Detect changes
        added = set(tickers) - set(previous_tickers)
        removed = set(previous_tickers) - set(tickers)
        
        current_date = date.today()
        conn = get_utf8_connection_universe(self.db_path)
        cursor = conn.cursor()
        
        # Mark removed stocks
        if removed:
            print(f"\n📉 REMOVALS DETECTED: {len(removed)} stocks")
            
            # Only show first 10 removals
            sample_removed = list(removed)[:10]
            for symbol in sample_removed:
                print(f"  • {ensure_utf8_universe(symbol)} removed")
            
            if len(removed) > 10:
                print(f"  • ... and {len(removed) - 10} more")
            
            # Update all removals in database
            for symbol in removed:
                symbol_utf8 = ensure_utf8_universe(symbol)
                cursor.execute('''
                    UPDATE universe_constituents
                    SET date_removed = ?
                    WHERE symbol = ? AND universe_name = ? AND date_removed IS NULL
                ''', (current_date, symbol_utf8, universe_name))
                
                # Log change
                cursor.execute('''
                    INSERT OR IGNORE INTO change_log 
                    (timestamp, date, universe_name, symbol, action, reason)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (int(datetime.now().timestamp()), current_date, universe_name, 
                      symbol_utf8, 'REMOVED', 'Removed from index'))
        
        # Add new stocks
        if added:
            print(f"\n📈 ADDITIONS DETECTED: {len(added)} stocks")
            
            # Only show first 10 additions
            sample_added = list(added)[:10]
            for symbol in sample_added:
                print(f"  • {ensure_utf8_universe(symbol)} added")
            
            if len(added) > 10:
                print(f"  • ... and {len(added) - 10} more")
            
            # Add all to database
            for symbol in added:
                symbol_utf8 = ensure_utf8_universe(symbol)
                
                # First check if this symbol exists but was previously removed
                cursor.execute('''
                    SELECT date_removed FROM universe_constituents
                    WHERE symbol = ? AND universe_name = ?
                    ORDER BY date_added DESC LIMIT 1
                ''', (symbol_utf8, universe_name))
                
                existing = cursor.fetchone()
                
                if existing and existing[0] is not None:
                    # Stock was removed, now being re-added
                    cursor.execute('''
                        UPDATE universe_constituents
                        SET date_removed = NULL, last_verified = ?
                        WHERE symbol = ? AND universe_name = ? AND date_removed IS NOT NULL
                    ''', (current_date, symbol_utf8, universe_name))
                else:
                    # New stock or already active
                    cursor.execute('''
                        INSERT OR IGNORE INTO universe_constituents
                        (symbol, universe_name, date_added, date_removed, last_verified, is_tradable_alpaca)
                        VALUES (?, ?, ?, NULL, ?, NULL)
                    ''', (symbol_utf8, universe_name, current_date, current_date))
                
                # Log change
                cursor.execute('''
                    INSERT OR IGNORE INTO change_log
                    (timestamp, date, universe_name, symbol, action, reason)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (int(datetime.now().timestamp()), current_date, universe_name,
                      symbol_utf8, 'ADDED', 'Added to index'))
        
        # Create daily snapshot with UTF-8 safe JSON
        tickers_utf8 = [ensure_utf8_universe(t) for t in tickers]
        tickers_json = sanitize_json_utf8(sorted(tickers_utf8))
        cursor.execute('''
            INSERT OR REPLACE INTO daily_snapshots
            (date, universe_name, tickers_json, ticker_count)
            VALUES (?, ?, ?, ?)
        ''', (current_date, universe_name, tickers_json, len(tickers_utf8)))
        
        # COMMIT before counting
        conn.commit()
        
        # Now count what's actually in the database
        cursor.execute('''
            SELECT COUNT(DISTINCT symbol)
            FROM universe_constituents
            WHERE universe_name = ? AND date_removed IS NULL
        ''', (universe_name,))
        db_active_count = cursor.fetchone()[0]
        
        conn.close()
        
        if not added and not removed:
            print(f"\n✅ No changes detected")
        
        print(f"\n📊 DATABASE STATISTICS:")
        print(f"  Fetched from source: {len(tickers)} stocks")
        print(f"  Active in database: {db_active_count} stocks")
        
        if db_active_count != len(tickers):
            print(f"  ⚠️  Mismatch: {abs(db_active_count - len(tickers))} stock difference")
        else:
            print(f"  ✅ Database matches source")
        
        print(f"\n✅ Updated {universe_name}: {len(tickers)} total constituents")
        print(f"{'='*70}\n")
        
        # Save CSV for inspection
        csv_path = self.universe_dir / f'{universe_name}_tickers.csv'
        pd.DataFrame({'Symbol': sorted(tickers_utf8)}).to_csv(csv_path, index=False, encoding='utf-8')
        print(f"💾 Saved to: {csv_path}")
    
    def _get_current_constituents(self, universe_name):
        """Get currently active constituents for a universe with UTF-8 safety"""
        universe_name = ensure_utf8_universe(universe_name)
        conn = get_utf8_connection_universe(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT DISTINCT symbol
            FROM universe_constituents
            WHERE universe_name = ? AND date_removed IS NULL
        ''', (universe_name,))
        
        rows = cursor.fetchall()
        tickers = [ensure_utf8_universe(row[0]) for row in rows]
        conn.close()
        
        return tickers
    
    # ============================================================
    # QUERY FUNCTIONS (for simulator integration) - UTF-8 SAFE
    # ============================================================
    
    def get_approved_tickers(self, universe_name, query_date=None):
        """Get approved tickers for a universe on a specific date with UTF-8 safety"""
        if query_date is None:
            query_date = date.today()
        
        universe_name = ensure_utf8_universe(universe_name)
        conn = get_utf8_connection_universe(self.db_path)
        cursor = conn.cursor()
        
        # Try to get from daily snapshot first
        cursor.execute('''
            SELECT tickers_json
            FROM daily_snapshots
            WHERE universe_name = ? AND date <= ?
            ORDER BY date DESC
            LIMIT 1
        ''', (universe_name, query_date))
        
        row = cursor.fetchone()
        if row:
            try:
                tickers = json.loads(row[0])
                tickers = [ensure_utf8_universe(t) for t in tickers]
                conn.close()
                return tickers
            except (json.JSONDecodeError, TypeError):
                pass
        
        # Fallback: query constituents table
        cursor.execute('''
            SELECT DISTINCT symbol
            FROM universe_constituents
            WHERE universe_name = ?
              AND date_added <= ?
              AND (date_removed IS NULL OR date_removed > ?)
        ''', (universe_name, query_date, query_date))
        
        rows = cursor.fetchall()
        tickers = [ensure_utf8_universe(row[0]) for row in rows]
        conn.close()
        
        return tickers
    
    def get_universe_info(self, universe_name):
        """Get summary info about a universe with UTF-8 safety"""
        universe_name = ensure_utf8_universe(universe_name)
        
        # Get current count
        current_tickers = self._get_current_constituents(universe_name)
        
        conn = get_utf8_connection_universe(self.db_path)
        cursor = conn.cursor()
        
        # Get last update date
        cursor.execute('''
            SELECT MAX(date)
            FROM daily_snapshots
            WHERE universe_name = ?
        ''', (universe_name,))
        
        last_update = cursor.fetchone()[0]
        
        # Get recent changes (last 30 days)
        cursor.execute('''
            SELECT COUNT(*)
            FROM change_log
            WHERE universe_name = ? AND date >= date('now', '-30 days')
        ''', (universe_name,))
        
        recent_changes = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'name': universe_name,
            'current_count': len(current_tickers),
            'last_update': last_update,
            'recent_changes': recent_changes,
            'tickers': current_tickers
        }
    
    def check_ticker(self, symbol, universe_name=None):
        """Check if a ticker is in one or more universes with UTF-8 safety"""
        symbol_utf8 = clean_ticker_utf8(symbol)
        
        conn = get_utf8_connection_universe(self.db_path)
        cursor = conn.cursor()
        
        if universe_name:
            # Clean universe name
            universe_name = ensure_utf8_universe(universe_name)
            
            # Check specific universe
            cursor.execute('''
                SELECT universe_name, date_added, date_removed, is_tradable_alpaca
                FROM universe_constituents
                WHERE symbol = ? AND universe_name = ?
                ORDER BY date_added DESC
                LIMIT 1
            ''', (symbol_utf8, universe_name))
        else:
            # Check all universes
            cursor.execute('''
                SELECT universe_name, date_added, date_removed, is_tradable_alpaca
                FROM universe_constituents
                WHERE symbol = ?
                ORDER BY date_added DESC
            ''', (symbol_utf8,))
        
        results = cursor.fetchall()
        conn.close()
        
        if not results:
            return {
                'symbol': symbol_utf8,
                'found': False,
                'universes': []
            }
        
        universes_info = []
        for row in results:
            univ_name, date_added, date_removed, tradable = row
            
            # Ensure UTF-8 for all string fields
            univ_name = ensure_utf8_universe(univ_name)
            status = 'ACTIVE' if date_removed is None else f'REMOVED on {date_removed}'
            
            universes_info.append({
                'universe': univ_name,
                'status': status,
                'date_added': date_added,
                'date_removed': date_removed,
                'is_tradable': tradable if tradable is not None else 'Not verified'
            })
        
        return {
            'symbol': symbol_utf8,
            'found': True,
            'universes': universes_info
        }
    
    def get_recent_changes(self, universe_name=None, days=30):
        """Get recent changes for a universe with UTF-8 safety"""
        conn = get_utf8_connection_universe(self.db_path)
        cursor = conn.cursor()
        
        if universe_name:
            universe_name = ensure_utf8_universe(universe_name)
            cursor.execute('''
                SELECT date, symbol, action, reason
                FROM change_log
                WHERE universe_name = ? AND date >= date('now', '-' || ? || ' days')
                ORDER BY timestamp DESC
            ''', (universe_name, days))
        else:
            cursor.execute('''
                SELECT universe_name, date, symbol, action, reason
                FROM change_log
                WHERE date >= date('now', '-' || ? || ' days')
                ORDER BY timestamp DESC
            ''', (days,))
        
        changes = cursor.fetchall()
        conn.close()
        
        # Ensure UTF-8 for all string fields in results
        sanitized_changes = []
        for change in changes:
            if universe_name:
                date_val, symbol, action, reason = change
                sanitized_changes.append((
                    date_val,
                    ensure_utf8_universe(symbol),
                    ensure_utf8_universe(action),
                    ensure_utf8_universe(reason) if reason else None
                ))
            else:
                univ_name, date_val, symbol, action, reason = change
                sanitized_changes.append((
                    ensure_utf8_universe(univ_name),
                    date_val,
                    ensure_utf8_universe(symbol),
                    ensure_utf8_universe(action),
                    ensure_utf8_universe(reason) if reason else None
                ))
        
        return sanitized_changes
    
    # ============================================================
    # UTILITY FUNCTIONS - UTF-8 SAFE
    # ============================================================
    
    def clear_universe(self, universe_name):
        """Clear all data for a specific universe with UTF-8 safety"""
        if universe_name == 'all':
            confirm = input("⚠️  Clear ALL universes? This cannot be undone! (yes/no): ")
            if confirm.lower() != 'yes':
                print("Cancelled.")
                return
            
            conn = get_utf8_connection_universe(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM universe_constituents')
            cursor.execute('DELETE FROM daily_snapshots')
            cursor.execute('DELETE FROM change_log')
            
            conn.commit()
            conn.close()
            
            print("✅ All universes cleared from database")
            return
        
        # Clear specific universe
        universe_name = ensure_utf8_universe(universe_name)
        
        print(f"\n{'='*70}")
        print(f"CLEARING {universe_name.upper()} UNIVERSE")
        print(f"{'='*70}")
        
        conn = get_utf8_connection_universe(self.db_path)
        cursor = conn.cursor()
        
        # Get count before deletion
        cursor.execute('''
            SELECT COUNT(*) FROM universe_constituents
            WHERE universe_name = ?
        ''', (universe_name,))
        count_before = cursor.fetchone()[0]
        
        # Delete all records for this universe
        cursor.execute('''
            DELETE FROM universe_constituents
            WHERE universe_name = ?
        ''', (universe_name,))
        
        cursor.execute('''
            DELETE FROM daily_snapshots
            WHERE universe_name = ?
        ''', (universe_name,))
        
        cursor.execute('''
            DELETE FROM change_log
            WHERE universe_name = ?
        ''', (universe_name,))
        
        conn.commit()
        conn.close()
        
        print(f"✅ Cleared {count_before} records for {universe_name}")
        print(f"{'='*70}\n")
    
    def vacuum_database(self):
        """Optimize database (reclaim space after deletions) with UTF-8 safety"""
        print("Optimizing database...")
        conn = get_utf8_connection_universe(self.db_path)
        conn.execute('VACUUM')
        conn.execute('ANALYZE')
        conn.close()
        print("✅ Database optimized")
    
    def verify_on_alpaca(self, symbols, batch_size=10):
        """Verify if symbols are tradable on Alpaca with UTF-8 safety"""
        if not self.api_key or not self.secret_key:
            print("⚠️  Alpaca API keys not provided, skipping verification")
            return {}
        
        # Clean all symbols first
        symbols = [clean_ticker_utf8(s) for s in symbols]
        symbols = [s for s in symbols if s]
        
        try:
            from alpaca.trading.client import TradingClient
            client = TradingClient(self.api_key, self.secret_key)
            
            print(f"\n🔍 Verifying {len(symbols)} symbols on Alpaca...")
            results = {}
            
            for i in range(0, len(symbols), batch_size):
                batch = symbols[i:i+batch_size]
                print(f"  Verifying... {min(i+batch_size, len(symbols))}/{len(symbols)}")
                
                for symbol in batch:
                    symbol_clean = clean_ticker_utf8(symbol)
                    try:
                        asset = client.get_asset(symbol_clean)
                        results[symbol_clean] = asset.tradable
                    except Exception:
                        results[symbol_clean] = False
            
            tradable_count = sum(1 for v in results.values() if v)
            print(f"\n✅ Verified: {tradable_count}/{len(symbols)} tradable on Alpaca")
            
            return results
            
        except Exception as e:
            print(f"❌ Error during Alpaca verification: {e}")
            return {}
    
    # ============================================================
    # DELEGATED FUNCTIONS (to helper modules)
    # ============================================================
    
    def print_status(self):
        """Delegate to reporter module"""
        return self.reporter.print_status()
    
    def print_ticker_info(self, symbol):
        """Delegate to reporter module with UTF-8 safety"""
        symbol_clean = clean_ticker_utf8(symbol)
        return self.reporter.print_ticker_info(symbol_clean)
    
    def diagnose_mismatch(self, universe_name):
        """Delegate to diagnostics module with UTF-8 safety"""
        universe_name = ensure_utf8_universe(universe_name)
        return self.diagnostics.diagnose_mismatch(universe_name)