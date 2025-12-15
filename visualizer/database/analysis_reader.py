"""
Analysis Database Reader
Reads pre-computed metrics from analysis databases
"""

import sqlite3
import json
import pandas as pd
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime, date


class AnalysisReader:
    """
    Fast reader for analysis databases
    All data is pre-computed - no calculations needed
    """
    
    def __init__(self, db_path: Path):
        """
        Initialize reader
        
        Args:
            db_path: Path to analysis database
        """
        self.db_path = Path(db_path)
        
        if not self.db_path.exists():
            raise FileNotFoundError(f"Analysis database not found: {db_path}")
        
        # Create connection with proper settings
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        
        # Load metadata
        self.metadata = self._load_metadata()
        self.strategies = self._load_strategies()
    
    def _load_metadata(self) -> Dict[str, str]:
        """Load analysis metadata"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT key, value FROM analysis_metadata")
        return dict(cursor.fetchall())
    
    def _load_strategies(self) -> List[str]:
        """Load list of strategies"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT strategy_name FROM strategy_summary ORDER BY strategy_name")
        return [row[0] for row in cursor.fetchall()]
    
    def _row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        """
        Convert SQLite Row to dict, handling all data types properly
        
        Handles:
        - datetime/date objects -> ISO strings
        - bytes -> UTF-8 strings (with error handling)
        - None values
        - All other types as-is
        """
        result = {}
        for key in row.keys():
            value = row[key]
            
            # Handle None
            if value is None:
                result[key] = None
            # Handle datetime/date
            elif isinstance(value, (datetime, date)):
                result[key] = value.isoformat()
            # Handle bytes - use errors='replace' to avoid decode errors
            elif isinstance(value, bytes):
                try:
                    # Try UTF-8 first
                    result[key] = value.decode('utf-8')
                except UnicodeDecodeError:
                    try:
                        # Try latin-1 which handles all byte values
                        result[key] = value.decode('latin-1')
                    except:
                        # Last resort: use errors='replace'
                        result[key] = value.decode('utf-8', errors='replace')
            # Handle everything else
            else:
                result[key] = value
        
        return result
    
    def get_strategies(self) -> List[str]:
        """Get list of all strategies"""
        return self.strategies
    
    def get_metadata(self) -> Dict[str, str]:
        """Get analysis metadata"""
        return self.metadata
    
    def get_summary(self, strategy_name: str) -> Optional[Dict[str, Any]]:
        """
        Get complete summary for a strategy
        
        Returns:
            dict: All metrics or None if not found
        """
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM strategy_summary WHERE strategy_name = ?",
            (strategy_name,)
        )
        
        row = cursor.fetchone()
        if not row:
            return None
        
        # Convert Row to dict with proper type handling
        return self._row_to_dict(row)
    
    def get_all_summaries(self) -> List[Dict[str, Any]]:
        """Get summaries for all strategies"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM strategy_summary ORDER BY total_return_pct DESC")
        return [self._row_to_dict(row) for row in cursor.fetchall()]
    
    def get_monthly_returns(self, strategy_name: str) -> pd.DataFrame:
        """Get monthly returns"""
        query = """
            SELECT year_month, return_pct, num_trades, win_rate_pct
            FROM monthly_returns
            WHERE strategy_name = ?
            ORDER BY year_month
        """
        return pd.read_sql_query(query, self.conn, params=(strategy_name,))
    
    def get_drawdown_periods(self, strategy_name: str, limit: int = 5) -> pd.DataFrame:
        """Get significant drawdown periods"""
        query = """
            SELECT * FROM drawdown_periods
            WHERE strategy_name = ?
            ORDER BY drawdown_pct DESC
            LIMIT ?
        """
        return pd.read_sql_query(query, self.conn, params=(strategy_name, limit))
    
    def get_returns_distribution(self, strategy_name: str) -> pd.DataFrame:
        """Get returns distribution (histogram bins)"""
        query = """
            SELECT 
                CAST(bin_start AS REAL) as bin_start,
                CAST(bin_end AS REAL) as bin_end,
                CAST(count AS INTEGER) as count,
                CAST(percentage AS REAL) as percentage
            FROM returns_distribution
            WHERE strategy_name = ?
            ORDER BY bin_start
        """
        df = pd.read_sql_query(query, self.conn, params=(strategy_name,))
        
        # Ensure numeric types
        if not df.empty:
            df['bin_start'] = pd.to_numeric(df['bin_start'], errors='coerce')
            df['bin_end'] = pd.to_numeric(df['bin_end'], errors='coerce')
            df['count'] = pd.to_numeric(df['count'], errors='coerce')
            df['percentage'] = pd.to_numeric(df['percentage'], errors='coerce')
        
        return df
    
    def get_stock_performance(self, strategy_name: str) -> pd.DataFrame:
        """Get per-stock performance"""
        query = """
            SELECT * FROM stock_performance_cache
            WHERE strategy_name = ?
            ORDER BY net_profit_loss DESC
        """
        return pd.read_sql_query(query, self.conn, params=(strategy_name,))
    
    def get_chart_data(self, strategy_name: str, chart_type: str) -> Optional[Dict[str, Any]]:
        """
        Get pre-computed chart data
        
        Args:
            strategy_name: Strategy name
            chart_type: One of: equity_curve, drawdown_curve
        
        Returns:
            dict: Chart data or None
        """
        cursor = self.conn.cursor()
        chart_id = f"{strategy_name}_{chart_type}"
        
        cursor.execute(
            "SELECT chart_data FROM chart_cache WHERE chart_id = ?",
            (chart_id,)
        )
        
        row = cursor.fetchone()
        if row:
            try:
                # Handle potential byte encoding issues
                chart_data = row[0]
                if isinstance(chart_data, bytes):
                    try:
                        chart_data = chart_data.decode('utf-8')
                    except UnicodeDecodeError:
                        chart_data = chart_data.decode('latin-1')
                return json.loads(chart_data)
            except (json.JSONDecodeError, TypeError, AttributeError) as e:
                print(f"Error loading chart data for {chart_id}: {e}")
                return None
        return None
    
    def compare_strategies(self) -> pd.DataFrame:
        """Get comparison data for all strategies"""
        query = """
            SELECT 
                strategy_name,
                total_return_pct,
                annualized_return_pct,
                win_rate_pct,
                sharpe_ratio,
                sortino_ratio,
                max_drawdown_pct,
                profit_factor,
                completed_trades,
                total_profit_dollars
            FROM strategy_summary
            ORDER BY total_return_pct DESC
        """
        return pd.read_sql_query(query, self.conn)
    
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