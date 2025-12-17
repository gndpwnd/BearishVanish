# ============================================================================
# FILE: db_reader.py
# ============================================================================

"""
Simulation Database Reader
Reads from simulation database for analysis engine

This is used by the analysis engine to read from simulation DB
The visualizer uses analysis_reader.py to read from analysis DB
"""

import sqlite3
import pandas as pd
from pathlib import Path
import json


class SimulationReader:
    """
    Reads simulation database for analysis
    
    Used by analysis engine to compute metrics from simulation results
    """
    
    def __init__(self, db_path):
        """
        Initialize reader
        
        Args:
            db_path: Path to simulation database (.db file)
        """
        self.db_path = Path(db_path)
        if not self.db_path.exists():
            raise FileNotFoundError(f"Simulation database not found: {db_path}")
        
        self.conn = sqlite3.connect(str(self.db_path))
        # Set text factory to handle non-UTF8 data by replacing invalid characters
        self.conn.text_factory = lambda x: str(x, 'utf-8', 'replace')
        self.conn.row_factory = sqlite3.Row
        
        # Cache metadata
        self._metadata = {}
        self._load_metadata()
    
    def _load_metadata(self):
        """Load simulation metadata"""
        cursor = self.conn.cursor()
        
        # Try to get simulation info
        try:
            cursor.execute("SELECT * FROM simulation_info LIMIT 1")
            row = cursor.fetchone()
            if row:
                self._metadata = dict(row)
        except sqlite3.OperationalError:
            # Table might not exist in older databases
            pass
    
    def _table_exists(self, table_name):
        """Check if a table exists in the database"""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table_name,)
        )
        return cursor.fetchone() is not None

    def get_metadata(self):
        """Get simulation metadata"""
        return self._metadata.copy()
    
    def get_simulation_id(self):
        """Get simulation ID"""
        return self._metadata.get('simulation_id', 'unknown')
    
    def get_universe(self):
        """Get universe name"""
        return self._metadata.get('universe_name', 'unknown')
    
    def get_num_symbols(self):
        """Get number of symbols"""
        return self._metadata.get('num_symbols', 0)
    
    def get_initial_cash(self):
        """Get initial cash amount"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT initial_capital FROM strategy_performance LIMIT 1")
        row = cursor.fetchone()
        return row['initial_capital'] if row else 100000
    
    def list_strategies(self):
        """List all strategies in simulation"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT strategy_name FROM strategy_performance ORDER BY strategy_name")
        rows = cursor.fetchall()
        return [row['strategy_name'] for row in rows]
    
    def get_strategy_performance(self, strategy_name):
        """
        Get performance metrics for a strategy
        
        Returns:
            dict: Strategy performance metrics
        """
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM strategy_performance WHERE strategy_name = ?",
            (strategy_name,)
        )
        row = cursor.fetchone()
        
        return dict(row) if row else {}
    
    def get_trade_history(self, strategy_name):
        """
        Get all trades for a strategy
        
        Returns:
            DataFrame: All trades (including open positions)
        """
        # Check if table exists
        if not self._table_exists('trade_history'):
            return pd.DataFrame()
        
        query = """
            SELECT * FROM trade_history 
            WHERE strategy_name = ?
            ORDER BY entry_timestamp
        """
        df = pd.read_sql_query(query, self.conn, params=(strategy_name,))
        
        # Convert date columns
        date_cols = ['entry_date', 'exit_date']
        for col in date_cols:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')
        
        return df
    
    def get_closed_trades(self, strategy_name):
        """
        Get only closed trades for a strategy
        
        Returns:
            DataFrame: Closed trades only
        """
        trades = self.get_trade_history(strategy_name)
        
        if trades.empty:
            return pd.DataFrame()
        
        # Filter for closed trades
        closed_trades = trades[trades['trade_status'] == 'CLOSED'].copy()
        
        # Calculate holding days if not present
        if 'holding_days' not in closed_trades.columns and 'entry_date' in closed_trades.columns and 'exit_date' in closed_trades.columns:
            closed_trades['holding_days'] = (closed_trades['exit_date'] - closed_trades['entry_date']).dt.days
        
        return closed_trades
    
    def get_open_positions(self, strategy_name):
        """
        Get open positions for a strategy
        
        Returns:
            DataFrame: Open positions
        """
        trades = self.get_trade_history(strategy_name)
        
        if trades.empty:
            return pd.DataFrame()
        
        return trades[trades['trade_status'] == 'OPEN'].copy()
    
    def get_portfolio_history(self, strategy_name):
        """
        Get portfolio history for a strategy
        
        Returns:
            DataFrame: Daily portfolio snapshots
        """
        query = """
            SELECT * FROM portfolio_history 
            WHERE strategy_name = ?
            ORDER BY timestamp
        """
        df = pd.read_sql_query(query, self.conn, params=(strategy_name,))
        
        # Convert date column
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'], errors='coerce')
        
        return df
    
    def get_stock_performance(self, strategy_name):
        """
        Get per-symbol performance summary
        
        Returns:
            DataFrame: Stock performance data
        """
        query = """
            SELECT * FROM stock_performance 
            WHERE strategy_name = ?
            ORDER BY net_profit_loss DESC
        """
        df = pd.read_sql_query(query, self.conn, params=(strategy_name,))
        
        # Calculate win rate if not present
        if 'win_rate_pct' not in df.columns and 'total_trades' in df.columns and 'winning_trades' in df.columns:
            df['win_rate_pct'] = (df['winning_trades'] / df['total_trades'] * 100).fillna(0)
        
        return df
    
    def get_trade_attempts(self, strategy_name):
        """
        Get trade attempts (including rejections)
        
        Returns:
            DataFrame: All trade attempts
        """
        query = """
            SELECT * FROM trade_attempts 
            WHERE strategy_name = ?
            ORDER BY timestamp
        """
        df = pd.read_sql_query(query, self.conn, params=(strategy_name,))
        
        # Convert date column
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'], errors='coerce')
        
        return df
    
    def get_rejected_trades(self, strategy_name):
        """
        Get rejected trade attempts
        
        Returns:
            DataFrame: Rejected trades only
        """
        attempts = self.get_trade_attempts(strategy_name)
        
        if attempts.empty:
            return pd.DataFrame()
        
        return attempts[attempts['success'] == 0].copy()
    
    def get_strategy_config(self, strategy_name):
        """
        Get strategy configuration
        
        Returns:
            dict: Strategy configuration
        """
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM strategy_configs WHERE strategy_name = ?",
            (strategy_name,)
        )
        row = cursor.fetchone()
        
        if not row:
            return {}
        
        config = dict(row)
        
        # Parse JSON parameters
        if 'parameters_json' in config and config['parameters_json']:
            try:
                config['parameters'] = json.loads(config['parameters_json'])
            except (json.JSONDecodeError, TypeError):
                config['parameters'] = {}
        
        return config
    
    def get_indicator_history(self, strategy_name, symbol=None, indicator_name=None):
        """
        Get indicator history
        
        Args:
            strategy_name: Strategy name
            symbol: Optional symbol filter
            indicator_name: Optional indicator name filter
        
        Returns:
            DataFrame: Indicator history
        """
        query = "SELECT * FROM indicator_history WHERE strategy_name = ?"
        params = [strategy_name]
        
        if symbol:
            query += " AND symbol = ?"
            params.append(symbol)
        
        if indicator_name:
            query += " AND indicator_name = ?"
            params.append(indicator_name)
        
        query += " ORDER BY timestamp"
        
        df = pd.read_sql_query(query, self.conn, params=params)
        
        # Convert date column
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'], errors='coerce')
        
        return df
    
    def get_execution_log(self, strategy_name, symbol=None):
        """
        Get execution log
        
        Returns:
            DataFrame: Execution log entries
        """
        query = "SELECT * FROM execution_log WHERE strategy_name = ?"
        params = [strategy_name]
        
        if symbol:
            query += " AND symbol = ?"
            params.append(symbol)
        
        query += " ORDER BY timestamp"
        
        df = pd.read_sql_query(query, self.conn, params=params)
        
        # Convert date column
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'], errors='coerce')
        
        return df
    
    def get_best_trades(self, strategy_name, limit=10):
        """
        Get best trades by profit percentage
        
        Returns:
            DataFrame: Best trades
        """
        query = """
            SELECT * FROM trade_history 
            WHERE strategy_name = ? AND trade_status = 'CLOSED' 
            ORDER BY profit_loss_pct DESC 
            LIMIT ?
        """
        df = pd.read_sql_query(query, self.conn, params=(strategy_name, limit))
        
        # Convert date columns
        date_cols = ['entry_date', 'exit_date']
        for col in date_cols:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')
        
        return df
    
    def get_worst_trades(self, strategy_name, limit=10):
        """
        Get worst trades by profit percentage
        
        Returns:
            DataFrame: Worst trades
        """
        query = """
            SELECT * FROM trade_history 
            WHERE strategy_name = ? AND trade_status = 'CLOSED' 
            ORDER BY profit_loss_pct ASC 
            LIMIT ?
        """
        df = pd.read_sql_query(query, self.conn, params=(strategy_name, limit))
        
        # Convert date columns
        date_cols = ['entry_date', 'exit_date']
        for col in date_cols:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')
        
        return df
    
    def get_volume_analysis(self, strategy_name):
        """
        Get volume analysis for trades
        
        Returns:
            dict: Volume statistics
        """
        trades = self.get_closed_trades(strategy_name)
        
        if trades.empty:
            return {}
        
        # Check if volume columns exist
        if 'entry_relative_volume' not in trades.columns:
            return {}
        
        # Filter trades with volume data
        valid_trades = trades[trades['entry_relative_volume'].notna()]
        
        if valid_trades.empty:
            return {}
        
        # Categorize by volume
        high_vol = valid_trades[valid_trades['entry_relative_volume'] > 2.0]
        low_vol = valid_trades[valid_trades['entry_relative_volume'] < 1.0]
        
        # Calculate win rates
        high_vol_wins = high_vol[high_vol['profit_loss_dollars'] > 0]
        low_vol_wins = low_vol[low_vol['profit_loss_dollars'] > 0]
        
        return {
            'trades_with_volume_data': len(valid_trades),
            'avg_entry_volume_ratio': valid_trades['entry_relative_volume'].mean(),
            'high_volume_trades': len(high_vol),
            'low_volume_trades': len(low_vol),
            'high_vol_win_rate': (len(high_vol_wins) / len(high_vol) * 100) if len(high_vol) > 0 else 0,
            'low_vol_win_rate': (len(low_vol_wins) / len(low_vol) * 100) if len(low_vol) > 0 else 0,
        }
    
    def get_correlation_with_benchmark(self, strategy_name, benchmark='SPY'):
        """
        Calculate correlation with benchmark
        
        Returns:
            float: Correlation coefficient
        """
        # Get portfolio history for strategy
        strategy_portfolio = self.get_portfolio_history(strategy_name)
        
        if strategy_portfolio.empty:
            return None
        
        # Get portfolio history for benchmark
        benchmark_portfolio = self.get_portfolio_history(benchmark)
        
        if benchmark_portfolio.empty:
            return None
        
        # Calculate returns
        strategy_returns = strategy_portfolio['portfolio_value'].pct_change().dropna()
        benchmark_returns = benchmark_portfolio['portfolio_value'].pct_change().dropna()
        
        # Align series
        min_len = min(len(strategy_returns), len(benchmark_returns))
        
        if min_len < 2:
            return None
        
        strategy_aligned = strategy_returns.iloc[-min_len:]
        benchmark_aligned = benchmark_returns.iloc[-min_len:]
        
        # Calculate correlation
        correlation = strategy_aligned.corr(benchmark_aligned)
        
        return correlation
    
    def get_benchmark_performance(self):
        """
        Get benchmark strategy performance
        
        Returns:
            dict: Benchmark performance
        """
        # Look for common benchmark names
        benchmarks = ['SPY', 'QQQ', 'DIA', 'IWM', 'VTI']
        
        for benchmark in benchmarks:
            try:
                perf = self.get_strategy_performance(benchmark)
                if perf:
                    return perf
            except:
                continue
        
        return {}
    
    def get_daily_returns(self, strategy_name):
        """
        Get daily returns series
        
        Returns:
            Series: Daily returns
        """
        portfolio = self.get_portfolio_history(strategy_name)
        
        if portfolio.empty:
            return pd.Series()
        
        if 'daily_return_pct' in portfolio.columns:
            # Use pre-computed daily returns
            returns = portfolio['daily_return_pct'] / 100  # Convert from percentage
        else:
            # Calculate from portfolio value
            returns = portfolio['portfolio_value'].pct_change().dropna()
        
        return returns
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def find_latest_simulation_db():
    """
    Find the latest simulation database
    
    Returns:
        Path: Path to latest simulation database
    """
    # Try different possible locations
    possible_paths = [
        Path('../simulator/simulations'),
        Path('./simulations'),
        Path('../../simulator/simulations'),
        Path(__file__).parent.parent / 'simulator' / 'simulations'
    ]
    
    for sim_dir in possible_paths:
        if sim_dir.exists():
            db_files = list(sim_dir.glob('simulation_*.db'))
            if db_files:
                # Sort by creation time (newest first)
                return sorted(db_files, key=lambda x: x.stat().st_mtime, reverse=True)[0]
    
    return None


def list_simulation_databases():
    """
    List all simulation databases
    
    Returns:
        list: Database file paths
    """
    # Try different possible locations
    possible_paths = [
        Path('../simulator/simulations'),
        Path('./simulations'),
        Path('../../simulator/simulations'),
        Path(__file__).parent.parent / 'simulator' / 'simulations'
    ]
    
    all_dbs = []
    
    for sim_dir in possible_paths:
        if sim_dir.exists():
            db_files = list(sim_dir.glob('simulation_*.db'))
            all_dbs.extend(db_files)
    
    # Sort by modification time (newest first)
    return sorted(all_dbs, key=lambda x: x.stat().st_mtime, reverse=True)


if __name__ == '__main__':
    # Test the reader
    latest = find_latest_simulation_db()
    
    if latest:
        print(f"Found simulation database: {latest.name}")
        
        reader = SimulationReader(latest)
        
        # Get strategies
        strategies = reader.list_strategies()
        print(f"Strategies: {strategies}")
        
        if strategies:
            # Get first strategy info
            strategy = strategies[0]
            perf = reader.get_strategy_performance(strategy)
            print(f"\nPerformance for {strategy}:")
            print(f"  Return: {perf.get('total_return_pct', 0):.2f}%")
            print(f"  Win Rate: {perf.get('win_rate_pct', 0):.2f}%")
            print(f"  Sharpe: {perf.get('sharpe_ratio', 0):.2f}")
        
        reader.close()
    else:
        print("No simulation databases found")