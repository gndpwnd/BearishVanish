# ============================================================================
# FILE: visualizer/simulation_reader.py
# ============================================================================

"""
Simulation Database Reader for Visualizer
Independent reader - no imports from other apps
"""

import sqlite3
import pandas as pd
from pathlib import Path


class SimulationReader:
    """
    Reads simulation database independently
    Used by visualizer for detailed trade views
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
        self.conn.row_factory = sqlite3.Row
    
    def list_strategies(self):
        """List all strategies in simulation"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT strategy_name FROM strategy_performance ORDER BY strategy_name")
        rows = cursor.fetchall()
        return [row['strategy_name'] for row in rows]
    
    def get_trade_history(self, strategy_name):
        """
        Get all trades for a strategy
        
        Returns:
            DataFrame: All trades (including open positions)
        """
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
        if not df.empty:
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
        
        try:
            df = pd.read_sql_query(query, self.conn, params=(strategy_name,))
            
            # Convert date column
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'], errors='coerce')
            
            return df
        except Exception:
            return pd.DataFrame()
    
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
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()