"""
Simulation Telemetry System - Accurate Data Collection & Storage
Fixes the fundamental issues with metric calculations and data tracking
"""

import sqlite3
import json
import pandas as pd
from datetime import datetime
from pathlib import Path
import hashlib

TELEMETRY_DIR = Path('./telemetry')
TELEMETRY_DB = TELEMETRY_DIR / 'simulations.db'

class SimulationTelemetry:
    """
    Comprehensive telemetry system for tracking simulation data
    Stores all data needed for accurate reporting and analysis
    """
    
    def __init__(self):
        """Initialize telemetry database"""
        TELEMETRY_DIR.mkdir(exist_ok=True)
        self.db_path = TELEMETRY_DB
        self._init_database()
    
    def _init_database(self):
        """Create telemetry database schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Table 1: Simulation runs
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS simulations (
                simulation_id TEXT PRIMARY KEY,
                timestamp INTEGER NOT NULL,
                universe_name TEXT,
                universe_size INTEGER,
                start_date TEXT,
                end_date TEXT,
                initial_capital REAL,
                duration_seconds REAL,
                forced_liquidation BOOLEAN,
                config_json TEXT
            )
        ''')
        
        # Table 2: Strategy performance per simulation
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS strategy_performance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                simulation_id TEXT NOT NULL,
                strategy_name TEXT NOT NULL,
                initial_capital REAL,
                final_value REAL,
                total_return_pct REAL,
                total_profit_dollars REAL,
                max_drawdown_pct REAL,
                sharpe_ratio REAL,
                sortino_ratio REAL,
                calmar_ratio REAL,
                total_trades INTEGER,
                winning_trades INTEGER,
                losing_trades INTEGER,
                win_rate_pct REAL,
                avg_win_dollars REAL,
                avg_loss_dollars REAL,
                profit_factor REAL,
                avg_trade_duration_days REAL,
                max_positions INTEGER,
                avg_positions REAL,
                exposure_time_pct REAL,
                beta REAL,
                alpha_pct REAL,
                information_ratio REAL,
                FOREIGN KEY (simulation_id) REFERENCES simulations(simulation_id)
            )
        ''')
        
        # Table 3: Individual trades (FIXED - proper P&L tracking)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                simulation_id TEXT NOT NULL,
                strategy_name TEXT NOT NULL,
                symbol TEXT NOT NULL,
                entry_date TEXT NOT NULL,
                exit_date TEXT,
                entry_price REAL NOT NULL,
                exit_price REAL,
                shares REAL NOT NULL,
                entry_value REAL NOT NULL,
                exit_value REAL,
                profit_loss_dollars REAL,
                profit_loss_pct REAL,
                holding_days REAL,
                trade_status TEXT NOT NULL,  -- 'OPEN' or 'CLOSED'
                forced_exit BOOLEAN,
                exit_reason TEXT,
                FOREIGN KEY (simulation_id) REFERENCES simulations(simulation_id)
            )
        ''')
        
        # Table 4: Daily portfolio snapshots
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                simulation_id TEXT NOT NULL,
                strategy_name TEXT NOT NULL,
                date TEXT NOT NULL,
                portfolio_value REAL NOT NULL,
                cash REAL NOT NULL,
                positions_value REAL NOT NULL,
                num_positions INTEGER NOT NULL,
                daily_return_pct REAL,
                FOREIGN KEY (simulation_id) REFERENCES simulations(simulation_id)
            )
        ''')
        
        # Table 5: Per-stock performance
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS stock_performance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                simulation_id TEXT NOT NULL,
                strategy_name TEXT NOT NULL,
                symbol TEXT NOT NULL,
                total_trades INTEGER,
                winning_trades INTEGER,
                losing_trades INTEGER,
                total_invested REAL,
                total_returned REAL,
                net_profit_loss REAL,
                win_rate_pct REAL,
                FOREIGN KEY (simulation_id) REFERENCES simulations(simulation_id)
            )
        ''')
        
        # Indexes for fast queries
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_sim_strategy ON strategy_performance(simulation_id, strategy_name)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_trades_sim ON trades(simulation_id, strategy_name)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol, trade_status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_snapshots ON daily_snapshots(simulation_id, strategy_name, date)')
        
        conn.commit()
        conn.close()
    
    def create_simulation_id(self, universe_name, symbols, start_date):
        """Generate unique simulation ID"""
        # Create deterministic ID based on parameters
        data = f"{universe_name}_{len(symbols)}_{start_date}_{datetime.now().isoformat()}"
        return hashlib.md5(data.encode()).hexdigest()[:16]
    
    def start_simulation(self, universe_name, symbols, start_date, end_date, 
                        initial_capital, config=None):
        """Record start of simulation"""
        sim_id = self.create_simulation_id(universe_name, symbols, start_date)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO simulations 
            (simulation_id, timestamp, universe_name, universe_size, 
             start_date, end_date, initial_capital, config_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            sim_id,
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
        
        return sim_id
    
    def record_trade_entry(self, sim_id, strategy_name, symbol, date, price, shares):
        """Record a BUY trade (entry)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        entry_value = price * shares
        
        cursor.execute('''
            INSERT INTO trades
            (simulation_id, strategy_name, symbol, entry_date, entry_price, 
             shares, entry_value, trade_status)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'OPEN')
        ''', (sim_id, strategy_name, symbol, str(date), price, shares, entry_value))
        
        trade_id = cursor.lastrowid
        
        conn.commit()
        conn.close()
        
        return trade_id
    
    def record_trade_exit(self, sim_id, strategy_name, symbol, exit_date, 
                         exit_price, forced=False, reason=None):
        """
        Record a SELL trade (exit) - matches with most recent OPEN trade for this symbol
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Find the most recent OPEN trade for this symbol and strategy
        cursor.execute('''
            SELECT id, entry_date, entry_price, shares, entry_value
            FROM trades
            WHERE simulation_id = ? AND strategy_name = ? AND symbol = ?
              AND trade_status = 'OPEN'
            ORDER BY entry_date DESC
            LIMIT 1
        ''', (sim_id, strategy_name, symbol))
        
        trade = cursor.fetchone()
        
        if not trade:
            print(f"⚠️  WARNING: No open trade found for {symbol} in {strategy_name}")
            conn.close()
            return None
        
        trade_id, entry_date, entry_price, shares, entry_value = trade
        
        # Calculate P&L
        exit_value = exit_price * shares
        profit_loss = exit_value - entry_value
        profit_loss_pct = (profit_loss / entry_value * 100) if entry_value > 0 else 0
        
        # Calculate holding period
        entry_dt = pd.to_datetime(entry_date)
        exit_dt = pd.to_datetime(exit_date)
        holding_days = (exit_dt - entry_dt).total_seconds() / 86400
        
        # Update trade record
        cursor.execute('''
            UPDATE trades
            SET exit_date = ?, exit_price = ?, exit_value = ?,
                profit_loss_dollars = ?, profit_loss_pct = ?,
                holding_days = ?, trade_status = 'CLOSED',
                forced_exit = ?, exit_reason = ?
            WHERE id = ?
        ''', (
            str(exit_date), exit_price, exit_value,
            profit_loss, profit_loss_pct,
            holding_days, forced, reason,
            trade_id
        ))
        
        conn.commit()
        conn.close()
        
        return trade_id
    
    def record_daily_snapshot(self, sim_id, strategy_name, date, portfolio_value,
                             cash, positions_value, num_positions, daily_return=None):
        """Record daily portfolio state"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO daily_snapshots
            (simulation_id, strategy_name, date, portfolio_value, cash,
             positions_value, num_positions, daily_return_pct)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (sim_id, strategy_name, str(date), portfolio_value, cash,
              positions_value, num_positions, daily_return))
        
        conn.commit()
        conn.close()
    
    def finalize_strategy(self, sim_id, strategy_name, tracker, spy_returns=None):
        """
        Calculate and store final strategy metrics
        FIXED: Accurate calculations that handle open positions
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get all CLOSED trades for accurate win rate
        cursor.execute('''
            SELECT profit_loss_dollars, holding_days
            FROM trades
            WHERE simulation_id = ? AND strategy_name = ?
              AND trade_status = 'CLOSED'
        ''', (sim_id, strategy_name))
        
        closed_trades = cursor.fetchall()
        
        # Calculate accurate metrics
        total_trades = len(closed_trades)
        winning_trades = sum(1 for pnl, _ in closed_trades if pnl > 0)
        losing_trades = sum(1 for pnl, _ in closed_trades if pnl < 0)
        
        # FIXED: Win rate based only on closed trades
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        
        # Average win/loss
        wins = [pnl for pnl, _ in closed_trades if pnl > 0]
        losses = [pnl for pnl, _ in closed_trades if pnl < 0]
        
        avg_win = sum(wins) / len(wins) if wins else 0
        avg_loss = sum(losses) / len(losses) if losses else 0
        
        # Profit factor
        gross_profit = sum(wins)
        gross_loss = abs(sum(losses))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
        
        # Average trade duration
        avg_duration = sum(days for _, days in closed_trades) / total_trades if total_trades > 0 else 0
        
        # Portfolio metrics
        initial_capital = tracker.initial_cash
        final_value = tracker.get_final_value()
        total_return = (final_value - initial_capital) / initial_capital * 100
        profit_dollars = final_value - initial_capital
        
        # Store performance data
        cursor.execute('''
            INSERT INTO strategy_performance
            (simulation_id, strategy_name, initial_capital, final_value,
             total_return_pct, total_profit_dollars, max_drawdown_pct,
             sharpe_ratio, sortino_ratio, calmar_ratio,
             total_trades, winning_trades, losing_trades, win_rate_pct,
             avg_win_dollars, avg_loss_dollars, profit_factor,
             avg_trade_duration_days, max_positions, avg_positions,
             exposure_time_pct, beta, alpha_pct, information_ratio)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            sim_id, strategy_name, initial_capital, final_value,
            total_return, profit_dollars, tracker.get_max_drawdown(),
            tracker.get_sharpe_ratio(), tracker.get_sortino_ratio(), tracker.get_calmar_ratio(),
            total_trades, winning_trades, losing_trades, win_rate,
            avg_win, avg_loss, profit_factor,
            avg_duration, tracker.max_positions, 
            sum(1 for v in tracker.positions.values() if v > 0) / len(tracker.dates) if tracker.dates else 0,
            tracker.get_exposure_time(),
            tracker.get_portfolio_beta(spy_returns) if spy_returns is not None else None,
            tracker.get_alpha(tracker.get_return_pct()) if spy_returns is not None else None,
            tracker.get_information_ratio(spy_returns) if spy_returns is not None else None
        ))
        
        conn.commit()
        conn.close()
    
    def get_simulation_history(self, limit=20):
        """Get recent simulation history"""
        conn = sqlite3.connect(self.db_path)
        
        query = '''
            SELECT s.simulation_id, s.timestamp, s.universe_name, s.universe_size,
                   s.start_date, s.end_date, s.initial_capital,
                   COUNT(DISTINCT sp.strategy_name) as num_strategies
            FROM simulations s
            LEFT JOIN strategy_performance sp ON s.simulation_id = sp.simulation_id
            GROUP BY s.simulation_id
            ORDER BY s.timestamp DESC
            LIMIT ?
        '''
        
        df = pd.read_sql_query(query, conn, params=(limit,))
        conn.close()
        
        return df
    
    def get_strategy_comparison(self, sim_id):
        """Get strategy performance comparison for a simulation"""
        conn = sqlite3.connect(self.db_path)
        
        query = '''
            SELECT strategy_name, total_return_pct, total_profit_dollars,
                   win_rate_pct, sharpe_ratio, max_drawdown_pct,
                   total_trades, winning_trades, losing_trades
            FROM strategy_performance
            WHERE simulation_id = ?
            ORDER BY total_return_pct DESC
        '''
        
        df = pd.read_sql_query(query, conn, params=(sim_id,))
        conn.close()
        
        return df
    
    def get_trade_history(self, sim_id, strategy_name=None, symbol=None, 
                         status='CLOSED'):
        """Get filtered trade history"""
        conn = sqlite3.connect(self.db_path)
        
        query = '''
            SELECT symbol, entry_date, exit_date, entry_price, exit_price,
                   shares, profit_loss_dollars, profit_loss_pct, holding_days,
                   trade_status, forced_exit, exit_reason
            FROM trades
            WHERE simulation_id = ?
        '''
        
        params = [sim_id]
        
        if strategy_name:
            query += ' AND strategy_name = ?'
            params.append(strategy_name)
        
        if symbol:
            query += ' AND symbol = ?'
            params.append(symbol)
        
        if status:
            query += ' AND trade_status = ?'
            params.append(status)
        
        query += ' ORDER BY entry_date DESC'
        
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        
        return df
    
    def print_simulation_summary(self, sim_id):
        """Print comprehensive summary of a simulation"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get simulation info
        cursor.execute('''
            SELECT timestamp, universe_name, universe_size, start_date, end_date, initial_capital
            FROM simulations
            WHERE simulation_id = ?
        ''', (sim_id,))
        
        sim_info = cursor.fetchone()
        
        if not sim_info:
            print(f"Simulation {sim_id} not found")
            conn.close()
            return
        
        timestamp, universe, size, start, end, capital = sim_info
        run_time = datetime.fromtimestamp(timestamp)
        
        print(f"\n{'='*70}")
        print(f"SIMULATION SUMMARY: {sim_id}")
        print(f"{'='*70}")
        print(f"Run Time: {run_time}")
        print(f"Universe: {universe} ({size} stocks)")
        print(f"Period: {start} to {end}")
        print(f"Initial Capital: ${capital:,.0f}")
        
        # Get strategy performance
        cursor.execute('''
            SELECT strategy_name, total_return_pct, total_profit_dollars,
                   win_rate_pct, total_trades, winning_trades, losing_trades,
                   sharpe_ratio, max_drawdown_pct
            FROM strategy_performance
            WHERE simulation_id = ?
            ORDER BY total_return_pct DESC
        ''', (sim_id,))
        
        strategies = cursor.fetchall()
        
        print(f"\n📊 STRATEGY PERFORMANCE:")
        print(f"{'Strategy':<25} {'Return %':<12} {'Profit':<15} {'Win Rate':<12} {'Sharpe':<10}")
        print(f"{'-'*70}")
        
        for strat in strategies:
            name, ret, profit, wr, total, wins, losses, sharpe, dd = strat
            print(f"{name:<25} {ret:>10.2f}% ${profit:>13,.0f} {wr:>10.1f}% {sharpe:>10.3f}")
        
        conn.close()
        print(f"{'='*70}\n")


# Global telemetry instance
telemetry = SimulationTelemetry()