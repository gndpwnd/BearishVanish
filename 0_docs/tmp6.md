"""
UTF-8 Safe Database Writing Functions for simulation_telemetry.py
Replace these functions in your simulation_telemetry.py file
"""

import json
import sqlite3
from datetime import datetime

# ============================================================
# UTF-8 SAFETY HELPER FUNCTIONS
# ============================================================

def ensure_utf8(text):
    """
    Ensure a string is valid UTF-8
    
    Args:
        text: Input string (can be str, bytes, or None)
    
    Returns:
        UTF-8 encoded string or None
    """
    if text is None:
        return None
    
    if isinstance(text, bytes):
        # Try to decode bytes
        try:
            return text.decode('utf-8', errors='replace')
        except:
            return text.decode('latin-1', errors='replace')
    
    if not isinstance(text, str):
        text = str(text)
    
    # Ensure string is valid UTF-8 by encoding and decoding
    try:
        # This will catch any encoding issues
        text.encode('utf-8')
        return text
    except UnicodeEncodeError:
        # Replace problematic characters
        return text.encode('utf-8', errors='replace').decode('utf-8')

def sanitize_json(data):
    """
    Sanitize data before JSON serialization to ensure UTF-8 compatibility
    
    Args:
        data: Dictionary or object to serialize
    
    Returns:
        JSON string with UTF-8 safe encoding
    """
    if data is None:
        return None
    
    try:
        # First attempt: normal serialization
        return json.dumps(data, ensure_ascii=False)
    except (TypeError, ValueError, UnicodeDecodeError):
        # Second attempt: sanitize the data
        if isinstance(data, dict):
            sanitized = {
                ensure_utf8(k): sanitize_value(v) 
                for k, v in data.items()
            }
        else:
            sanitized = sanitize_value(data)
        
        try:
            return json.dumps(sanitized, ensure_ascii=False)
        except:
            # Final fallback: ASCII-only encoding
            return json.dumps(sanitized, ensure_ascii=True)

def sanitize_value(value):
    """Recursively sanitize values for JSON"""
    if value is None:
        return None
    elif isinstance(value, (str, bytes)):
        return ensure_utf8(value)
    elif isinstance(value, dict):
        return {ensure_utf8(k): sanitize_value(v) for k, v in value.items()}
    elif isinstance(value, (list, tuple)):
        return [sanitize_value(v) for v in value]
    elif isinstance(value, (int, float, bool)):
        return value
    else:
        return ensure_utf8(str(value))

def get_utf8_connection(db_path):
    """
    Create SQLite connection with UTF-8 encoding
    
    Args:
        db_path: Path to database file
    
    Returns:
        sqlite3.Connection with UTF-8 settings
    """
    conn = sqlite3.connect(db_path)
    conn.text_factory = str  # Ensure strings are returned as str
    # Set UTF-8 encoding
    conn.execute("PRAGMA encoding = 'UTF-8'")
    return conn

# ============================================================
# UPDATED DATABASE FUNCTIONS (in SimulationTelemetry class)
# ============================================================

# Add this to your __init__ method:
def _init_database(self):
    """Initialize SQLite database with UTF-8 encoding"""
    conn = get_utf8_connection(self.db_path)
    cursor = conn.cursor()
    
    # Set UTF-8 as the default encoding
    cursor.execute("PRAGMA encoding = 'UTF-8'")
    
    # ... rest of your existing _init_database code ...
    # (keep all your existing CREATE TABLE statements)
    
    conn.commit()
    conn.close()

# Replace the record_simulation_start method:
def record_simulation_start(self, universe_name, symbols, start_date, end_date, 
                           initial_capital, config=None):
    """Record simulation metadata with UTF-8 safety"""
    conn = get_utf8_connection(self.db_path)
    cursor = conn.cursor()
    
    # Sanitize all string inputs
    universe_name = ensure_utf8(universe_name)
    sanitized_symbols = [ensure_utf8(s) for s in symbols]
    config_json = sanitize_json(config or {})
    
    cursor.execute('''
        INSERT INTO simulation_info 
        (simulation_id, start_time, universe_name, num_symbols,
         date_range_start, date_range_end, initial_capital, config_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        ensure_utf8(self.simulation_id),
        int(datetime.now().timestamp()),
        universe_name,
        len(sanitized_symbols),
        ensure_utf8(str(start_date)),
        ensure_utf8(str(end_date)),
        initial_capital,
        config_json
    ))
    
    conn.commit()
    conn.close()

# Replace the record_trade_attempt method:
def record_trade_attempt(self, strategy_name, symbol, signal, price, date,
                        portfolio_value, cash, num_positions, max_positions,
                        success, rejection_reason=None, volume=0, 
                        avg_volume_20d=0, relative_volume=1.0):
    """Record trade attempt with UTF-8 safety"""
    conn = get_utf8_connection(self.db_path)
    cursor = conn.cursor()
    
    timestamp = self._get_simulation_timestamp(date)
    
    # Sanitize all string inputs
    strategy_name = ensure_utf8(strategy_name)
    symbol = ensure_utf8(symbol)
    signal = ensure_utf8(signal)
    rejection_reason = ensure_utf8(rejection_reason) if rejection_reason else None
    
    cursor.execute('''
        INSERT INTO trade_attempts
        (timestamp, date, strategy_name, symbol, signal, price,
         volume, avg_volume_20d, relative_volume,
         portfolio_value, cash, num_positions, max_positions, 
         success, rejection_reason)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        timestamp,
        ensure_utf8(str(date)),
        strategy_name,
        symbol,
        signal,
        price,
        volume,
        avg_volume_20d,
        relative_volume,
        portfolio_value,
        cash,
        num_positions,
        max_positions,
        success,
        rejection_reason
    ))
    
    conn.commit()
    conn.close()

# Replace the record_trade_entry method:
def record_trade_entry(self, strategy_name, symbol, date, price, shares,
                      portfolio_value=None, cash=None, num_positions=None,
                      entry_reason=None, volume=0, avg_volume_20d=0, 
                      relative_volume=1.0):
    """Record trade entry with UTF-8 safety"""
    conn = get_utf8_connection(self.db_path)
    cursor = conn.cursor()
    
    timestamp = self._get_simulation_timestamp(date)
    
    # Sanitize all string inputs
    strategy_name = ensure_utf8(strategy_name)
    symbol = ensure_utf8(symbol)
    entry_reason = ensure_utf8(entry_reason) if entry_reason else None
    
    cursor.execute('''
        INSERT INTO trade_history
        (strategy_name, symbol, entry_timestamp, entry_date, entry_price, shares,
         entry_volume, entry_avg_volume_20d, entry_relative_volume,
         entry_portfolio_value, entry_cash, entry_num_positions, 
         trade_status, entry_reason)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'OPEN', ?)
    ''', (
        strategy_name, 
        symbol, 
        timestamp, 
        ensure_utf8(str(date)), 
        price, 
        shares,
        volume, 
        avg_volume_20d, 
        relative_volume,
        portfolio_value, 
        cash, 
        num_positions, 
        entry_reason
    ))
    
    conn.commit()
    conn.close()

# Replace the record_trade_exit method:
def record_trade_exit(self, strategy_name, symbol, exit_date, exit_price,
                     portfolio_value=None, cash=None, forced=False, reason=None,
                     volume=0, avg_volume_20d=0, relative_volume=1.0):
    """Record trade exit with UTF-8 safety"""
    conn = get_utf8_connection(self.db_path)
    cursor = conn.cursor()
    
    exit_timestamp = self._get_simulation_timestamp(exit_date)
    
    # Sanitize all string inputs
    strategy_name = ensure_utf8(strategy_name)
    symbol = ensure_utf8(symbol)
    reason = ensure_utf8(reason) if reason else None
    
    # Find most recent OPEN trade
    cursor.execute('''
        SELECT id, entry_timestamp, entry_date, entry_price, shares
        FROM trade_history
        WHERE strategy_name = ? AND symbol = ? AND trade_status = 'OPEN'
        ORDER BY entry_timestamp DESC
        LIMIT 1
    ''', (strategy_name, symbol))
    
    trade = cursor.fetchone()
    if not trade:
        conn.close()
        return
    
    trade_id, entry_timestamp, entry_date, entry_price, shares = trade
    
    # Calculate P&L
    profit_loss = (exit_price - entry_price) * shares
    profit_loss_pct = (exit_price - entry_price) / entry_price * 100
    holding_days = (exit_timestamp - entry_timestamp) / 86400.0
    holding_bars = int(holding_days)
    
    # Update trade
    cursor.execute('''
        UPDATE trade_history
        SET exit_timestamp = ?, exit_date = ?, exit_price = ?,
            exit_volume = ?, exit_avg_volume_20d = ?, exit_relative_volume = ?,
            exit_portfolio_value = ?, exit_cash = ?,
            profit_loss_dollars = ?, profit_loss_pct = ?,
            holding_days = ?, holding_bars = ?,
            trade_status = 'CLOSED',
            forced_exit = ?, exit_reason = ?
        WHERE id = ?
    ''', (
        exit_timestamp, 
        ensure_utf8(str(exit_date)), 
        exit_price,
        volume, 
        avg_volume_20d, 
        relative_volume,
        portfolio_value, 
        cash,
        profit_loss, 
        profit_loss_pct,
        holding_days, 
        holding_bars,
        forced, 
        reason, 
        trade_id
    ))
    
    conn.commit()
    conn.close()

# Replace the log_execution method:
def log_execution(self, strategy_name, symbol, date, bar_number, action, details=None):
    """Log execution with UTF-8 safety"""
    conn = get_utf8_connection(self.db_path)
    cursor = conn.cursor()
    
    timestamp = self._get_simulation_timestamp(date)
    
    # Sanitize strings
    strategy_name = ensure_utf8(strategy_name)
    symbol = ensure_utf8(symbol)
    action = ensure_utf8(action)
    
    # Sanitize details JSON
    details_json = sanitize_json(details) if details else None
    
    cursor.execute('''
        INSERT INTO execution_log
        (timestamp, date, bar_number, strategy_name, symbol, action, details)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (
        timestamp, 
        ensure_utf8(str(date)), 
        bar_number, 
        strategy_name, 
        symbol, 
        action,
        details_json
    ))
    
    conn.commit()
    conn.close()

# Replace the batch_insert_trade_attempts method:
def batch_insert_trade_attempts(self, attempts_list):
    """Batch insert trade attempts with UTF-8 safety"""
    if not attempts_list:
        return
    
    # Sanitize all string fields in each tuple
    sanitized_attempts = []
    for attempt in attempts_list:
        # Unpack tuple (15 elements)
        (timestamp, date_str, strategy_name, symbol, signal, price,
         volume, avg_volume_20d, relative_volume,
         portfolio_value, cash, num_positions, max_positions, 
         success, rejection_reason) = attempt
        
        # Sanitize strings
        sanitized = (
            timestamp,
            ensure_utf8(date_str),
            ensure_utf8(strategy_name),
            ensure_utf8(symbol),
            ensure_utf8(signal),
            price,
            volume,
            avg_volume_20d,
            relative_volume,
            portfolio_value,
            cash,
            num_positions,
            max_positions,
            success,
            ensure_utf8(rejection_reason) if rejection_reason else None
        )
        sanitized_attempts.append(sanitized)
    
    conn = get_utf8_connection(self.db_path)
    cursor = conn.cursor()
    
    cursor.executemany('''
        INSERT INTO trade_attempts
        (timestamp, date, strategy_name, symbol, signal, price,
         volume, avg_volume_20d, relative_volume,
         portfolio_value, cash, num_positions, max_positions, 
         success, rejection_reason)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', sanitized_attempts)
    
    conn.commit()
    conn.close()

# Replace the batch_insert_trade_entries method:
def batch_insert_trade_entries(self, entries_list):
    """Batch insert trade entries with UTF-8 safety"""
    if not entries_list:
        return
    
    # Sanitize all string fields
    sanitized_entries = []
    for entry in entries_list:
        # Unpack tuple (13 elements)
        (strategy_name, symbol, timestamp, date_str, price, shares,
         volume, avg_volume_20d, relative_volume,
         portfolio_value, cash, num_positions, entry_reason) = entry
        
        # Sanitize strings
        sanitized = (
            ensure_utf8(strategy_name),
            ensure_utf8(symbol),
            timestamp,
            ensure_utf8(date_str),
            price,
            shares,
            volume,
            avg_volume_20d,
            relative_volume,
            portfolio_value,
            cash,
            num_positions,
            ensure_utf8(entry_reason) if entry_reason else None
        )
        sanitized_entries.append(sanitized)
    
    conn = get_utf8_connection(self.db_path)
    cursor = conn.cursor()
    
    cursor.executemany('''
        INSERT INTO trade_history
        (strategy_name, symbol, entry_timestamp, entry_date, entry_price, shares,
        entry_volume, entry_avg_volume_20d, entry_relative_volume,
        entry_portfolio_value, entry_cash, entry_num_positions, 
        trade_status, entry_reason)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'OPEN', ?)
    ''', sanitized_entries)
    
    conn.commit()
    conn.close()

# Replace the finalize_strategy method (just the string handling parts):
def finalize_strategy(self, strategy_name, tracker=None, spy_returns=None, rejected_count=0):
    """Calculate and store final metrics with UTF-8 safety"""
    import numpy as np
    
    # Sanitize strategy name
    strategy_name = ensure_utf8(strategy_name)
    
    print(f"  📊 Finalizing {strategy_name}...")
    
    conn = get_utf8_connection(self.db_path)
    cursor = conn.cursor()
    
    # ... rest of your existing finalize_strategy code ...
    # Just make sure when inserting strategy_config_json, you use:
    
    # At the end where you INSERT OR REPLACE:
    cursor.execute('''
        INSERT OR REPLACE INTO strategy_performance
        (strategy_name, initial_capital, final_value, total_return_pct,
        total_profit_dollars, total_trades, completed_trades, open_positions,
        rejected_trades, win_rate_pct, winning_trades, losing_trades, profit_factor,
        sharpe_ratio, sortino_ratio, calmar_ratio, max_drawdown_pct,
        avg_win_dollars, avg_loss_dollars, avg_trade_duration_days,
        risk_reward_ratio, expectancy_dollars, exposure_time_pct,
        beta, alpha_pct, information_ratio,
        position_size_pct, max_positions, strategy_config_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        ensure_utf8(strategy_name),  # ← Add ensure_utf8 here
        initial_capital,
        final_value,
        total_return_pct,
        total_profit_dollars,
        total_trades,
        completed_trades,
        open_positions,
        rejected_count,
        win_rate,
        winning_trades,
        losing_trades,
        profit_factor,
        sharpe_ratio,
        sortino_ratio,
        calmar_ratio,
        max_drawdown_pct,
        avg_win,
        avg_loss,
        avg_holding_days,
        risk_reward_ratio,
        expectancy,
        exposure_time_pct,
        None,  # beta
        None,  # alpha
        None,  # information_ratio
        position_size_pct,
        max_positions,
        sanitize_json(strategy_config_json)  # ← Add sanitize_json here
    ))
    
    conn.commit()
    conn.close()




"""
UTF-8 Safe Database Writing Functions for stock_universe.py
Replace these functions in your stock_universe.py file
"""

import sqlite3
import json
import pandas as pd
import requests
from datetime import date
from io import StringIO

# ============================================================
# UTF-8 SAFETY HELPERS (add to top of file)
# ============================================================

def ensure_utf8_universe(text):
    """Ensure text is valid UTF-8 (same as telemetry version)"""
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
    """Clean ticker symbol and ensure UTF-8 compatibility"""
    if not ticker:
        return None
    
    # Ensure UTF-8
    ticker = ensure_utf8_universe(ticker)
    
    # Strip whitespace and convert to uppercase
    ticker = ticker.strip().upper()
    
    # Remove any non-ASCII characters that might have slipped through
    ticker = ''.join(c for c in ticker if ord(c) < 128)
    
    return ticker if ticker else None

# ============================================================
# UPDATED METHODS FOR UniverseManager CLASS
# ============================================================

# Replace the _init_database method:
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

# Replace the _fetch_sp500 method:
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
        raw_tickers = df['Symbol'].tolist()
        tickers = [clean_ticker_utf8(t) for t in raw_tickers]
        tickers = [t for t in tickers if t]  # Remove None values
        
        # Additional cleaning
        from ticker_validation import clean_tickers
        cleaned_tickers = clean_tickers(tickers)
        
        if len(cleaned_tickers) < len(tickers):
            print(f"  ℹ️  Filtered out {len(tickers) - len(cleaned_tickers)} invalid entries")
        
        print(f"  ✅ Fetched {len(cleaned_tickers)} S&P 500 tickers from Wikipedia")
        
        return cleaned_tickers, df
        
    except Exception as e:
        print(f"  ❌ Error fetching S&P 500: {e}")
        return None, None

# Replace the _fetch_nasdaq100 method:
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
        raw_tickers = df['Symbol'].tolist()
        tickers = [clean_ticker_utf8(t) for t in raw_tickers]
        tickers = [t for t in tickers if t]
        
        # Additional cleaning
        from ticker_validation import clean_tickers
        cleaned_tickers = clean_tickers(tickers)
        
        if len(cleaned_tickers) < len(tickers):
            print(f"  ℹ️  Filtered out {len(tickers) - len(cleaned_tickers)} invalid entries")
        
        print(f"  ✅ Fetched {len(cleaned_tickers)} NASDAQ 100 tickers from Slickcharts")
        
        return cleaned_tickers, df
        
    except Exception as e:
        print(f"  ❌ Error fetching NASDAQ 100: {e}")
        return None, None

# Replace the update_universe method (key parts):
def update_universe(self, universe_name):
    """Update universe with UTF-8 safety"""
    if universe_name == 'all':
        for name in ['sp500', 'nasdaq100', 'russell3000']:
            self.update_universe(name)
        return
    
    print(f"\n{'='*70}")
    print(f"UPDATING {universe_name.upper()} UNIVERSE")
    print(f"{'='*70}")
    
    # Fetch current tickers (already UTF-8 safe from updated fetch methods)
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
        sample_removed = list(removed)[:10]
        for symbol in sample_removed:
            print(f"  • {ensure_utf8_universe(symbol)} removed")
        
        if len(removed) > 10:
            print(f"  • ... and {len(removed) - 10} more")
        
        for symbol in removed:
            # Ensure UTF-8 before writing
            symbol_utf8 = ensure_utf8_universe(symbol)
            universe_utf8 = ensure_utf8_universe(universe_name)
            
            cursor.execute('''
                UPDATE universe_constituents
                SET date_removed = ?
                WHERE symbol = ? AND universe_name = ? AND date_removed IS NULL
            ''', (current_date, symbol_utf8, universe_utf8))
            
            # Log change
            cursor.execute('''
                INSERT OR IGNORE INTO change_log 
                (timestamp, date, universe_name, symbol, action, reason)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                int(datetime.now().timestamp()), 
                current_date, 
                universe_utf8, 
                symbol_utf8, 
                'REMOVED', 
                'Removed from index'
            ))
    
    # Add new stocks
    if added:
        print(f"\n📈 ADDITIONS DETECTED: {len(added)} stocks")
        sample_added = list(added)[:10]
        for symbol in sample_added:
            print(f"  • {ensure_utf8_universe(symbol)} added")
        
        if len(added) > 10:
            print(f"  • ... and {len(added) - 10} more")
        
        for symbol in added:
            # Ensure UTF-8 before writing
            symbol_utf8 = ensure_utf8_universe(symbol)
            universe_utf8 = ensure_utf8_universe(universe_name)
            
            # Check if exists but was removed
            cursor.execute('''
                SELECT date_removed FROM universe_constituents
                WHERE symbol = ? AND universe_name = ?
                ORDER BY date_added DESC LIMIT 1
            ''', (symbol_utf8, universe_utf8))
            
            existing = cursor.fetchone()
            
            if existing and existing[0] is not None:
                # Re-add previously removed stock
                cursor.execute('''
                    UPDATE universe_constituents
                    SET date_removed = NULL, last_verified = ?
                    WHERE symbol = ? AND universe_name = ? AND date_removed IS NOT NULL
                ''', (current_date, symbol_utf8, universe_utf8))
            else:
                # New stock
                cursor.execute('''
                    INSERT OR IGNORE INTO universe_constituents
                    (symbol, universe_name, date_added, date_removed, last_verified, is_tradable_alpaca)
                    VALUES (?, ?, ?, NULL, ?, NULL)
                ''', (symbol_utf8, universe_utf8, current_date, current_date))
            
            # Log change
            cursor.execute('''
                INSERT OR IGNORE INTO change_log
                (timestamp, date, universe_name, symbol, action, reason)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                int(datetime.now().timestamp()), 
                current_date, 
                universe_utf8,
                symbol_utf8, 
                'ADDED', 
                'Added to index'
            ))
    
    # Create daily snapshot with UTF-8 safe JSON
    tickers_utf8 = [ensure_utf8_universe(t) for t in tickers]
    tickers_json = json.dumps(sorted(tickers_utf8), ensure_ascii=False)
    universe_utf8 = ensure_utf8_universe(universe_name)
    
    cursor.execute('''
        INSERT OR REPLACE INTO daily_snapshots
        (date, universe_name, tickers_json, ticker_count)
        VALUES (?, ?, ?, ?)
    ''', (current_date, universe_utf8, tickers_json, len(tickers_utf8)))
    
    conn.commit()
    
    # Count active symbols
    cursor.execute('''
        SELECT COUNT(DISTINCT symbol)
        FROM universe_constituents
        WHERE universe_name = ? AND date_removed IS NULL
    ''', (universe_utf8,))
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

# Replace the _get_current_constituents method:
def _get_current_constituents(self, universe_name):
    """Get currently active constituents with UTF-8 safety"""
    conn = get_utf8_connection_universe(self.db_path)
    cursor = conn.cursor()
    
    universe_utf8 = ensure_utf8_universe(universe_name)
    
    cursor.execute('''
        SELECT DISTINCT symbol
        FROM universe_constituents
        WHERE universe_name = ? AND date_removed IS NULL
    ''', (universe_utf8,))
    
    tickers = [ensure_utf8_universe(row[0]) for row in cursor.fetchall()]
    conn.close()
    
    return tickers

# Replace the get_approved_tickers method:
def get_approved_tickers(self, universe_name, query_date=None):
    """Get approved tickers with UTF-8 safety"""
    if query_date is None:
        query_date = date.today()
    
    conn = get_utf8_connection_universe(self.db_path)
    cursor = conn.cursor()
    
    universe_utf8 = ensure_utf8_universe(universe_name)
    
    # Try daily snapshot first
    cursor.execute('''
        SELECT tickers_json
        FROM daily_snapshots
        WHERE universe_name = ? AND date <= ?
        ORDER BY date DESC
        LIMIT 1
    ''', (universe_utf8, query_date))
    
    row = cursor.fetchone()
    if row:
        # Parse JSON with UTF-8 safety
        try:
            tickers = json.loads(row[0])
            tickers = [ensure_utf8_universe(t) for t in tickers]
            conn.close()
            return tickers
        except (json.JSONDecodeError, TypeError):
            # Fall through to fallback query
            pass
    
    # Fallback query
    cursor.execute('''
        SELECT DISTINCT symbol
        FROM universe_constituents
        WHERE universe_name = ?
          AND date_added <= ?
          AND (date_removed IS NULL OR date_removed > ?)
    ''', (universe_utf8, query_date, query_date))
    
    tickers = [ensure_utf8_universe(row[0]) for row in cursor.fetchall()]
    conn.close()
    
    return tickers

# Replace the check_ticker method:
def check_ticker(self, symbol, universe_name=None):
    """Check ticker with UTF-8 safety"""
    symbol_utf8 = ensure_utf8_universe(symbol.upper())
    
    conn = get_utf8_connection_universe(self.db_path)
    cursor = conn.cursor()
    
    if universe_name:
        universe_utf8 = ensure_utf8_universe(universe_name)
        cursor.execute('''
            SELECT universe_name, date_added, date_removed, is_tradable_alpaca
            FROM universe_constituents
            WHERE symbol = ? AND universe_name = ?
            ORDER BY date_added DESC
            LIMIT 1
        ''', (symbol_utf8, universe_utf8))
    else:
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
        
        status = 'ACTIVE' if date_removed is None else f'REMOVED on {date_removed}'
        
        universes_info.append({
            'universe': ensure_utf8_universe(univ_name),
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


"""
UTF-8 Safe Database Writing Functions for data_manager.py
Replace these functions in your data_manager.py file
"""

import sqlite3
import pandas as pd
from datetime import datetime

# ============================================================
# UTF-8 SAFETY HELPERS (add to top of file)
# ============================================================

def ensure_utf8_data(text):
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

def get_utf8_connection_data(db_path, timeout=30.0):
    """Create SQLite connection with UTF-8 encoding"""
    conn = sqlite3.connect(db_path, timeout=timeout)
    conn.text_factory = str
    conn.execute("PRAGMA encoding = 'UTF-8'")
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA synchronous=NORMAL')
    conn.execute('PRAGMA cache_size=10000')
    conn.execute('PRAGMA temp_store=MEMORY')
    return conn

def clean_symbol_utf8(symbol):
    """Clean symbol and ensure UTF-8/ASCII compatibility"""
    if not symbol:
        return None
    
    # Ensure UTF-8
    symbol = ensure_utf8_data(symbol)
    
    # Strip and uppercase
    symbol = symbol.strip().upper()
    
    # Remove any non-ASCII characters (symbols should be ASCII)
    symbol = ''.join(c for c in symbol if ord(c) < 128)
    
    return symbol if symbol else None

# ============================================================
# UPDATED METHODS FOR DataManager CLASS
# ============================================================

# Replace the _init_database method:
def _init_database(self):
    """Initialize SQLite database with UTF-8 encoding"""
    conn = get_utf8_connection_data(self.db_path)
    
    # Enable WAL mode for better concurrency
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA synchronous=NORMAL')
    
    # Set UTF-8 encoding
    conn.execute("PRAGMA encoding = 'UTF-8'")
    
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

# Replace the _get_connection method:
def _get_connection(self):
    """Get a connection from pool with UTF-8 encoding"""
    with self._connection_lock:
        if self._connection_pool:
            return self._connection_pool.pop()
        else:
            conn = get_utf8_connection_data(self.db_path)
            return conn

# Replace the load_multiple_symbols_batch method:
def load_multiple_symbols_batch(self, symbols, start_date=None, end_date=None):
    """
    🚀 FAST: Load multiple symbols with UTF-8 safety
    """
    if not symbols:
        return {}
    
    # Clean all symbols
    symbols = [clean_symbol_utf8(s) for s in symbols]
    symbols = [s for s in symbols if s]  # Remove None values
    
    if not symbols:
        return {}
    
    conn = self._get_connection()
    
    try:
        # Build query
        query = 'SELECT symbol, timestamp, open, high, low, close, volume, trade_count, vwap FROM stock_bars WHERE symbol IN ('
        query += ','.join('?' * len(symbols))
        query += ')'
        
        params = symbols.copy()
        
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
        if not self.quiet and len(symbols) > 10:
            from tqdm import tqdm
            symbol_iterator = tqdm(symbols, desc="Processing symbols", unit="sym", 
                                bar_format='{desc}: {percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt}')
        else:
            symbol_iterator = symbols
        
        for symbol in symbol_iterator:
            # Ensure symbol is UTF-8 clean for comparison
            symbol_clean = clean_symbol_utf8(symbol)
            df_symbol = df_all[df_all['symbol'] == symbol_clean].copy()
            
            if not df_symbol.empty:
                df_symbol.set_index('timestamp', inplace=True)
                df_symbol.drop('symbol', axis=1, inplace=True)
                result[symbol_clean] = df_symbol
        
        return result
        
    except Exception as e:
        print(f"❌ Batch load error: {e}")
        self._return_connection(conn)
        return {}

# Replace the load_offline_data method:
def load_offline_data(self, symbol, start_date=None, end_date=None):
    """Load cached data with UTF-8 safety"""
    try:
        # Clean symbol
        symbol = clean_symbol_utf8(symbol)
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

# Replace the save_offline_data method:
def save_offline_data(self, symbol, df):
    """Save data with UTF-8 safety"""
    try:
        # Clean symbol
        symbol = clean_symbol_utf8(symbol)
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

# Replace the _update_metadata method:
def _update_metadata(self, symbol, conn):
    """Update metadata with UTF-8 safety"""
    # Clean symbol
    symbol = clean_symbol_utf8(symbol)
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

# Replace the get_data_range method:
def get_data_range(self, symbol):
    """Get data range with UTF-8 safety"""
    try:
        # Clean symbol
        symbol = clean_symbol_utf8(symbol)
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

# Replace the get_stock_data method (just the symbol cleaning part):
def get_stock_data(self, symbol, days=180):
    """Main method to get stock data with UTF-8 safety"""
    try:
        # Clean symbol
        symbol = clean_symbol_utf8(symbol)
        if not symbol:
            print(f"❌ Invalid symbol provided")
            return None
        
        end_date = datetime.now().replace(tzinfo=None)
        start_date = (end_date - timedelta(days=days)).replace(tzinfo=None)
        
        # ... rest of your existing get_stock_data code ...
        # (keep all existing logic, just ensure symbol is already cleaned)
        
    except Exception as e:
        print(f"❌ Unexpected error for {symbol}: {e}")
        return None

# Replace the list_cached_symbols method:
def list_cached_symbols(self):
    """List all symbols with UTF-8 safety"""
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
            symbol = ensure_utf8_data(row[0])
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