"""
Enhanced Simulation Telemetry with Complete Trade Recording AND BATCH OPTIMIZATION
WITH UTF-8 SAFETY FOR ALL DATABASE WRITES
FIXES: Missing timestamps, rejected trades, trade attempts, and context data
USES SIMULATION TIMESTAMPS to prevent look-ahead bias
ADDED: Batch insert methods for 5-10x speedup
ADDED: Volume tracking for all trades
FIXED: Indentation errors in record methods
ADDED: UTF-8 encoding safety for all database operations
"""

import sqlite3
import json
import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path
import hashlib
import time

# Import shared UTF-8 utilities
from utilities.utf8_helpers import ensure_utf8, sanitize_json, get_utf8_connection

TELEMETRY_ROOT = Path('./simulations')

class SimulationTelemetry:
    """
    Enhanced telemetry system with complete trade recording and UTF-8 safety
    All timestamps use simulation time (not real-world time) to prevent look-ahead bias
    """
    
    def __init__(self, simulation_name=None):
        """Initialize telemetry for a new simulation"""
        TELEMETRY_ROOT.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        if simulation_name:
            safe_name = "".join(c for c in simulation_name if c.isalnum() or c in ('-', '_'))
            db_name = f"simulation_{timestamp}_{safe_name}.db"
        else:
            hash_suffix = hashlib.md5(str(datetime.now().timestamp()).encode()).hexdigest()[:8]
            db_name = f"simulation_{timestamp}_{hash_suffix}.db"
        
        self.db_path = TELEMETRY_ROOT / db_name
        self.simulation_id = db_name.replace('.db', '')
        
        print(f"\n📊 Creating simulation database: {db_name}")
        self._init_database()
    
    def _init_database(self):
        """Create enhanced database schema with volume tracking and UTF-8 encoding"""
        conn = get_utf8_connection(self.db_path)
        cursor = conn.cursor()
        
        # Set UTF-8 encoding explicitly
        cursor.execute("PRAGMA encoding = 'UTF-8'")
        
        # Table 1: Simulation metadata
        cursor.execute('''
            CREATE TABLE simulation_info (
                id INTEGER PRIMARY KEY,
                simulation_id TEXT UNIQUE NOT NULL,
                start_time INTEGER NOT NULL,
                end_time INTEGER,
                universe_name TEXT,
                num_symbols INTEGER,
                date_range_start TEXT,
                date_range_end TEXT,
                initial_capital REAL,
                config_json TEXT
            )
        ''')
        
        # Table 2: Strategy performance WITH CONFIGURATION
        cursor.execute('''
            CREATE TABLE strategy_performance (
                strategy_name TEXT PRIMARY KEY,
                initial_capital REAL,
                final_value REAL,
                total_return_pct REAL,
                total_profit_dollars REAL,
                total_trades INTEGER,
                completed_trades INTEGER,
                open_positions INTEGER,
                rejected_trades INTEGER,
                win_rate_pct REAL,
                winning_trades INTEGER,
                losing_trades INTEGER,
                profit_factor REAL,
                sharpe_ratio REAL,
                sortino_ratio REAL,
                calmar_ratio REAL,
                max_drawdown_pct REAL,
                avg_win_dollars REAL,
                avg_loss_dollars REAL,
                avg_trade_duration_days REAL,
                risk_reward_ratio REAL,
                expectancy_dollars REAL,
                exposure_time_pct REAL,
                beta REAL,
                alpha_pct REAL,
                information_ratio REAL,
                position_size_pct REAL,
                max_positions INTEGER,
                strategy_config_json TEXT
            )
        ''')
        
        # Table 3: ENHANCED Trade history with volume tracking
        cursor.execute('''
            CREATE TABLE trade_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                strategy_name TEXT NOT NULL,
                symbol TEXT NOT NULL,
                entry_timestamp INTEGER NOT NULL,
                entry_date TEXT NOT NULL,
                entry_price REAL NOT NULL,
                shares REAL NOT NULL,
                
                -- Volume at entry
                entry_volume INTEGER,
                entry_avg_volume_20d REAL,
                entry_relative_volume REAL,
                
                entry_portfolio_value REAL,
                entry_cash REAL,
                entry_num_positions INTEGER,
                exit_timestamp INTEGER,
                exit_date TEXT,
                exit_price REAL,
                
                -- Volume at exit
                exit_volume INTEGER,
                exit_avg_volume_20d REAL,
                exit_relative_volume REAL,
                
                exit_portfolio_value REAL,
                exit_cash REAL,
                profit_loss_dollars REAL,
                profit_loss_pct REAL,
                holding_days REAL,
                holding_bars INTEGER,
                trade_status TEXT NOT NULL,
                forced_exit BOOLEAN,
                exit_reason TEXT,
                entry_reason TEXT
            )
        ''')
        
        # Table 4: Trade attempts with volume
        cursor.execute('''
            CREATE TABLE trade_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp INTEGER NOT NULL,
                date TEXT NOT NULL,
                strategy_name TEXT NOT NULL,
                symbol TEXT NOT NULL,
                signal TEXT NOT NULL,
                price REAL NOT NULL,
                
                -- Volume metrics
                volume INTEGER,
                avg_volume_20d REAL,
                relative_volume REAL,
                
                portfolio_value REAL,
                cash REAL,
                num_positions INTEGER,
                max_positions INTEGER,
                success BOOLEAN NOT NULL,
                rejection_reason TEXT
            )
        ''')
        
        # Table 5: Portfolio history with timestamps
        cursor.execute('''
            CREATE TABLE portfolio_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp INTEGER NOT NULL,
                strategy_name TEXT NOT NULL,
                date TEXT NOT NULL,
                portfolio_value REAL NOT NULL,
                cash REAL,
                positions_value REAL,
                num_positions INTEGER,
                daily_return_pct REAL
            )
        ''')
        
        # Table 6: Per-stock performance
        cursor.execute('''
            CREATE TABLE stock_performance (
                strategy_name TEXT NOT NULL,
                symbol TEXT NOT NULL,
                total_trades INTEGER,
                winning_trades INTEGER,
                losing_trades INTEGER,
                net_profit_loss REAL,
                win_rate_pct REAL,
                PRIMARY KEY (strategy_name, symbol)
            )
        ''')
        
        # Table 7: Bar-by-bar execution log
        cursor.execute('''
            CREATE TABLE execution_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp INTEGER NOT NULL,
                date TEXT NOT NULL,
                bar_number INTEGER NOT NULL,
                strategy_name TEXT NOT NULL,
                symbol TEXT NOT NULL,
                action TEXT NOT NULL,
                details TEXT
            )
        ''')
        
        # Table 8: Strategy configurations
        cursor.execute('''
            CREATE TABLE strategy_configs (
                strategy_name TEXT PRIMARY KEY,
                initial_capital REAL,
                position_size_pct REAL,
                max_positions INTEGER,
                color TEXT,
                parameters_json TEXT,
                created_timestamp INTEGER
            )
        ''')
        
        # Table 9: Indicator history for debugging
        cursor.execute('''
            CREATE TABLE indicator_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp INTEGER NOT NULL,
                date TEXT NOT NULL,
                strategy_name TEXT NOT NULL,
                symbol TEXT NOT NULL,
                indicator_name TEXT NOT NULL,
                indicator_value REAL,
                indicator_params TEXT
            )
        ''')
        
        # Indexes for performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_trades_strategy ON trade_history(strategy_name, trade_status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trade_history(symbol)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_trades_entry_ts ON trade_history(entry_timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_trades_volume ON trade_history(entry_relative_volume, exit_relative_volume)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_portfolio_strategy ON portfolio_history(strategy_name, timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_attempts_strategy ON trade_attempts(strategy_name, success)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_attempts_volume ON trade_attempts(relative_volume, success)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_execution_strategy ON execution_log(strategy_name, timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_indicator_history ON indicator_history(strategy_name, symbol, indicator_name)')
        
        # Additional performance indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_trade_history_strategy ON trade_history(strategy_name, trade_status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_trade_attempts_strategy ON trade_attempts(strategy_name, success)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_portfolio_strategy_time ON portfolio_history(strategy_name, timestamp)')
        
        conn.commit()
        conn.close()

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
    
    def _get_simulation_timestamp(self, date):
        """
        Convert simulation date to timestamp consistently
        Ensures NO look-ahead bias by using simulation time only
        """
        if isinstance(date, str):
            date_obj = pd.to_datetime(date)
            return int(date_obj.timestamp())
        elif hasattr(date, 'timestamp'):
            return int(date.timestamp())
        elif isinstance(date, (pd.Timestamp, np.datetime64)):
            return int(pd.to_datetime(date).timestamp())
        else:
            # Try to convert using pandas as last resort
            try:
                return int(pd.to_datetime(date).timestamp())
            except Exception as e:
                raise ValueError(f"Cannot convert {type(date)} to timestamp: {date} - Error: {e}")
            
    def record_trade_attempt(self, strategy_name, symbol, signal, price, date,
                            portfolio_value, cash, num_positions, max_positions,
                            success, rejection_reason=None, volume=0, avg_volume_20d=0, relative_volume=1.0):
        """
        Record EVERY trade attempt, including rejections WITH VOLUME and UTF-8 safety
        Uses SIMULATION TIME, not real-world time
        """
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

    def record_trade_entry(self, strategy_name, symbol, date, price, shares,
                          portfolio_value=None, cash=None, num_positions=None,
                          entry_reason=None, volume=0, avg_volume_20d=0, relative_volume=1.0):
        """
        Record BUY trade with volume data and UTF-8 safety
        Uses SIMULATION TIME, not real-world time
        """
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
            strategy_name, symbol, timestamp, ensure_utf8(str(date)), price, shares,
            volume, avg_volume_20d, relative_volume,
            portfolio_value, cash, num_positions, entry_reason
        ))
        
        conn.commit()
        conn.close()

    def record_trade_exit(self, strategy_name, symbol, exit_date, exit_price,
                         portfolio_value=None, cash=None, forced=False, reason=None,
                         volume=0, avg_volume_20d=0, relative_volume=1.0):
        """
        Record SELL trade with volume data and UTF-8 safety
        Uses SIMULATION TIME, not real-world time
        """
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
            exit_timestamp, ensure_utf8(str(exit_date)), exit_price,
            volume, avg_volume_20d, relative_volume,
            portfolio_value, cash,
            profit_loss, profit_loss_pct,
            holding_days, holding_bars,
            forced, reason, trade_id
        ))
        
        conn.commit()
        conn.close()

    def record_daily_snapshot(self, strategy_name, date, portfolio_value,
                             cash, positions_value, num_positions, daily_return=None):
        """Record daily portfolio state with SIMULATION timestamp and UTF-8 safety"""
        conn = get_utf8_connection(self.db_path)
        cursor = conn.cursor()
        
        timestamp = self._get_simulation_timestamp(date)
        
        # Sanitize string inputs
        strategy_name = ensure_utf8(strategy_name)
        
        cursor.execute('''
            INSERT INTO portfolio_history
            (timestamp, strategy_name, date, portfolio_value, cash, positions_value,
             num_positions, daily_return_pct)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (timestamp, strategy_name, ensure_utf8(str(date)), portfolio_value, cash, positions_value,
              num_positions, daily_return))
        
        conn.commit()
        conn.close()

    def log_execution(self, strategy_name, symbol, date, bar_number, action, details=None):
        """
        Log bar-by-bar execution for debugging with UTF-8 safety
        Uses SIMULATION TIME, not real-world time
        """
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
        ''', (timestamp, ensure_utf8(str(date)), bar_number, strategy_name, symbol, action,
              details_json))
        
        conn.commit()
        conn.close()

    def finalize_strategy(self, strategy_name, tracker=None, spy_returns=None, rejected_count=0):
        """Calculate and store final metrics - DATABASE ONLY VERSION with UTF-8 safety"""
        import numpy as np
        import json
        import sqlite3
        import time
        
        # Sanitize strategy name
        strategy_name = ensure_utf8(strategy_name)
        
        print(f"  📊 Finalizing {strategy_name}...")
        print(f"    Using database: {self.db_path}")
        
        conn = get_utf8_connection(self.db_path)
        cursor = conn.cursor()
        
        # ========================================================
        # 1. GET ALL TRADE STATS FROM DATABASE - WITH DEBUG
        # ========================================================
        cursor.execute('''
            SELECT 
                COUNT(*) as total_trades,
                SUM(CASE WHEN trade_status = 'CLOSED' THEN 1 ELSE 0 END) as completed_trades,
                SUM(CASE WHEN trade_status = 'OPEN' THEN 1 ELSE 0 END) as open_positions,
                SUM(CASE WHEN trade_status = 'CLOSED' AND profit_loss_dollars > 0 THEN 1 ELSE 0 END) as winning_trades,
                SUM(CASE WHEN trade_status = 'CLOSED' AND profit_loss_dollars < 0 THEN 1 ELSE 0 END) as losing_trades,
                SUM(CASE WHEN trade_status = 'CLOSED' AND profit_loss_dollars > 0 THEN profit_loss_dollars ELSE 0 END) as gross_profit,
                ABS(SUM(CASE WHEN trade_status = 'CLOSED' AND profit_loss_dollars < 0 THEN profit_loss_dollars ELSE 0 END)) as gross_loss,
                AVG(CASE WHEN trade_status = 'CLOSED' AND profit_loss_dollars > 0 THEN profit_loss_dollars END) as avg_win,
                AVG(CASE WHEN trade_status = 'CLOSED' AND profit_loss_dollars < 0 THEN profit_loss_dollars END) as avg_loss,
                AVG(CASE WHEN trade_status = 'CLOSED' THEN holding_days END) as avg_holding_days
            FROM trade_history
            WHERE strategy_name = ?
        ''', (strategy_name,))
        
        stats = cursor.fetchone()
        
        total_trades = stats[0] or 0
        completed_trades = stats[1] or 0
        open_positions = stats[2] or 0
        winning_trades = stats[3] or 0
        losing_trades = stats[4] or 0
        gross_profit = stats[5] or 0
        gross_loss = stats[6] or 0
        avg_win = stats[7] or 0
        avg_loss = stats[8] or 0
        avg_holding_days = stats[9] or 0
        
        # DEBUG: Show trade stats
        print(f"    Found in database:")
        print(f"      Total trades: {total_trades:,}")
        print(f"      Completed trades: {completed_trades:,}")
        print(f"      Open positions: {open_positions:,}")
        print(f"      Winning trades: {winning_trades:,}")
        print(f"      Losing trades: {losing_trades:,}")
        
        # Check for trade attempts in database
        cursor.execute('''
            SELECT COUNT(*), SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END)
            FROM trade_attempts
            WHERE strategy_name = ?
        ''', (strategy_name,))
        
        attempts_stats = cursor.fetchone()
        total_attempts = attempts_stats[0] or 0
        successful_attempts = attempts_stats[1] or 0
        
        print(f"    Trade attempts: {total_attempts:,} (successful: {successful_attempts:,})")
        
        # ========================================================
        # 2. CALCULATE DERIVED METRICS
        # ========================================================
        win_rate = (winning_trades / completed_trades * 100) if completed_trades > 0 else 0
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else 0
        risk_reward_ratio = abs(avg_win / avg_loss) if avg_loss != 0 else 0
        expectancy = (win_rate/100 * avg_win) + ((1 - win_rate/100) * avg_loss)
        
        print(f"    Calculated metrics:")
        print(f"      Win rate: {win_rate:.1f}%")
        print(f"      Profit factor: {profit_factor:.2f}")
        
        # ========================================================
        # 3. GET PORTFOLIO METRICS FROM DATABASE
        # ========================================================
        cursor.execute('''
            SELECT 
                MIN(portfolio_value) as min_value,
                MAX(portfolio_value) as max_value,
                portfolio_value as final_value,
                cash as final_cash
            FROM portfolio_history
            WHERE strategy_name = ?
            ORDER BY timestamp DESC
            LIMIT 1
        ''', (strategy_name,))
        
        portfolio_stats = cursor.fetchone()
        
        if portfolio_stats:
            min_value = portfolio_stats[0] or 0
            max_value = portfolio_stats[1] or 0
            final_value = portfolio_stats[2] or 100000
            final_cash = portfolio_stats[3] or 100000
        else:
            min_value = max_value = final_value = final_cash = 100000
            print(f"    ⚠️  No portfolio history found for {strategy_name}")
        
        # Get initial capital from first portfolio snapshot
        cursor.execute('''
            SELECT portfolio_value
            FROM portfolio_history
            WHERE strategy_name = ?
            ORDER BY timestamp ASC
            LIMIT 1
        ''', (strategy_name,))
        
        initial_result = cursor.fetchone()
        initial_capital = initial_result[0] if initial_result else 100000
        
        # Calculate returns
        total_return_pct = ((final_value - initial_capital) / initial_capital * 100) if initial_capital > 0 else 0
        total_profit_dollars = final_value - initial_capital
        
        print(f"    Portfolio:")
        print(f"      Initial: ${initial_capital:,.2f}")
        print(f"      Final: ${final_value:,.2f}")
        print(f"      Return: {total_return_pct:.2f}%")
        
        # ========================================================
        # 4. CALCULATE RISK METRICS FROM PORTFOLIO HISTORY
        # ========================================================
        cursor.execute('''
            SELECT daily_return_pct
            FROM portfolio_history
            WHERE strategy_name = ? AND daily_return_pct IS NOT NULL
            ORDER BY timestamp
        ''', (strategy_name,))
        
        returns = [row[0] for row in cursor.fetchall()]
        sharpe_ratio = 0
        sortino_ratio = 0
        
        if len(returns) > 2:
            returns_arr = np.array(returns)
            if returns_arr.std() > 0:
                sharpe_ratio = (returns_arr.mean() / returns_arr.std()) * np.sqrt(252 * 6.5)
            
            downside_returns = returns_arr[returns_arr < 0]
            if len(downside_returns) > 0 and downside_returns.std() > 0:
                sortino_ratio = (returns_arr.mean() / downside_returns.std()) * np.sqrt(252 * 6.5)
        
        # Calculate max drawdown from portfolio values
        cursor.execute('''
            SELECT portfolio_value
            FROM portfolio_history
            WHERE strategy_name = ?
            ORDER BY timestamp
        ''', (strategy_name,))
        
        values = [row[0] for row in cursor.fetchall()]
        max_drawdown_pct = 0
        
        if len(values) > 0:
            peak = values[0]
            for value in values:
                if value > peak:
                    peak = value
                dd = (peak - value) / peak * 100
                if dd > max_drawdown_pct:
                    max_drawdown_pct = dd
        
        # Calculate Calmar ratio
        calmar_ratio = 0
        if max_drawdown_pct > 0:
            annual_return = total_return_pct * 2  # Approximate annual from 6 months
            calmar_ratio = annual_return / max_drawdown_pct
        
        # ========================================================
        # 5. GET STRATEGY CONFIGURATION
        # ========================================================
        cursor.execute('''
            SELECT position_size_pct, max_positions, parameters_json
            FROM strategy_configs
            WHERE strategy_name = ?
        ''', (strategy_name,))
        
        config_row = cursor.fetchone()
        position_size_pct = config_row[0] if config_row else 0.10
        max_positions = config_row[1] if config_row else 10
        strategy_config_json = config_row[2] if config_row else '{}'
        
        # Calculate exposure time
        cursor.execute('''
            SELECT 
                COUNT(CASE WHEN num_positions > 0 THEN 1 END) * 100.0 / COUNT(*)
            FROM portfolio_history
            WHERE strategy_name = ?
        ''', (strategy_name,))
        
        exposure_result = cursor.fetchone()
        exposure_time_pct = exposure_result[0] if exposure_result else 0
        
        # ========================================================
        # 6. INSERT PERFORMANCE RECORD WITH UTF-8 SAFETY
        # ========================================================
        try:
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
                ensure_utf8(strategy_name),
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
                sanitize_json(strategy_config_json)
            ))
            
            conn.commit()
            print(f"    ✅ Successfully updated strategy_performance")
            
            # Verify the update
            cursor.execute('''
                SELECT total_trades, total_return_pct 
                FROM strategy_performance 
                WHERE strategy_name = ?
            ''', (strategy_name,))
            
            result = cursor.fetchone()
            if result:
                print(f"    ✅ Confirmed: total_trades={result[0]}, return={result[1]:.2f}%")
            
        except Exception as e:
            print(f"    ❌ Error updating strategy_performance: {e}")
            import traceback
            traceback.print_exc()
        
        conn.close()

    def record_simulation_end(self):
        """Mark simulation as complete"""
        conn = get_utf8_connection(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE simulation_info 
            SET end_time = ?
            WHERE simulation_id = ?
        ''', (int(datetime.now().timestamp()), ensure_utf8(self.simulation_id)))
        
        conn.commit()
        conn.close()
    
    def print_summary(self):
        """Print simulation summary"""
        conn = get_utf8_connection(self.db_path)
        
        # Get simulation info
        info = pd.read_sql_query('SELECT * FROM simulation_info', conn).iloc[0]
        
        print(f"\n{'='*70}")
        print(f"SIMULATION COMPLETE: {self.simulation_id}")
        print(f"{'='*70}")
        print(f"Database: {self.db_path}")
        print(f"Universe: {info['universe_name']} ({info['num_symbols']} symbols)")
        print(f"Period: {info['date_range_start']} to {info['date_range_end']}")
        
        # Get strategy results
        strategies = pd.read_sql_query('''
            SELECT strategy_name, total_return_pct, total_profit_dollars,
                   win_rate_pct, completed_trades, open_positions, rejected_trades
            FROM strategy_performance
            ORDER BY total_return_pct DESC
        ''', conn)
        
        print(f"\n📊 RESULTS:")
        for _, row in strategies.iterrows():
            print(f"  {row['strategy_name']}:")
            print(f"    Return: {row['total_return_pct']:+.2f}%")
            print(f"    Profit: ${row['total_profit_dollars']:+,.0f}")
            print(f"    Win Rate: {row['win_rate_pct']:.1f}% ({row['completed_trades']} trades)")
            print(f"    Open: {row['open_positions']} | Rejected: {row['rejected_trades']}")
        
        print(f"\n{'='*70}\n")
        
        conn.close()

    # ============================================================
    # 🚀 BATCH INSERT METHODS WITH UTF-8 SAFETY
    # ============================================================
    
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
    
    def batch_update_trade_exits(self, exits_list):
        """Batch update trade exits with UTF-8 safety"""
        if not exits_list:
            return
        
        conn = get_utf8_connection(self.db_path)
        cursor = conn.cursor()
        
        for exit_tuple in exits_list:
            try:
                # Check we have the right number of elements
                if len(exit_tuple) != 16:
                    print(f"⚠️  Skipping: Expected 16 values, got {len(exit_tuple)}")
                    continue
                    
                # Extract values by index
                exit_timestamp = exit_tuple[0]
                exit_date = exit_tuple[1]
                exit_price = exit_tuple[2]
                exit_volume = exit_tuple[3]
                exit_avg_volume_20d = exit_tuple[4]
                exit_relative_volume = exit_tuple[5]
                portfolio_value = exit_tuple[6]
                cash = exit_tuple[7]
                profit_loss = exit_tuple[8]
                profit_loss_pct = exit_tuple[9]
                holding_days = exit_tuple[10]
                holding_bars = exit_tuple[11]
                forced = exit_tuple[12]
                reason = exit_tuple[13]
                strategy_name = exit_tuple[14]
                symbol = exit_tuple[15]
                
                # Sanitize strings
                strategy_name = ensure_utf8(strategy_name)
                symbol = ensure_utf8(symbol)
                reason = ensure_utf8(reason) if reason else None
                
                # Find most recent OPEN trade
                cursor.execute('''
                    SELECT id, entry_timestamp, entry_price, shares
                    FROM trade_history
                    WHERE strategy_name = ? AND symbol = ? AND trade_status = 'OPEN'
                    ORDER BY entry_timestamp DESC
                    LIMIT 1
                ''', (strategy_name, symbol))
                
                trade = cursor.fetchone()
                if trade:
                    trade_id, entry_timestamp_db, entry_price_db, shares = trade
                    
                    # Use provided P&L values or calculate if not provided
                    profit_loss_calc = profit_loss if profit_loss is not None else (exit_price - entry_price_db) * shares
                    profit_loss_pct_calc = profit_loss_pct if profit_loss_pct is not None else ((exit_price - entry_price_db) / entry_price_db * 100) if entry_price_db > 0 else 0
                    
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
                        exit_timestamp, ensure_utf8(str(exit_date)), exit_price,
                        exit_volume, exit_avg_volume_20d, exit_relative_volume,
                        portfolio_value, cash,
                        profit_loss_calc, profit_loss_pct_calc,
                        holding_days, holding_bars,
                        forced, reason, trade_id
                    ))
                    
            except Exception as e:
                print(f"❌ Error processing exit: {e}")
                print(f"   Data: {exit_tuple}")
                continue
        
        conn.commit()
        conn.close()

    def batch_insert_portfolio_snapshots(self, snapshots_list):
        """Batch insert portfolio snapshots with UTF-8 safety"""
        if not snapshots_list:
            return
        
        # Sanitize string fields
        sanitized_snapshots = []
        for snapshot in snapshots_list:
            (timestamp, strategy_name, date_str, portfolio_value, 
             cash, positions_value, num_positions, daily_return) = snapshot
            
            sanitized = (
                timestamp,
                ensure_utf8(strategy_name),
                ensure_utf8(date_str),
                portfolio_value,
                cash,
                positions_value,
                num_positions,
                daily_return
            )
            sanitized_snapshots.append(sanitized)
        
        conn = get_utf8_connection(self.db_path)
        cursor = conn.cursor()
        
        cursor.executemany('''
            INSERT INTO portfolio_history
            (timestamp, strategy_name, date, portfolio_value, cash, positions_value,
             num_positions, daily_return_pct)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', sanitized_snapshots)
        
        conn.commit()
        conn.close()

    def batch_insert_execution_log(self, log_entries):
        """Batch insert execution log entries with UTF-8 safety"""
        if not log_entries:
            return
        
        # Sanitize string fields
        sanitized_entries = []
        for entry in log_entries:
            (timestamp, date_str, bar_number, strategy_name, 
             symbol, action, details) = entry
            
            sanitized = (
                timestamp,
                ensure_utf8(date_str),
                bar_number,
                ensure_utf8(strategy_name),
                ensure_utf8(symbol),
                ensure_utf8(action),
                sanitize_json(details) if details else None
            )
            sanitized_entries.append(sanitized)
        
        conn = get_utf8_connection(self.db_path)
        cursor = conn.cursor()
        
        cursor.executemany('''
            INSERT INTO execution_log
            (timestamp, date, bar_number, strategy_name, symbol, action, details)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', sanitized_entries)
        
        conn.commit()
        conn.close()


# ============================================================
# HELPER: Flush Buffer Class
# ============================================================

class BatchBuffer:
    """
    Helper class to manage batch buffers with automatic flushing
    Use this in your simulator to avoid manual buffer management
    """
    
    def __init__(self, telemetry, batch_size=1000):
        self.telemetry = telemetry
        self.batch_size = batch_size
        
        # Separate buffers for each table
        self.attempts = []
        self.entries = []
        self.exits = []
        self.snapshots = []
        self.logs = []
    
    def add_attempt(self, *args):
        """Add trade attempt to buffer"""
        self.attempts.append(args)
        if len(self.attempts) >= self.batch_size:
            self.flush_attempts()
    
    def add_entry(self, *args):
        """Add trade entry to buffer"""
        self.entries.append(args)
        if len(self.entries) >= self.batch_size:
            self.flush_entries()
    
    def add_exit(self, *args):
        """Add trade exit to buffer"""
        # Check if we received a single tuple with 16 values
        if len(args) == 1 and isinstance(args[0], tuple) and len(args[0]) == 16:
            self.exits.append(args[0])
        # Check if we received 16 separate arguments
        elif len(args) == 16:
            self.exits.append(args)
        else:
            print(f"⚠️  Warning: Invalid exit data format. Got {len(args)} arguments, expected 16")
            if len(args) == 1:
                print(f"   Argument type: {type(args[0])}, length: {len(args[0]) if hasattr(args[0], '__len__') else 'N/A'}")
            return
        
        if len(self.exits) >= self.batch_size:
            self.flush_exits()
    
    def add_snapshot(self, *args):
        """Add portfolio snapshot to buffer"""
        self.snapshots.append(args)
        if len(self.snapshots) >= self.batch_size:
            self.flush_snapshots()
    
    def add_log(self, *args):
        """Add log entry to buffer"""
        self.logs.append(args)
        if len(self.logs) >= self.batch_size:
            self.flush_logs()
    
    def flush_attempts(self):
        """Flush trade attempts buffer"""
        if self.attempts:
            self.telemetry.batch_insert_trade_attempts(self.attempts)
            self.attempts = []
    
    def flush_entries(self):
        """Flush trade entries buffer"""
        if self.entries:
            self.telemetry.batch_insert_trade_entries(self.entries)
            self.entries = []
    
    def flush_exits(self):
        """Flush trade exits buffer"""
        if self.exits:
            self.telemetry.batch_update_trade_exits(self.exits)
            self.exits = []
    
    def flush_snapshots(self):
        """Flush portfolio snapshots buffer"""
        if self.snapshots:
            self.telemetry.batch_insert_portfolio_snapshots(self.snapshots)
            self.snapshots = []
    
    def flush_logs(self):
        """Flush execution logs buffer"""
        if self.logs:
            self.telemetry.batch_insert_execution_log(self.logs)
            self.logs = []
    
    def flush_all(self):
        """Flush all buffers"""
        self.flush_attempts()
        self.flush_entries()
        self.flush_exits()
        self.flush_snapshots()
        self.flush_logs()
    
    def __enter__(self):
        """Context manager support"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Auto-flush on exit"""
        self.flush_all()