# ============================================================================
# FILE 1: visualizer/analysis_reader.py
# ============================================================================

"""
Analysis Database Reader
Reads pre-computed metrics from analysis database
"""

import sqlite3
import json
import pandas as pd
from pathlib import Path


class AnalysisReader:
    """
    Fast reader for analysis databases
    All data is pre-computed - no calculations needed
    """
    
    def __init__(self, analysis_db_path):
        """
        Initialize reader
        
        Args:
            analysis_db_path: Path to analysis database
        """
        self.db_path = Path(analysis_db_path)
        
        if not self.db_path.exists():
            raise FileNotFoundError(f"Analysis database not found: {analysis_db_path}")
        
        # CRITICAL FIX: Set proper connection settings
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row  # Enable column access by name
        
        # Enable proper type detection
        self.conn.execute("PRAGMA encoding = 'UTF-8'")
        
        # Load strategy list
        self._strategies = self._load_strategies()
        
        print(f"📊 Loaded analysis: {self.db_path.name}")
        print(f"   Strategies: {len(self._strategies)}")

    def _load_strategies(self):
        """Load list of strategies"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT strategy_name FROM strategy_summary ORDER BY strategy_name")
        return [row[0] for row in cursor.fetchall()]
    
    def get_strategies(self):
        """Get list of all strategies"""
        return self._strategies
    
    def get_summary(self, strategy_name):
        """
        Get complete summary for a strategy
        
        Returns:
            dict: All metrics
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM strategy_summary WHERE strategy_name = ?", (strategy_name,))
        
        row = cursor.fetchone()
        if not row:
            return {}
        
        # Get column names
        cursor.execute("PRAGMA table_info(strategy_summary)")
        columns = [col[1] for col in cursor.fetchall()]
        
        # Create dict
        return dict(zip(columns, row))
    
    def get_monthly_returns(self, strategy_name):
        """Get monthly returns"""
        query = """
            SELECT year_month, return_pct, num_trades, win_rate_pct
            FROM monthly_returns
            WHERE strategy_name = ?
            ORDER BY year_month
        """
        return pd.read_sql_query(query, self.conn, params=(strategy_name,))
    
    def get_drawdown_periods(self, strategy_name):
        """Get significant drawdown periods"""
        query = """
            SELECT * FROM drawdown_periods
            WHERE strategy_name = ?
            ORDER BY drawdown_pct DESC
            LIMIT 5
        """
        return pd.read_sql_query(query, self.conn, params=(strategy_name,))
    
    def get_returns_distribution(self, strategy_name):
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

    def get_stock_performance(self, strategy_name, top_n=10):
        """Get top/bottom stock performance"""
        query = """
            SELECT * FROM stock_performance_cache
            WHERE strategy_name = ?
            ORDER BY net_profit_loss DESC
        """
        df = pd.read_sql_query(query, self.conn, params=(strategy_name,))
        
        if df.empty:
            return pd.DataFrame(), pd.DataFrame()
        
        top = df.head(top_n)
        bottom = df.tail(top_n)
        
        return top, bottom
    
    def get_chart_data(self, strategy_name, chart_type):
        """Get pre-computed chart data"""
        cursor = self.conn.cursor()
        
        chart_id = f"{strategy_name}_{chart_type}"
        cursor.execute(
            "SELECT chart_data FROM chart_cache WHERE chart_id = ?",
            (chart_id,)
        )
        
        row = cursor.fetchone()
        if row:
            return json.loads(row[0])
        return None
    
    def get_metadata(self):
        """Get analysis metadata"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT key, value FROM analysis_metadata")
        return dict(cursor.fetchall())
    
    def compare_strategies(self):
        """Get comparison data for all strategies"""
        query = """
            SELECT 
                strategy_name,
                total_return_pct,
                win_rate_pct,
                sharpe_ratio,
                max_drawdown_pct,
                profit_factor,
                completed_trades
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