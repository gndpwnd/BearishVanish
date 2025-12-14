"""
Enhanced Simulation Telemetry with Complete Trade Recording AND BATCH OPTIMIZATION
FIXES: Missing timestamps, rejected trades, trade attempts, and context data
USES SIMULATION TIMESTAMPS to prevent look-ahead bias
ADDED: Batch insert methods for 5-10x speedup
FIXED: batch_update_trade_exits unpacking error
"""

import sqlite3
import json
import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path
import hashlib
import time

TELEMETRY_ROOT = Path('./simulations')

class SimulationTelemetry:
    """
    Enhanced telemetry system with complete trade recording
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
        """Create enhanced database schema with strategy configuration"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
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
                position_size_pct REAL,     -- NEW: Strategy position size percentage
                max_positions INTEGER,      -- NEW: Strategy maximum concurrent positions
                strategy_config_json TEXT   -- NEW: Full strategy configuration as JSON
            )
        ''')
        
        # Table 3: ENHANCED Trade history with full timestamps
        cursor.execute('''
            CREATE TABLE trade_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                strategy_name TEXT NOT NULL,
                symbol TEXT NOT NULL,
                entry_timestamp INTEGER NOT NULL,
                entry_date TEXT NOT NULL,
                entry_price REAL NOT NULL,
                shares REAL NOT NULL,
                entry_portfolio_value REAL,
                entry_cash REAL,
                entry_num_positions INTEGER,
                exit_timestamp INTEGER,
                exit_date TEXT,
                exit_price REAL,
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
        
        # Table 4: NEW - Trade attempts (including rejections)
        cursor.execute('''
            CREATE TABLE trade_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp INTEGER NOT NULL,
                date TEXT NOT NULL,
                strategy_name TEXT NOT NULL,
                symbol TEXT NOT NULL,
                signal TEXT NOT NULL,
                price REAL NOT NULL,
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
        
        # Table 7: NEW - Bar-by-bar execution log
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
        
        # Table 8: NEW - Strategy configurations
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
        
        # Indexes
        cursor.execute('CREATE INDEX idx_trades_strategy ON trade_history(strategy_name, trade_status)')
        cursor.execute('CREATE INDEX idx_trades_symbol ON trade_history(symbol)')
        cursor.execute('CREATE INDEX idx_trades_entry_ts ON trade_history(entry_timestamp)')
        cursor.execute('CREATE INDEX idx_portfolio_strategy ON portfolio_history(strategy_name, timestamp)')
        cursor.execute('CREATE INDEX idx_attempts_strategy ON trade_attempts(strategy_name, success)')
        cursor.execute('CREATE INDEX idx_execution_strategy ON execution_log(strategy_name, timestamp)')
        
        conn.commit()
        conn.close()

    def record_simulation_start(self, universe_name, symbols, start_date, end_date, 
                               initial_capital, config=None):
        """Record simulation metadata"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Simulation metadata uses real-world timestamps (when simulation runs)
        # This is OK because it's about the simulation itself, not the trading
        cursor.execute('''
            INSERT INTO simulation_info 
            (simulation_id, start_time, universe_name, num_symbols,
             date_range_start, date_range_end, initial_capital, config_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            self.simulation_id,
            int(datetime.now().timestamp()),
            universe_name,
            len(symbols),
            str(start_date),
            str(end_date),
            initial_capital,
            json.dumps(config or {})
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
                            success, rejection_reason=None):
        """
        Record EVERY trade attempt, including rejections
        Uses SIMULATION TIME, not real-world time to prevent look-ahead bias
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Use simulation time (not real-world time)
        timestamp = self._get_simulation_timestamp(date)
        
        cursor.execute('''
            INSERT INTO trade_attempts
            (timestamp, date, strategy_name, symbol, signal, price,
             portfolio_value, cash, num_positions, max_positions, 
             success, rejection_reason)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            timestamp,
            str(date),
            strategy_name,
            symbol,
            signal,
            price,
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
                          entry_reason=None):
        """
        Record BUY trade with enhanced context
        Uses SIMULATION TIME, not real-world time
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Use simulation time (not real-world time)
        timestamp = self._get_simulation_timestamp(date)
        
        cursor.execute('''
            INSERT INTO trade_history
            (strategy_name, symbol, entry_timestamp, entry_date, entry_price, shares,
             entry_portfolio_value, entry_cash, entry_num_positions, 
             trade_status, entry_reason)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'OPEN', ?)
        ''', (
            strategy_name, symbol, timestamp, str(date), price, shares,
            portfolio_value, cash, num_positions, entry_reason
        ))
        
        conn.commit()
        conn.close()

    def record_trade_exit(self, strategy_name, symbol, exit_date, exit_price,
                         portfolio_value=None, cash=None, forced=False, reason=None):
        """
        Record SELL trade with enhanced context
        Uses SIMULATION TIME, not real-world time
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Use simulation time (not real-world time)
        exit_timestamp = self._get_simulation_timestamp(exit_date)
        
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
        
        # Calculate P&L (using simulation times)
        profit_loss = (exit_price - entry_price) * shares
        profit_loss_pct = (exit_price - entry_price) / entry_price * 100
        
        # Calculate holding period using simulation timestamps
        holding_days = (exit_timestamp - entry_timestamp) / 86400.0  # Convert seconds to days
        
        # For holding bars, we need to know the bar frequency
        # Since we don't have that here, we can leave it or calculate differently
        # Let's approximate assuming daily bars (1 bar per day)
        holding_bars = int(holding_days)
        
        # Update trade
        cursor.execute('''
            UPDATE trade_history
            SET exit_timestamp = ?, exit_date = ?, exit_price = ?,
                exit_portfolio_value = ?, exit_cash = ?,
                profit_loss_dollars = ?, profit_loss_pct = ?,
                holding_days = ?, holding_bars = ?,
                trade_status = 'CLOSED',
                forced_exit = ?, exit_reason = ?
            WHERE id = ?
        ''', (
            exit_timestamp, str(exit_date), exit_price,
            portfolio_value, cash,
            profit_loss, profit_loss_pct,
            holding_days, holding_bars,
            forced, reason, trade_id
        ))
        
        conn.commit()
        conn.close()

    def record_daily_snapshot(self, strategy_name, date, portfolio_value,
                             cash, positions_value, num_positions, daily_return=None):
        """Record daily portfolio state with SIMULATION timestamp"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Use simulation time (not real-world time)
        timestamp = self._get_simulation_timestamp(date)
        
        cursor.execute('''
            INSERT INTO portfolio_history
            (timestamp, strategy_name, date, portfolio_value, cash, positions_value,
             num_positions, daily_return_pct)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (timestamp, strategy_name, str(date), portfolio_value, cash, positions_value,
              num_positions, daily_return))
        
        conn.commit()
        conn.close()

    def log_execution(self, strategy_name, symbol, date, bar_number, action, details=None):
        """
        Log bar-by-bar execution for debugging
        Uses SIMULATION TIME, not real-world time
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Use simulation time (not real-world time)
        timestamp = self._get_simulation_timestamp(date)
        
        cursor.execute('''
            INSERT INTO execution_log
            (timestamp, date, bar_number, strategy_name, symbol, action, details)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (timestamp, str(date), bar_number, strategy_name, symbol, action,
              json.dumps(details) if details else None))
        
        conn.commit()
        conn.close()

    def finalize_strategy(self, strategy_name, tracker, spy_returns=None, rejected_count=0):
        """Calculate and store final metrics with strategy configuration"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get strategy configuration from tracker
        strategy_config = tracker.strategy_config if hasattr(tracker, 'strategy_config') else {}
        
        # Extract configuration values
        position_size_pct = strategy_config.get('position_size_pct', 0.10)
        max_positions = strategy_config.get('max_positions', 10)
        
        # Get all parameters from strategy instance if available
        full_config = {}
        if hasattr(tracker, 'strategy_instance'):
            strategy_instance = tracker.strategy_instance
            if hasattr(strategy_instance, 'get_config'):
                full_config = strategy_instance.get_config()
            else:
                # Extract basic parameters
                full_config = {
                    'name': getattr(strategy_instance, 'name', strategy_name),
                    'initial_capital': getattr(strategy_instance, 'initial_capital', tracker.initial_cash),
                    'position_size_pct': getattr(strategy_instance, 'position_size_pct', position_size_pct),
                    'max_positions': getattr(strategy_instance, 'max_positions', max_positions),
                    'color': getattr(strategy_instance, 'color', 'blue'),
                }
        
        # Get completed trades for win rate
        cursor.execute('''
            SELECT profit_loss_dollars FROM trade_history
            WHERE strategy_name = ? AND trade_status = 'CLOSED'
        ''', (strategy_name,))
        
        closed_trades = cursor.fetchall()
        total_trades = len(closed_trades)
        wins = sum(1 for (pnl,) in closed_trades if pnl > 0)
        losses = sum(1 for (pnl,) in closed_trades if pnl < 0)
        win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
        
        # Get open positions count
        cursor.execute('''
            SELECT COUNT(*) FROM trade_history
            WHERE strategy_name = ? AND trade_status = 'OPEN'
        ''', (strategy_name,))
        open_positions = cursor.fetchone()[0]
        
        # Calculate profit factor
        gross_profit = sum(pnl for (pnl,) in closed_trades if pnl > 0)
        gross_loss = abs(sum(pnl for (pnl,) in closed_trades if pnl < 0))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
        
        # Also store strategy configuration in separate table
        cursor.execute('''
            INSERT OR REPLACE INTO strategy_configs
            (strategy_name, initial_capital, position_size_pct, max_positions, 
            color, parameters_json, created_timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            strategy_name,
            full_config.get('initial_capital', tracker.initial_cash),
            full_config.get('position_size_pct', position_size_pct),
            full_config.get('max_positions', max_positions),
            full_config.get('color', 'blue'),
            json.dumps(full_config),
            int(time.time())
        ))
        
        # Store performance with configuration
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
            strategy_name,
            tracker.initial_cash,
            tracker.get_final_value(),
            tracker.get_return_pct(),
            tracker.get_profit_dollars(),
            len(tracker.trades),
            total_trades,
            open_positions,
            rejected_count,
            win_rate,
            wins,
            losses,
            profit_factor,
            tracker.get_sharpe_ratio(),
            tracker.get_sortino_ratio(),
            tracker.get_calmar_ratio(),
            tracker.get_max_drawdown(),
            tracker.get_avg_win(),
            tracker.get_avg_loss(),
            tracker.get_avg_trade_duration(),
            abs(tracker.get_avg_win() / tracker.get_avg_loss()) if tracker.get_avg_loss() != 0 else 0,
            tracker.get_expectancy(),
            tracker.get_exposure_time(),
            tracker.get_portfolio_beta(spy_returns) if spy_returns is not None else None,
            tracker.get_alpha(tracker.get_return_pct()) if spy_returns is not None else None,
            tracker.get_information_ratio(spy_returns) if spy_returns is not None else None,
            position_size_pct,
            max_positions,
            json.dumps(full_config)
        ))
        
        conn.commit()
        conn.close()

    def record_simulation_end(self):
        """Mark simulation as complete"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Simulation end uses real-world timestamp (when simulation finished)
        cursor.execute('''
            UPDATE simulation_info 
            SET end_time = ?
            WHERE simulation_id = ?
        ''', (int(datetime.now().timestamp()), self.simulation_id))
        
        conn.commit()
        conn.close()
    
    def print_summary(self):
        """Print simulation summary"""
        conn = sqlite3.connect(self.db_path)
        
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
    # 🚀 NEW: BATCH INSERT METHODS (5-10x Speedup)
    # ============================================================
    
    def batch_insert_trade_attempts(self, attempts_list):
        """
        Batch insert trade attempts (including rejections)
        5-10x faster than individual inserts
        
        Args:
            attempts_list: List of tuples matching trade_attempts schema
        """
        if not attempts_list:
            return
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.executemany('''
            INSERT INTO trade_attempts
            (timestamp, date, strategy_name, symbol, signal, price,
             portfolio_value, cash, num_positions, max_positions, 
             success, rejection_reason)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', attempts_list)
        
        conn.commit()
        conn.close()

    def batch_insert_trade_entries(self, entries_list):
        """
        Batch insert trade entries (BUY orders)
        
        Args:
            entries_list: List of tuples matching trade_history schema
        """
        if not entries_list:
            return
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.executemany('''
            INSERT INTO trade_history
            (strategy_name, symbol, entry_timestamp, entry_date, entry_price, shares,
             entry_portfolio_value, entry_cash, entry_num_positions, 
             trade_status, entry_reason)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'OPEN', ?)
        ''', entries_list)
        
        conn.commit()
        conn.close()

    def batch_update_trade_exits(self, exits_list):
        """
        Batch update trade exits (SELL orders)
        SIMPLER FIX: Access tuple elements directly
        
        Args:
            exits_list: List of tuples where each tuple contains 13 values
        """
        if not exits_list:
            return
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for exit_tuple in exits_list:
            try:
                # Check we have the right number of elements
                if len(exit_tuple) != 13:
                    print(f"⚠️  Skipping: Expected 13 values, got {len(exit_tuple)}")
                    continue
                    
                # Extract values by index (simpler than unpacking)
                exit_timestamp = exit_tuple[0]
                exit_date = exit_tuple[1]
                exit_price = exit_tuple[2]
                portfolio_value = exit_tuple[3]
                cash = exit_tuple[4]
                profit_loss = exit_tuple[5]
                profit_loss_pct = exit_tuple[6]
                holding_days = exit_tuple[7]
                holding_bars = exit_tuple[8]
                forced = exit_tuple[9]
                reason = exit_tuple[10]
                strategy_name = exit_tuple[11]
                symbol = exit_tuple[12]
                
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
                    
                    # Calculate P&L if not provided
                    profit_loss_calc = profit_loss if profit_loss is not None else (exit_price - entry_price_db) * shares
                    profit_loss_pct_calc = profit_loss_pct if profit_loss_pct is not None else ((exit_price - entry_price_db) / entry_price_db * 100) if entry_price_db > 0 else 0
                    
                    cursor.execute('''
                        UPDATE trade_history
                        SET exit_timestamp = ?, exit_date = ?, exit_price = ?,
                            exit_portfolio_value = ?, exit_cash = ?,
                            profit_loss_dollars = ?, profit_loss_pct = ?,
                            holding_days = ?, holding_bars = ?,
                            trade_status = 'CLOSED',
                            forced_exit = ?, exit_reason = ?
                        WHERE id = ?
                    ''', (
                        exit_timestamp, str(exit_date), exit_price,
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
        """
        Batch insert daily portfolio snapshots
        Much faster than one-by-one
        
        Args:
            snapshots_list: List of tuples matching portfolio_history schema
        """
        if not snapshots_list:
            return
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.executemany('''
            INSERT INTO portfolio_history
            (timestamp, strategy_name, date, portfolio_value, cash, positions_value,
             num_positions, daily_return_pct)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', snapshots_list)
        
        conn.commit()
        conn.close()

        def batch_insert_execution_log(self, log_entries):
            """
            Batch insert execution log entries
            
            Args:
                log_entries: List of tuples for execution_log table
            """
            if not log_entries:
                return
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.executemany('''
                INSERT INTO execution_log
                (timestamp, date, bar_number, strategy_name, symbol, action, details)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', log_entries)
            
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
        """Add trade exit to buffer - FIXED VERSION"""
        # Check if we received a single tuple with 13 values
        if len(args) == 1 and isinstance(args[0], tuple) and len(args[0]) == 13:
            self.exits.append(args[0])
        # Check if we received 13 separate arguments
        elif len(args) == 13:
            self.exits.append(args)
        else:
            print(f"⚠️  Warning: Invalid exit data format. Got {len(args)} arguments")
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