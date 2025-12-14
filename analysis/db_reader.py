"""
Database Reader - Pure SQLite reading layer for analysis
NO dependency on simulator code - reads everything from database

Replace your existing db_reader.py with this file
"""

import sqlite3
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime


class SimulationReader:
    """
    Read simulation data from SQLite database
    NO dependencies on simulator code
    """
    
    def __init__(self, db_path):
        """Initialize reader with database path"""
        self.db_path = Path(db_path)
        
        if not self.db_path.exists():
            raise FileNotFoundError(f"Database not found: {db_path}")
        
        self.conn = sqlite3.connect(str(self.db_path))
        
        # Load simulation info
        self.sim_info = self._load_simulation_info()
        
    def _load_simulation_info(self):
        """Load basic simulation information"""
        try:
            query = "SELECT * FROM simulation_info"
            df = pd.read_sql_query(query, self.conn)
            
            if df.empty:
                return {}
            
            return df.iloc[0].to_dict()
        except Exception as e:
            print(f"Warning: Could not load simulation_info: {e}")
            return {}
    
    def get_simulation_id(self):
        """Get simulation ID"""
        return self.sim_info.get('simulation_id', 'unknown')
    
    def get_universe(self):
        """Get universe name"""
        return self.sim_info.get('universe_name', 'unknown')
    
    def get_num_symbols(self):
        """Get number of symbols"""
        return self.sim_info.get('num_symbols', 0)
    
    def get_date_range(self):
        """Get simulation date range"""
        return {
            'start': self.sim_info.get('date_range_start', 'unknown'),
            'end': self.sim_info.get('date_range_end', 'unknown')
        }
    
    def get_initial_cash(self):
        """Get initial cash from database"""
        return self.sim_info.get('initial_cash', 100000)
    
    def list_strategies(self):
        """Get list of all strategies in simulation"""
        try:
            query = "SELECT DISTINCT strategy_name FROM strategy_performance"
            df = pd.read_sql_query(query, self.conn)
            return df['strategy_name'].tolist()
        except Exception as e:
            print(f"Error listing strategies: {e}")
            return []
    
    def get_strategy_performance(self, strategy_name):
        """
        Get complete performance metrics for a strategy
        
        Returns:
            dict: All performance metrics from database
        """
        try:
            query = """
                SELECT * FROM strategy_performance 
                WHERE strategy_name = ?
            """
            df = pd.read_sql_query(query, self.conn, params=(strategy_name,))
            
            if df.empty:
                return None
            
            return df.iloc[0].to_dict()
        except Exception as e:
            print(f"Error getting strategy performance: {e}")
            return None
    
    def get_all_strategy_performance(self):
        """Get performance for all strategies"""
        try:
            query = "SELECT * FROM strategy_performance ORDER BY total_return_pct DESC"
            return pd.read_sql_query(query, self.conn)
        except Exception as e:
            print(f"Error getting all strategy performance: {e}")
            return pd.DataFrame()
    
    def get_portfolio_history(self, strategy_name):
        """
        Get portfolio value history over time
        
        Returns:
            DataFrame with columns: date, portfolio_value, cash, positions_value
        """
        try:
            query = """
                SELECT * FROM portfolio_history 
                WHERE strategy_name = ?
                ORDER BY date
            """
            df = pd.read_sql_query(query, self.conn, params=(strategy_name,))
            
            if df.empty:
                return df
            
            # Convert date strings to datetime
            df['date'] = pd.to_datetime(df['date'])
            
            return df
        except Exception as e:
            print(f"Error getting portfolio history: {e}")
            return pd.DataFrame()
    
    def get_trade_history(self, strategy_name, status=None):
        """
        Get trade history for a strategy
        
        Args:
            strategy_name: Strategy to get trades for
            status: Optional filter ('OPEN', 'CLOSED', or None for all)
        
        Returns:
            DataFrame with all trade details
        """
        try:
            if status:
                query = """
                    SELECT * FROM trade_history 
                    WHERE strategy_name = ? AND trade_status = ?
                    ORDER BY entry_date
                """
                df = pd.read_sql_query(query, self.conn, params=(strategy_name, status))
            else:
                query = """
                    SELECT * FROM trade_history 
                    WHERE strategy_name = ?
                    ORDER BY entry_date
                """
                df = pd.read_sql_query(query, self.conn, params=(strategy_name,))
            
            if df.empty:
                return df
            
            # Convert dates
            df['entry_date'] = pd.to_datetime(df['entry_date'])
            if 'exit_date' in df.columns:
                df['exit_date'] = pd.to_datetime(df['exit_date'], errors='coerce')
            
            return df
        except Exception as e:
            print(f"Error getting trade history: {e}")
            return pd.DataFrame()
    
    def get_open_positions(self, strategy_name):
        """Get current open positions"""
        return self.get_trade_history(strategy_name, status='OPEN')
    
    def get_closed_trades(self, strategy_name):
        """Get closed trades only"""
        return self.get_trade_history(strategy_name, status='CLOSED')
    
    def get_winning_trades(self, strategy_name):
        """Get winning trades"""
        closed = self.get_closed_trades(strategy_name)
        if closed.empty:
            return pd.DataFrame()
        return closed[closed['profit_loss_dollars'] > 0]
    
    def get_losing_trades(self, strategy_name):
        """Get losing trades"""
        closed = self.get_closed_trades(strategy_name)
        if closed.empty:
            return pd.DataFrame()
        return closed[closed['profit_loss_dollars'] < 0]
    
    def get_stock_performance(self, strategy_name):
        """
        Get per-stock performance summary
        
        Returns:
            DataFrame with performance by stock
        """
        try:
            trades = self.get_trade_history(strategy_name)
            
            if trades.empty:
                return pd.DataFrame()
            
            # Group by symbol and calculate metrics
            summary = trades.groupby('symbol').agg({
                'entry_price': 'count',  # Number of trades
                'profit_loss_dollars': ['sum', 'mean'],
                'profit_loss_pct': 'mean'
            }).reset_index()
            
            summary.columns = ['symbol', 'num_trades', 'total_pnl', 'avg_pnl', 'avg_pnl_pct']
            
            # Add win rate per stock
            closed = self.get_closed_trades(strategy_name)
            if not closed.empty:
                win_rate = closed.groupby('symbol').apply(
                    lambda x: (x['profit_loss_dollars'] > 0).sum() / len(x) * 100 if len(x) > 0 else 0
                ).reset_index()
                win_rate.columns = ['symbol', 'win_rate']
                summary = summary.merge(win_rate, on='symbol', how='left')
            
            return summary.sort_values('total_pnl', ascending=False)
        except Exception as e:
            print(f"Error getting stock performance: {e}")
            return pd.DataFrame()
    
    def calculate_returns_series(self, strategy_name):
        """
        Calculate returns series from portfolio history
        
        Returns:
            pandas Series of percentage returns
        """
        portfolio = self.get_portfolio_history(strategy_name)
        
        if portfolio.empty:
            return pd.Series()
        
        values = portfolio['portfolio_value']
        return values.pct_change().dropna()
    
    def get_summary_stats(self, strategy_name):
        """
        Get comprehensive summary statistics
        Reconstructs metrics from database without tracker
        """
        perf = self.get_strategy_performance(strategy_name)
        
        if not perf:
            return {}
        
        trades = self.get_trade_history(strategy_name)
        closed = self.get_closed_trades(strategy_name)
        open_pos = self.get_open_positions(strategy_name)
        
        # Basic metrics
        stats = {
            'total_return_pct': perf.get('total_return_pct', 0),
            'total_profit_dollars': perf.get('total_profit_dollars', 0),
            'initial_cash': self.get_initial_cash(),
            'final_value': self.get_initial_cash() + perf.get('total_profit_dollars', 0),
            
            # Trade counts
            'total_trades': len(trades),
            'completed_trades': len(closed),
            'open_positions': len(open_pos),
            
            # Win rate (from closed trades only)
            'win_rate_pct': perf.get('win_rate_pct', 0),
            'winning_trades': perf.get('winning_trades', 0),
            'losing_trades': perf.get('losing_trades', 0),
            
            # Risk metrics
            'sharpe_ratio': perf.get('sharpe_ratio', 0),
            'sortino_ratio': perf.get('sortino_ratio', 0),
            'max_drawdown_pct': perf.get('max_drawdown_pct', 0),
            'calmar_ratio': perf.get('calmar_ratio', 0),
            
            # Trade metrics
            'profit_factor': perf.get('profit_factor', 0),
            'avg_win_dollars': perf.get('avg_win_dollars', 0),
            'avg_loss_dollars': perf.get('avg_loss_dollars', 0),
            'expectancy_dollars': perf.get('expectancy_dollars', 0),
            
            # Market exposure
            'beta': perf.get('beta'),
            'alpha_pct': perf.get('alpha_pct'),
            'information_ratio': perf.get('information_ratio'),
            
            # Date range
            'start_date': self.get_date_range()['start'],
            'end_date': self.get_date_range()['end']
        }
        
        return stats
    
    def compare_strategies(self):
        """
        Compare all strategies in simulation
        
        Returns:
            DataFrame with comparative metrics
        """
        strategies = self.get_all_strategy_performance()
        
        if strategies.empty:
            return pd.DataFrame()
        
        # Select key comparison metrics
        columns = [
            'strategy_name',
            'total_return_pct',
            'total_profit_dollars',
            'sharpe_ratio',
            'max_drawdown_pct',
            'win_rate_pct',
            'profit_factor',
            'total_trades'
        ]
        
        # Only include columns that exist
        available_cols = [col for col in columns if col in strategies.columns]
        comparison = strategies[available_cols].copy()
        
        return comparison.sort_values('total_return_pct', ascending=False)
    
    def get_benchmark_comparison(self, strategy_name):
        """
        Get strategy vs benchmark comparison
        Assumes SPY is the benchmark
        """
        # Get strategy performance
        strategy_perf = self.get_strategy_performance(strategy_name)
        
        if not strategy_perf:
            return None
        
        # Get SPY performance (if exists)
        spy_perf = self.get_strategy_performance('SPY')
        
        if not spy_perf:
            return None
        
        comparison = {
            'strategy': {
                'name': strategy_name,
                'return': strategy_perf.get('total_return_pct', 0),
                'sharpe': strategy_perf.get('sharpe_ratio', 0),
                'max_dd': strategy_perf.get('max_drawdown_pct', 0)
            },
            'benchmark': {
                'name': 'S&P 500',
                'return': spy_perf.get('total_return_pct', 0),
                'sharpe': spy_perf.get('sharpe_ratio', 0),
                'max_dd': spy_perf.get('max_drawdown_pct', 0)
            },
            'excess': {
                'return': strategy_perf.get('total_return_pct', 0) - spy_perf.get('total_return_pct', 0),
                'sharpe': strategy_perf.get('sharpe_ratio', 0) - spy_perf.get('sharpe_ratio', 0)
            }
        }
        
        return comparison
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
    
    def __enter__(self):
        """Context manager support"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager cleanup"""
        self.close()


def load_simulation(db_path):
    """
    Load a simulation from database
    
    Usage:
        reader = load_simulation('simulations/simulation_20251213_152200_sp500.db')
        stats = reader.get_summary_stats('500 Intersection')
    """
    return SimulationReader(db_path)


# Quick test
if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python db_reader.py <path_to_simulation.db>")
        sys.exit(1)
    
    db_path = sys.argv[1]
    
    print(f"\n{'='*70}")
    print(f"TESTING DATABASE READER: {db_path}")
    print(f"{'='*70}\n")
    
    try:
        reader = SimulationReader(db_path)
        
        print(f"Simulation ID: {reader.get_simulation_id()}")
        print(f"Universe: {reader.get_universe()}")
        print(f"Symbols: {reader.get_num_symbols()}")
        print(f"Date Range: {reader.get_date_range()}")
        print(f"Initial Cash: ${reader.get_initial_cash():,}")
        
        strategies = reader.list_strategies()
        print(f"\nStrategies ({len(strategies)}):")
        for strat in strategies:
            print(f"  - {strat}")
            stats = reader.get_summary_stats(strat)
            if stats:
                print(f"    Return: {stats['total_return_pct']:+.2f}%")
                print(f"    Profit: ${stats['total_profit_dollars']:+,.0f}")
                print(f"    Trades: {stats['completed_trades']}")
                print(f"    Win Rate: {stats['win_rate_pct']:.1f}%")
        
        reader.close()
        
        print(f"\n✅ Database reader test successful!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()