"""
Simulation Database Reader
Reads detailed trade data from simulation databases
"""

import sqlite3
import pandas as pd
from pathlib import Path
from typing import Optional, List


class SimulationReader:
    """
    Reads simulation database for detailed trade information
    """
    
    def __init__(self, db_path: Path):
        """
        Initialize reader
        
        Args:
            db_path: Path to simulation database
        """
        self.db_path = Path(db_path)
        
        if not self.db_path.exists():
            raise FileNotFoundError(f"Simulation database not found: {db_path}")
        
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.text_factory = str  # FIX: Handle UTF-8 text properly
        self.conn.row_factory = sqlite3.Row
    
    def _decode_value(self, value):
        """Decode bytes to string with error handling"""
        if value is None:
            return None
        if isinstance(value, bytes):
            try:
                return value.decode('utf-8')
            except UnicodeDecodeError:
                try:
                    return value.decode('latin-1')
                except:
                    try:
                        return value.decode('utf-8', errors='replace')
                    except:
                        return str(value)
        return value
    
    def _decode_row(self, row):
        """Decode all values in a row"""
        if row is None:
            return None
        return {key: self._decode_value(row[key]) for key in row.keys()}
    
    def list_strategies(self) -> List[str]:
        """List all strategies in simulation"""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT DISTINCT strategy_name FROM trade_history ORDER BY strategy_name"
        )
        results = cursor.fetchall()
        return [self._decode_value(row[0]) for row in results]
    
    def get_trade_history(
        self,
        strategy_name: str,
        status: Optional[str] = None,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> pd.DataFrame:
        """
        Get trade history for a strategy
        
        Args:
            strategy_name: Strategy name
            status: Filter by status ('OPEN', 'CLOSED', None for all)
            limit: Maximum number of trades to return
            offset: Number of trades to skip
        
        Returns:
            DataFrame: Trade history
        """
        query = "SELECT * FROM trade_history WHERE strategy_name = ?"
        params = [strategy_name]
        
        if status:
            query += " AND trade_status = ?"
            params.append(status)
        
        query += " ORDER BY entry_timestamp DESC"
        
        if limit:
            query += " LIMIT ? OFFSET ?"
            params.extend([limit, offset])
        
        df = pd.read_sql_query(query, self.conn, params=params)
        
        # Decode any byte columns
        for col in df.columns:
            if df[col].dtype == 'object':
                df[col] = df[col].apply(lambda x: self._decode_value(x) if isinstance(x, bytes) else x)
        
        # Convert date columns
        date_cols = ['entry_date', 'exit_date', 'entry_timestamp', 'exit_timestamp']
        for col in date_cols:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')
        
        # Ensure numeric columns are numeric
        numeric_cols = ['entry_price', 'exit_price', 'shares', 'profit_loss_dollars', 'profit_loss_pct']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        return df
    
    def get_closed_trades(self, strategy_name: str) -> pd.DataFrame:
        """Get only closed trades"""
        return self.get_trade_history(strategy_name, status='CLOSED')
    
    def get_open_positions(self, strategy_name: str) -> pd.DataFrame:
        """Get only open positions"""
        return self.get_trade_history(strategy_name, status='OPEN')
    
    def get_best_trades(self, strategy_name: str, limit: int = 10) -> pd.DataFrame:
        """Get best trades by profit percentage"""
        query = """
            SELECT * FROM trade_history
            WHERE strategy_name = ? AND trade_status = 'CLOSED'
            ORDER BY profit_loss_pct DESC
            LIMIT ?
        """
        df = pd.read_sql_query(query, self.conn, params=(strategy_name, limit))
        
        # Decode bytes
        for col in df.columns:
            if df[col].dtype == 'object':
                df[col] = df[col].apply(lambda x: self._decode_value(x) if isinstance(x, bytes) else x)
        
        # Convert dates
        for col in ['entry_date', 'exit_date']:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')
        
        # Ensure numeric
        if 'profit_loss_pct' in df.columns:
            df['profit_loss_pct'] = pd.to_numeric(df['profit_loss_pct'], errors='coerce')
        
        return df
    
    def get_worst_trades(self, strategy_name: str, limit: int = 10) -> pd.DataFrame:
        """Get worst trades by profit percentage"""
        query = """
            SELECT * FROM trade_history
            WHERE strategy_name = ? AND trade_status = 'CLOSED'
            ORDER BY profit_loss_pct ASC
            LIMIT ?
        """
        df = pd.read_sql_query(query, self.conn, params=(strategy_name, limit))
        
        # Decode bytes
        for col in df.columns:
            if df[col].dtype == 'object':
                df[col] = df[col].apply(lambda x: self._decode_value(x) if isinstance(x, bytes) else x)
        
        # Convert dates
        for col in ['entry_date', 'exit_date']:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')
        
        # Ensure numeric
        if 'profit_loss_pct' in df.columns:
            df['profit_loss_pct'] = pd.to_numeric(df['profit_loss_pct'], errors='coerce')
        
        return df
    
    def get_stock_performance(self, strategy_name: str) -> pd.DataFrame:
        """Get per-symbol performance summary"""
        query = """
            SELECT * FROM stock_performance
            WHERE strategy_name = ?
            ORDER BY net_profit_loss DESC
        """
        df = pd.read_sql_query(query, self.conn, params=(strategy_name,))
        
        # Decode bytes
        for col in df.columns:
            if df[col].dtype == 'object':
                df[col] = df[col].apply(lambda x: self._decode_value(x) if isinstance(x, bytes) else x)
        
        # Calculate win rate if not present
        if not df.empty and 'win_rate_pct' not in df.columns:
            if 'total_trades' in df.columns and 'winning_trades' in df.columns:
                df['win_rate_pct'] = pd.to_numeric(
                    (df['winning_trades'] / df['total_trades'] * 100).fillna(0),
                    errors='coerce'
                )
        
        # Ensure numeric columns
        numeric_cols = ['total_trades', 'winning_trades', 'losing_trades', 'net_profit_loss', 'avg_profit_per_trade']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        return df
    
    def get_trade_attempts(self, strategy_name: str) -> pd.DataFrame:
        """Get all trade attempts (including rejections)"""
        query = """
            SELECT * FROM trade_attempts
            WHERE strategy_name = ?
            ORDER BY timestamp DESC
        """
        try:
            df = pd.read_sql_query(query, self.conn, params=(strategy_name,))
            
            # Decode bytes
            for col in df.columns:
                if df[col].dtype == 'object':
                    df[col] = df[col].apply(lambda x: self._decode_value(x) if isinstance(x, bytes) else x)
            
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'], errors='coerce')
            
            return df
        except Exception as e:
            print(f"Error getting trade attempts: {e}")
            return pd.DataFrame()
    
    def get_rejected_trades(self, strategy_name: str) -> pd.DataFrame:
        """Get rejected trade attempts"""
        attempts = self.get_trade_attempts(strategy_name)
        
        if attempts.empty:
            return pd.DataFrame()
        
        return attempts[attempts['success'] == 0].copy()
    
    def get_trade_count(self, strategy_name: str, status: Optional[str] = None) -> int:
        """Get count of trades"""
        query = "SELECT COUNT(*) FROM trade_history WHERE strategy_name = ?"
        params = [strategy_name]
        
        if status:
            query += " AND trade_status = ?"
            params.append(status)
        
        cursor = self.conn.cursor()
        cursor.execute(query, params)
        result = cursor.fetchone()
        return result[0] if result else 0
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
    
    def __del__(self):
        """Cleanup on deletion"""
        try:
            self.close()
        except:
            pass