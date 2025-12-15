"""
Modern Database Reader - Complete Database Access Layer
Reads from ALL 9 tables in the simulation database
NO mock objects - direct database access only

Tables covered:
1. simulation_info
2. strategy_performance  
3. trade_history
4. trade_attempts
5. portfolio_history
6. stock_performance
7. execution_log
8. strategy_configs
9. indicator_history
"""

import sqlite3
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
from functools import lru_cache


class SimulationReader:
    """
    Modern database reader for simulation analysis
    Provides direct access to all database tables
    """
    
    def __init__(self, db_path):
        """Initialize reader with database path"""
        self.db_path = Path(db_path)
        
        if not self.db_path.exists():
            raise FileNotFoundError(f"Database not found: {db_path}")
        
        self.conn = sqlite3.connect(str(self.db_path))
        self._sim_info = None  # Cached simulation info
        
    # ============================================================
    # SIMULATION INFO
    # ============================================================
    
    @property
    def sim_info(self):
        """Lazy-load simulation info (cached)"""
        if self._sim_info is None:
            try:
                query = "SELECT * FROM simulation_info LIMIT 1"
                df = pd.read_sql_query(query, self.conn)
                self._sim_info = df.iloc[0].to_dict() if not df.empty else {}
            except Exception as e:
                print(f"Warning: Could not load simulation_info: {e}")
                self._sim_info = {}
        return self._sim_info
    
    def get_simulation_id(self):
        """Get simulation ID"""
        return self.sim_info.get('simulation_id', 'unknown')
    
    def get_universe(self):
        """Get universe name (e.g., 'sp500', 'nasdaq100')"""
        return self.sim_info.get('universe_name', 'unknown')
    
    def get_num_symbols(self):
        """Get number of symbols in simulation"""
        return self.sim_info.get('num_symbols', 0)
    
    def get_date_range(self):
        """Get simulation date range"""
        return {
            'start': self.sim_info.get('date_range_start', 'unknown'),
            'end': self.sim_info.get('date_range_end', 'unknown')
        }
    
    def get_initial_cash(self):
        """Get initial capital"""
        return self.sim_info.get('initial_capital', 100000)
    
    def get_config_json(self):
        """Get simulation configuration as JSON string"""
        return self.sim_info.get('config_json', '{}')
    
    # ============================================================
    # STRATEGY MANAGEMENT
    # ============================================================
    
    def list_strategies(self):
        """Get list of all strategies in simulation"""
        try:
            query = "SELECT DISTINCT strategy_name FROM strategy_performance ORDER BY strategy_name"
            df = pd.read_sql_query(query, self.conn)
            return df['strategy_name'].tolist()
        except Exception as e:
            print(f"Error listing strategies: {e}")
            return []
    
    # ============================================================
    # TABLE 2: STRATEGY PERFORMANCE
    # ============================================================
    
    def get_strategy_performance(self, strategy_name):
        """
        Get complete performance metrics for a strategy from strategy_performance table
        
        Returns:
            dict: All performance metrics (or None if not found)
        """
        try:
            query = "SELECT * FROM strategy_performance WHERE strategy_name = ?"
            df = pd.read_sql_query(query, self.conn, params=(strategy_name,))
            return df.iloc[0].to_dict() if not df.empty else None
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
    
    def compare_strategies(self):
        """Compare all strategies (sorted by return)"""
        return self.get_all_strategy_performance()
    
    # ============================================================
    # TABLE 3: TRADE HISTORY
    # ============================================================
    
    def get_trade_history(self, strategy_name, status=None):
        """
        Get trade history for a strategy
        
        Args:
            strategy_name: Strategy name
            status: Optional filter ('OPEN', 'CLOSED', or None for all)
        
        Returns:
            DataFrame with all trade details including volume data
        """
        try:
            if status:
                query = """
                    SELECT * FROM trade_history 
                    WHERE strategy_name = ? AND trade_status = ?
                    ORDER BY entry_timestamp
                """
                df = pd.read_sql_query(query, self.conn, params=(strategy_name, status))
            else:
                query = """
                    SELECT * FROM trade_history 
                    WHERE strategy_name = ?
                    ORDER BY entry_timestamp
                """
                df = pd.read_sql_query(query, self.conn, params=(strategy_name,))
            
            if not df.empty:
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
        return closed[closed['profit_loss_dollars'] > 0] if not closed.empty else pd.DataFrame()
    
    def get_losing_trades(self, strategy_name):
        """Get losing trades"""
        closed = self.get_closed_trades(strategy_name)
        return closed[closed['profit_loss_dollars'] < 0] if not closed.empty else pd.DataFrame()
    
    def get_trades_by_symbol(self, strategy_name, symbol):
        """Get all trades for a specific symbol"""
        try:
            query = """
                SELECT * FROM trade_history 
                WHERE strategy_name = ? AND symbol = ?
                ORDER BY entry_timestamp
            """
            df = pd.read_sql_query(query, self.conn, params=(strategy_name, symbol))
            if not df.empty:
                df['entry_date'] = pd.to_datetime(df['entry_date'])
                df['exit_date'] = pd.to_datetime(df['exit_date'], errors='coerce')
            return df
        except Exception as e:
            print(f"Error getting trades by symbol: {e}")
            return pd.DataFrame()
    
    def get_forced_exits(self, strategy_name):
        """Get trades that were force-closed at simulation end"""
        try:
            query = """
                SELECT * FROM trade_history 
                WHERE strategy_name = ? AND forced_exit = 1
                ORDER BY entry_timestamp
            """
            return pd.read_sql_query(query, self.conn, params=(strategy_name,))
        except Exception as e:
            print(f"Error getting forced exits: {e}")
            return pd.DataFrame()
    
    # ============================================================
    # TABLE 4: TRADE ATTEMPTS (NEW!)
    # ============================================================
    
    def get_trade_attempts(self, strategy_name, success=None):
        """
        Get ALL trade attempts including rejections
        
        Args:
            strategy_name: Strategy name
            success: Optional filter (True, False, or None for all)
        
        Returns:
            DataFrame with all attempted trades
        """
        try:
            if success is not None:
                query = """
                    SELECT * FROM trade_attempts 
                    WHERE strategy_name = ? AND success = ?
                    ORDER BY timestamp
                """
                df = pd.read_sql_query(query, self.conn, params=(strategy_name, int(success)))
            else:
                query = """
                    SELECT * FROM trade_attempts 
                    WHERE strategy_name = ?
                    ORDER BY timestamp
                """
                df = pd.read_sql_query(query, self.conn, params=(strategy_name,))
            
            if not df.empty:
                df['date'] = pd.to_datetime(df['date'])
            
            return df
        except Exception as e:
            print(f"Error getting trade attempts: {e}")
            return pd.DataFrame()
    
    def get_rejected_attempts(self, strategy_name):
        """Get only rejected trade attempts"""
        return self.get_trade_attempts(strategy_name, success=False)
    
    def get_rejection_analysis(self, strategy_name):
        """
        Analyze why trades were rejected
        
        Returns:
            dict: Rejection statistics and reasons
        """
        attempts = self.get_trade_attempts(strategy_name)
        
        if attempts.empty:
            return {}
        
        total = len(attempts)
        successful = attempts['success'].sum()
        rejected = total - successful
        
        # Group by rejection reason
        rejections = attempts[attempts['success'] == False]
        rejection_reasons = rejections['rejection_reason'].value_counts().to_dict()
        
        # Analyze rejection patterns
        return {
            'total_attempts': total,
            'successful': successful,
            'rejected': rejected,
            'rejection_rate_pct': (rejected / total * 100) if total > 0 else 0,
            'rejection_reasons': rejection_reasons,
            'most_common_rejection': rejections['rejection_reason'].mode()[0] if not rejections.empty else None
        }
    
    # ============================================================
    # TABLE 5: PORTFOLIO HISTORY
    # ============================================================
    
    def get_portfolio_history(self, strategy_name):
        """
        Get portfolio value history over time (bar-by-bar)
        
        Returns:
            DataFrame with columns: date, portfolio_value, cash, positions_value, num_positions
        """
        try:
            query = """
                SELECT * FROM portfolio_history 
                WHERE strategy_name = ?
                ORDER BY timestamp
            """
            df = pd.read_sql_query(query, self.conn, params=(strategy_name,))
            
            if not df.empty:
                df['date'] = pd.to_datetime(df['date'])
            
            return df
        except Exception as e:
            print(f"Error getting portfolio history: {e}")
            return pd.DataFrame()
    
    def get_portfolio_at_date(self, strategy_name, date):
        """Get portfolio state at specific date"""
        try:
            query = """
                SELECT * FROM portfolio_history 
                WHERE strategy_name = ? AND date = ?
            """
            df = pd.read_sql_query(query, self.conn, params=(strategy_name, date))
            return df.iloc[0].to_dict() if not df.empty else None
        except Exception as e:
            print(f"Error getting portfolio at date: {e}")
            return None
    
    # ============================================================
    # TABLE 6: STOCK PERFORMANCE (NEW!)
    # ============================================================
    
    def get_stock_performance(self, strategy_name):
        """
        Get per-symbol performance summary DIRECTLY from table
        (No calculation needed - reads pre-computed data)
        
        Returns:
            DataFrame with performance by stock
        """
        try:
            query = """
                SELECT * FROM stock_performance 
                WHERE strategy_name = ?
                ORDER BY net_profit_loss DESC
            """
            return pd.read_sql_query(query, self.conn, params=(strategy_name,))
        except Exception as e:
            print(f"Error getting stock performance: {e}")
            return pd.DataFrame()
    
    def get_best_stocks(self, strategy_name, limit=10):
        """Get top N best performing stocks"""
        perf = self.get_stock_performance(strategy_name)
        return perf.head(limit) if not perf.empty else pd.DataFrame()
    
    def get_worst_stocks(self, strategy_name, limit=10):
        """Get top N worst performing stocks"""
        perf = self.get_stock_performance(strategy_name)
        return perf.tail(limit) if not perf.empty else pd.DataFrame()
    
    # ============================================================
    # TABLE 7: EXECUTION LOG (NEW!)
    # ============================================================
    
    def get_execution_log(self, strategy_name, symbol=None, action=None):
        """
        Get bar-by-bar execution log for debugging
        
        Args:
            strategy_name: Strategy name
            symbol: Optional symbol filter
            action: Optional action filter
        
        Returns:
            DataFrame with execution timeline
        """
        try:
            query = """
                SELECT * FROM execution_log 
                WHERE strategy_name = ?
            """
            params = [strategy_name]
            
            if symbol:
                query += " AND symbol = ?"
                params.append(symbol)
            
            if action:
                query += " AND action = ?"
                params.append(action)
            
            query += " ORDER BY timestamp"
            
            df = pd.read_sql_query(query, self.conn, params=params)
            
            if not df.empty:
                df['date'] = pd.to_datetime(df['date'])
            
            return df
        except Exception as e:
            print(f"Error getting execution log: {e}")
            return pd.DataFrame()
    
    def get_execution_timeline(self, strategy_name, start_date=None, end_date=None):
        """Get execution log for a specific time period"""
        try:
            query = """
                SELECT * FROM execution_log 
                WHERE strategy_name = ?
            """
            params = [strategy_name]
            
            if start_date:
                query += " AND date >= ?"
                params.append(start_date)
            
            if end_date:
                query += " AND date <= ?"
                params.append(end_date)
            
            query += " ORDER BY timestamp"
            
            df = pd.read_sql_query(query, self.conn, params=params)
            
            if not df.empty:
                df['date'] = pd.to_datetime(df['date'])
            
            return df
        except Exception as e:
            print(f"Error getting execution timeline: {e}")
            return pd.DataFrame()
    
    # ============================================================
    # TABLE 8: STRATEGY CONFIGS (NEW!)
    # ============================================================
    
    def get_strategy_config(self, strategy_name):
        """
        Get strategy configuration and parameters
        
        Returns:
            dict: Strategy configuration
        """
        try:
            query = "SELECT * FROM strategy_configs WHERE strategy_name = ?"
            df = pd.read_sql_query(query, self.conn, params=(strategy_name,))
            
            if df.empty:
                return None
            
            config = df.iloc[0].to_dict()
            
            # Parse JSON parameters if present
            if 'parameters_json' in config and config['parameters_json']:
                import json
                try:
                    config['parameters'] = json.loads(config['parameters_json'])
                except:
                    config['parameters'] = {}
            
            return config
        except Exception as e:
            print(f"Error getting strategy config: {e}")
            return None
    
    def get_all_strategy_configs(self):
        """Get configurations for all strategies"""
        try:
            query = "SELECT * FROM strategy_configs ORDER BY strategy_name"
            return pd.read_sql_query(query, self.conn)
        except Exception as e:
            print(f"Error getting all strategy configs: {e}")
            return pd.DataFrame()
    
    # ============================================================
    # TABLE 9: INDICATOR HISTORY (NEW!)
    # ============================================================
    
    def get_indicator_history(self, strategy_name, symbol=None, indicator_name=None):
        """
        Get indicator values over time
        
        Args:
            strategy_name: Strategy name
            symbol: Optional symbol filter
            indicator_name: Optional indicator name filter (e.g., 'rsi_14')
        
        Returns:
            DataFrame with indicator values
        """
        try:
            query = """
                SELECT * FROM indicator_history 
                WHERE strategy_name = ?
            """
            params = [strategy_name]
            
            if symbol:
                query += " AND symbol = ?"
                params.append(symbol)
            
            if indicator_name:
                query += " AND indicator_name = ?"
                params.append(indicator_name)
            
            query += " ORDER BY timestamp"
            
            df = pd.read_sql_query(query, self.conn, params=params)
            
            if not df.empty:
                df['date'] = pd.to_datetime(df['date'])
            
            return df
        except Exception as e:
            print(f"Error getting indicator history: {e}")
            return pd.DataFrame()
    
    def get_available_indicators(self, strategy_name):
        """Get list of available indicators for a strategy"""
        try:
            query = """
                SELECT DISTINCT indicator_name FROM indicator_history 
                WHERE strategy_name = ?
                ORDER BY indicator_name
            """
            df = pd.read_sql_query(query, self.conn, params=(strategy_name,))
            return df['indicator_name'].tolist() if not df.empty else []
        except Exception as e:
            print(f"Error getting available indicators: {e}")
            return []
    
    def get_indicator_at_trades(self, strategy_name, indicator_name):
        """
        Get indicator values at entry/exit times for all trades
        
        Returns:
            DataFrame with trades and corresponding indicator values
        """
        try:
            # Get trades
            trades = self.get_closed_trades(strategy_name)
            
            if trades.empty:
                return pd.DataFrame()
            
            # Get indicator values
            indicators = self.get_indicator_history(strategy_name, indicator_name=indicator_name)
            
            if indicators.empty:
                return pd.DataFrame()
            
            # Merge on timestamp/date
            # This is simplified - in practice you'd need to match timestamps carefully
            result = []
            
            for _, trade in trades.iterrows():
                entry_date = trade['entry_date']
                
                # Find nearest indicator value
                ind_at_entry = indicators[indicators['symbol'] == trade['symbol']]
                ind_at_entry = ind_at_entry[ind_at_entry['date'] <= entry_date].tail(1)
                
                if not ind_at_entry.empty:
                    result.append({
                        'symbol': trade['symbol'],
                        'entry_date': entry_date,
                        'indicator_value': ind_at_entry.iloc[0]['indicator_value'],
                        'profit_loss_pct': trade['profit_loss_pct']
                    })
            
            return pd.DataFrame(result)
        except Exception as e:
            print(f"Error getting indicator at trades: {e}")
            return pd.DataFrame()
    
    # ============================================================
    # VOLUME ANALYSIS
    # ============================================================
    
    def get_volume_analysis(self, strategy_name):
        """
        Analyze volume patterns in trades
        
        Returns:
            dict: Volume statistics
        """
        trades = self.get_closed_trades(strategy_name)
        
        if trades.empty or 'entry_relative_volume' not in trades.columns:
            return {}
        
        # Filter out trades with no volume data
        valid_trades = trades[trades['entry_relative_volume'].notna()]
        
        if valid_trades.empty:
            return {}
        
        # Analyze by volume categories
        valid_trades['volume_category'] = pd.cut(
            valid_trades['entry_relative_volume'],
            bins=[0, 1.0, 2.0, float('inf')],
            labels=['Low (<1x)', 'Normal (1-2x)', 'High (>2x)']
        )
        
        volume_performance = valid_trades.groupby('volume_category').agg({
            'profit_loss_pct': ['mean', 'count'],
            'profit_loss_dollars': 'sum'
        }).round(2)
        
        return {
            'trades_with_volume_data': len(valid_trades),
            'avg_entry_volume': valid_trades['entry_relative_volume'].mean(),
            'avg_exit_volume': valid_trades['exit_relative_volume'].mean() if 'exit_relative_volume' in valid_trades else None,
            'performance_by_volume': volume_performance.to_dict(),
            'high_volume_trades': len(valid_trades[valid_trades['entry_relative_volume'] > 2.0]),
            'low_volume_trades': len(valid_trades[valid_trades['entry_relative_volume'] < 1.0])
        }
    
    # ============================================================
    # ADVANCED QUERIES & ANALYTICS
    # ============================================================
    
    def get_summary_stats(self, strategy_name):
        """
        Get comprehensive summary statistics
        Returns pre-computed metrics from database
        """
        perf = self.get_strategy_performance(strategy_name)
        
        if not perf:
            return {}
        
        date_range = self.get_date_range()
        
        # Return everything from strategy_performance table
        stats = dict(perf)
        
        # Add date range
        stats['start_date'] = date_range['start']
        stats['end_date'] = date_range['end']
        stats['initial_cash'] = self.get_initial_cash()
        
        return stats
    
    def get_benchmark_comparison(self, strategy_name, benchmark='SPY'):
        """Compare strategy vs benchmark"""
        strategy_perf = self.get_strategy_performance(strategy_name)
        benchmark_perf = self.get_strategy_performance(benchmark)
        
        if not strategy_perf or not benchmark_perf:
            return None
        
        return {
            'strategy': {
                'name': strategy_name,
                'return': strategy_perf.get('total_return_pct', 0),
                'sharpe': strategy_perf.get('sharpe_ratio', 0),
                'max_dd': strategy_perf.get('max_drawdown_pct', 0)
            },
            'benchmark': {
                'name': benchmark,
                'return': benchmark_perf.get('total_return_pct', 0),
                'sharpe': benchmark_perf.get('sharpe_ratio', 0),
                'max_dd': benchmark_perf.get('max_drawdown_pct', 0)
            },
            'excess': {
                'return': strategy_perf.get('total_return_pct', 0) - benchmark_perf.get('total_return_pct', 0),
                'sharpe': strategy_perf.get('sharpe_ratio', 0) - benchmark_perf.get('sharpe_ratio', 0)
            }
        }
    
    def calculate_returns_series(self, strategy_name):
        """Calculate returns series from portfolio history"""
        portfolio = self.get_portfolio_history(strategy_name)
        
        if portfolio.empty:
            return pd.Series()
        
        portfolio = portfolio.set_index('date')
        returns = portfolio['portfolio_value'].pct_change().dropna()
        
        return returns
    
    def get_monthly_returns(self, strategy_name):
        """Calculate monthly returns"""
        returns = self.calculate_returns_series(strategy_name)
        
        if returns.empty:
            return pd.Series()
        
        monthly = returns.groupby(pd.Grouper(freq='ME')).apply(
            lambda x: (1 + x).prod() - 1
        ) * 100
        
        return monthly.dropna()
    
    # ============================================================
    # CROSS-TABLE QUERIES
    # ============================================================
    
    def get_trade_with_indicators(self, strategy_name, trade_id):
        """Get a trade with all associated indicator values"""
        try:
            # Get the trade
            query = "SELECT * FROM trade_history WHERE id = ? AND strategy_name = ?"
            trade = pd.read_sql_query(query, self.conn, params=(trade_id, strategy_name))
            
            if trade.empty:
                return None
            
            trade_data = trade.iloc[0].to_dict()
            
            # Get indicators at entry time
            symbol = trade_data['symbol']
            entry_date = trade_data['entry_date']
            
            indicators = self.get_indicator_history(strategy_name, symbol=symbol)
            
            if not indicators.empty:
                # Find indicators near entry
                indicators['date'] = pd.to_datetime(indicators['date'])
                entry_indicators = indicators[indicators['date'] <= entry_date].tail(5)
                trade_data['indicators_at_entry'] = entry_indicators.to_dict('records')
            
            return trade_data
        except Exception as e:
            print(f"Error getting trade with indicators: {e}")
            return None
    
    def get_full_trade_context(self, strategy_name, symbol, entry_date):
        """
        Get complete context for a trade:
        - Trade details
        - Indicator values
        - Execution log
        - Rejection attempts (if any)
        """
        try:
            context = {}
            
            # Trade details
            trades = self.get_trades_by_symbol(strategy_name, symbol)
            trade = trades[trades['entry_date'] == entry_date]
            context['trade'] = trade.to_dict('records')[0] if not trade.empty else None
            
            # Indicators
            indicators = self.get_indicator_history(strategy_name, symbol=symbol)
            if not indicators.empty:
                indicators['date'] = pd.to_datetime(indicators['date'])
                context['indicators'] = indicators[
                    (indicators['date'] >= entry_date - pd.Timedelta(days=5)) &
                    (indicators['date'] <= entry_date + pd.Timedelta(days=5))
                ].to_dict('records')
            
            # Execution log
            exec_log = self.get_execution_log(strategy_name, symbol=symbol)
            if not exec_log.empty:
                exec_log['date'] = pd.to_datetime(exec_log['date'])
                context['execution'] = exec_log[
                    (exec_log['date'] >= entry_date - pd.Timedelta(days=1)) &
                    (exec_log['date'] <= entry_date + pd.Timedelta(days=1))
                ].to_dict('records')
            
            # Trade attempts
            attempts = self.get_trade_attempts(strategy_name)
            if not attempts.empty:
                attempts['date'] = pd.to_datetime(attempts['date'])
                context['attempts'] = attempts[
                    (attempts['symbol'] == symbol) &
                    (attempts['date'] >= entry_date - pd.Timedelta(days=1)) &
                    (attempts['date'] <= entry_date + pd.Timedelta(days=1))
                ].to_dict('records')
            
            return context
        except Exception as e:
            print(f"Error getting full trade context: {e}")
            return {}
    
    # ============================================================
    # UTILITIES
    # ============================================================
    
    def get_table_info(self, table_name):
        """Get information about a table structure"""
        try:
            query = f"PRAGMA table_info({table_name})"
            return pd.read_sql_query(query, self.conn)
        except Exception as e:
            print(f"Error getting table info: {e}")
            return pd.DataFrame()
    
    def list_all_tables(self):
        """List all tables in database"""
        try:
            query = "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            df = pd.read_sql_query(query, self.conn)
            return df['name'].tolist()
        except Exception as e:
            print(f"Error listing tables: {e}")
            return []
    
    def execute_custom_query(self, query, params=None):
        """Execute a custom SQL query"""
        try:
            if params:
                return pd.read_sql_query(query, self.conn, params=params)
            else:
                return pd.read_sql_query(query, self.conn)
        except Exception as e:
            print(f"Error executing custom query: {e}")
            return pd.DataFrame()
    
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
    
    def __repr__(self):
        """String representation"""
        return f"SimulationReader(db='{self.db_path.name}', universe='{self.get_universe()}', strategies={len(self.list_strategies())})"


# ============================================================
# CONVENIENCE FUNCTIONS
# ============================================================

def load_simulation(db_path):
    """
    Load a simulation from database
    
    Usage:
        reader = load_simulation('simulations/simulation_20251213_152200_sp500.db')
        stats = reader.get_summary_stats('My Strategy')
    """
    return SimulationReader(db_path)


def quick_summary(db_path):
    """Print quick summary of a simulation"""
    with SimulationReader(db_path) as reader:
        print(f"\n{'='*70}")
        print(f"SIMULATION: {reader.db_path.name}")
        print(f"{'='*70}")
        print(f"Universe: {reader.get_universe()}")
        print(f"Symbols: {reader.get_num_symbols()}")
        print(f"Date Range: {reader.get_date_range()['start']} to {reader.get_date_range()['end']}")
        print(f"Initial Capital: ${reader.get_initial_cash():,}")
        
        strategies = reader.list_strategies()
        print(f"\nStrategies ({len(strategies)}):")
        
        for strat in strategies:
            stats = reader.get_summary_stats(strat)
            if stats:
                print(f"\n  📊 {strat}")
                print(f"     Return: {stats['total_return_pct']:+.2f}%")
                print(f"     Profit: ${stats['total_profit_dollars']:+,.0f}")
                print(f"     Trades: {stats['completed_trades']} completed, {stats['open_positions']} open")
                print(f"     Win Rate: {stats['win_rate_pct']:.1f}%")
                print(f"     Sharpe: {stats['sharpe_ratio']:.3f}")
        
        print(f"\n{'='*70}\n")


# ============================================================
# TESTING
# ============================================================

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python db_reader.py <path_to_simulation.db>")
        sys.exit(1)
    
    db_path = sys.argv[1]
    
    try:
        quick_summary(db_path)
        
        # Test new features
        with SimulationReader(db_path) as reader:
            strategies = reader.list_strategies()
            
            if strategies:
                strat = strategies[0]
                print(f"\n🔍 TESTING NEW FEATURES FOR: {strat}\n")
                
                # Test rejection analysis
                rejection_stats = reader.get_rejection_analysis(strat)
                if rejection_stats:
                    print(f"✅ Rejection Analysis:")
                    print(f"   Total Attempts: {rejection_stats['total_attempts']}")
                    print(f"   Rejection Rate: {rejection_stats['rejection_rate_pct']:.1f}%")
                
                # Test stock performance table
                stock_perf = reader.get_stock_performance(strat)
                print(f"\n✅ Stock Performance Table: {len(stock_perf)} stocks")
                
                # Test volume analysis
                volume_stats = reader.get_volume_analysis(strat)
                if volume_stats:
                    print(f"\n✅ Volume Analysis:")
                    print(f"   Trades with Volume Data: {volume_stats['trades_with_volume_data']}")
                
                # Test available indicators
                indicators = reader.get_available_indicators(strat)
                if indicators:
                    print(f"\n✅ Available Indicators: {', '.join(indicators)}")
        
        print("\n✅ All tests passed!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()