# ============================================================================
# FILE 7: analysis_engine.py - MAIN ORCHESTRATOR
# ============================================================================

"""
Analysis Engine - Main Orchestrator
Runs all calculators and stores results in analysis database

Usage:
    python analysis_engine.py --sim ../simulator/simulations/latest.db
    python analysis_engine.py --latest
"""

import sqlite3
import argparse
from pathlib import Path
from datetime import datetime
import time
import json

# Import UTF-8 utilities
from utilities.utf8_helpers import ensure_utf8, get_utf8_connection

# Import database reader and schema
from db_reader import SimulationReader
from analysis_db_schema import create_analysis_database

# Import all calculators
from calculators.trade_metrics import TradeMetricsCalculator
from calculators.risk_metrics import RiskMetricsCalculator
from calculators.drawdown_metrics import DrawdownMetricsCalculator
from calculators.streak_metrics import StreakMetricsCalculator
from calculators.monthly_metrics import MonthlyMetricsCalculator
from calculators.volume_metrics import VolumeMetricsCalculator

# Import processors
from processors.chart_processor import ChartProcessor

# Import progress reporter for API monitoring
try:
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from monitoring.progress_reporter import get_reporter
    MONITORING_AVAILABLE = True
except ImportError:
    MONITORING_AVAILABLE = False
    get_reporter = None


class AnalysisEngine:
    """
    Main Analysis Engine
    Orchestrates all metric calculations and database writes
    """
    
    def __init__(self, simulation_db_path):
        """
        Initialize engine
        
        Args:
            simulation_db_path: Path to simulation database
        """
        self.sim_db_path = Path(simulation_db_path)
        
        if not self.sim_db_path.exists():
            raise FileNotFoundError(f"Simulation database not found: {simulation_db_path}")
        
        # Open simulation database
        self.reader = SimulationReader(self.sim_db_path)
        
        # Create analysis database path
        self.analysis_db_path = self._create_analysis_db_path()
        
        # Create analysis database
        create_analysis_database(self.analysis_db_path)
        
        # Connect to analysis database with UTF-8 safety
        self.conn = get_utf8_connection(str(self.analysis_db_path))

        # Initialize progress reporter for API monitoring
        self.reporter = None
        self.process_id = None
        if MONITORING_AVAILABLE:
            try:
                self.reporter = get_reporter()
            except Exception as e:
                print(f"   Warning: Could not initialize progress reporting: {e}")
                self.reporter = None

        print(f"📊 ANALYSIS ENGINE")
        print(f"   Input:  {self.sim_db_path.name}")
        print(f"   Output: {self.analysis_db_path.name}")
        print(f"{'='*70}")
    
    def _create_analysis_db_path(self):
        """Create path for analysis database"""
        analysis_dir = Path(__file__).parent / 'analysis_dbs'
        analysis_dir.mkdir(exist_ok=True)
        
        # Get simulation ID from database
        sim_id = self.reader.get_simulation_id()
        
        # Create filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        db_name = f'analysis_{timestamp}_{sim_id}.db'
        
        return analysis_dir / db_name
    
    def run_analysis(self):
        """
        Run complete analysis pipeline

        Returns:
            Path: Path to created analysis database
        """
        start_time = time.time()

        # Get all strategies
        strategies = self.reader.list_strategies()

        if not strategies:
            print("❌ No strategies found in simulation database")
            return None

        print(f"\n📈 Found {len(strategies)} strategies:")
        for strat in strategies:
            print(f"   • {strat}")

        # Register analysis process with monitoring API
        # Total items: strategies + benchmark analysis + metadata + optimization = len(strategies) + 3
        total_steps = len(strategies) + 3
        if self.reporter:
            try:
                self.process_id = self.reporter.register(
                    process_type="analysis",
                    total_items=total_steps,
                    metadata={
                        "simulation_db": str(self.sim_db_path.name),
                        "num_strategies": len(strategies),
                        "strategies": strategies
                    }
                )
            except Exception:
                pass  # Silently fail for registration
        
        # Analyze each strategy
        for i, strategy_name in enumerate(strategies, 1):
            print(f"\n[{i}/{len(strategies)}] Analyzing: {strategy_name}")
            self._analyze_strategy(strategy_name)

            # Report progress to monitoring API
            if self.reporter and self.process_id:
                try:
                    self.reporter.update(i, f"Analyzed {strategy_name}")
                except Exception:
                    pass  # Silently fail for progress updates

        # Also analyze SPY benchmark if available
        try:
            self._analyze_benchmark()
            # Report benchmark analysis progress
            if self.reporter and self.process_id:
                try:
                    self.reporter.update(len(strategies) + 1, "SPY benchmark analyzed")
                except Exception:
                    pass
        except Exception as e:
            print(f"⚠️  Could not analyze SPY benchmark: {e}")
        
        # Store metadata
        self._store_metadata()

        # Report metadata stored progress
        if self.reporter and self.process_id:
            try:
                self.reporter.update(len(strategies) + 2, "Metadata stored")
            except Exception:
                pass

        # Optimize database
        self._optimize_database()

        # Report database optimization progress
        if self.reporter and self.process_id:
            try:
                self.reporter.update(len(strategies) + 3, "Database optimized")
            except Exception:
                pass

        # Close connections
        self.conn.close()
        self.reader.close()

        elapsed = time.time() - start_time

        # Mark analysis complete in monitoring API
        if self.reporter and self.process_id:
            try:
                self.reporter.complete(f"Analysis completed in {elapsed:.1f}s")
            except Exception:
                pass  # Silently fail for completion

        print(f"\n{'='*70}")
        print(f"✅ Analysis Complete!")
        print(f"   Time: {elapsed:.1f} seconds")
        print(f"   Database: {self.analysis_db_path.name}")
        print(f"   Size: {self.analysis_db_path.stat().st_size / 1024:.1f} KB")
        print(f"\n📊 To visualize:")
        print(f"   cd ../visualizer && python main.py")
        print(f"{'='*70}\n")

        return self.analysis_db_path
    
    def _analyze_strategy(self, strategy_name):
        """
        Analyze a single strategy using all calculators with error boundaries
        
        Args:
            strategy_name: Strategy to analyze
        """
        timestamp = int(time.time())
        
        # Initialize empty metrics (in case calculators fail)
        trade_metrics = {}
        risk_metrics = {}
        dd_metrics = {}
        dd_periods = []
        streak_metrics = {}
        streak_periods = []
        monthly_data = {}
        volume_metrics = {}
        chart_data = {}
        perf = {}
        
        # 1. Calculate trade metrics
        try:
            print("   📊 Trade metrics...", end=" ", flush=True)
            trade_calc = TradeMetricsCalculator(self.reader, strategy_name)
            trade_metrics = trade_calc.calculate()
            print("✓")
        except Exception as e:
            print(f"✗ Failed: {e}")
            trade_metrics = self._empty_trade_metrics()
        
        # 2. Calculate risk metrics
        try:
            print("   ⚠️  Risk metrics...", end=" ", flush=True)
            risk_calc = RiskMetricsCalculator(self.reader, strategy_name)
            risk_metrics = risk_calc.calculate()
            print("✓")
        except Exception as e:
            print(f"✗ Failed: {e}")
            risk_metrics = self._empty_risk_metrics()
        
        # 3. Calculate drawdown metrics
        try:
            print("   📉 Drawdown analysis...", end=" ", flush=True)
            dd_calc = DrawdownMetricsCalculator(self.reader, strategy_name)
            dd_results = dd_calc.calculate()
            dd_metrics = dd_results['metrics']
            dd_periods = dd_results['periods']
            print("✓")
        except Exception as e:
            print(f"✗ Failed: {e}")
            dd_metrics = {'max_drawdown_pct': 0, 'max_drawdown_dollars': 0, 'avg_drawdown_pct': 0}
            dd_periods = []
        
        # 4. Calculate streak metrics
        try:
            print("   🎯 Streak analysis...", end=" ", flush=True)
            streak_calc = StreakMetricsCalculator(self.reader, strategy_name)
            streak_results = streak_calc.calculate()
            streak_metrics = streak_results['metrics']
            streak_periods = streak_results['streaks']
            print("✓")
        except Exception as e:
            print(f"✗ Failed: {e}")
            streak_metrics = {'max_win_streak': 0, 'max_loss_streak': 0, 'current_streak': 0}
            streak_periods = []
        
        # 5. Calculate monthly metrics
        try:
            print("   📅 Monthly returns...", end=" ", flush=True)
            monthly_calc = MonthlyMetricsCalculator(self.reader, strategy_name)
            monthly_data = monthly_calc.calculate()
            print("✓")
        except Exception as e:
            print(f"✗ Failed: {e}")
            monthly_data = {}
        
        # 6. Calculate volume metrics
        try:
            print("   📊 Volume analysis...", end=" ", flush=True)
            volume_calc = VolumeMetricsCalculator(self.reader, strategy_name)
            volume_metrics = volume_calc.calculate()
            print("✓")
        except Exception as e:
            print(f"✗ Failed: {e}")
            volume_metrics = {}
        
        # 7. Pre-compute charts
        try:
            print("   📈 Chart preprocessing...", end=" ", flush=True)
            chart_proc = ChartProcessor(self.reader, strategy_name)
            chart_data = chart_proc.process_all()
            print("✓")
        except Exception as e:
            print(f"✗ Failed: {e}")
            chart_data = {}
        
        # 8. Get portfolio metrics from simulation
        try:
            print("   💼 Portfolio metrics...", end=" ", flush=True)
            perf = self.reader.get_strategy_performance(strategy_name)

            # Calculate unrealized P&L from open positions
            # If there are open trades, they contribute to unrealized P&L
            open_positions = trade_metrics.get('open_positions', 0)
            if open_positions > 0:
                # Get open trades to calculate unrealized P&L
                try:
                    open_trades = self.reader.get_open_trades(strategy_name)
                    if not open_trades.empty and 'unrealized_pnl' in open_trades.columns:
                        perf['unrealized_pnl'] = open_trades['unrealized_pnl'].sum()
                    else:
                        perf['unrealized_pnl'] = 0.0
                except Exception:
                    perf['unrealized_pnl'] = 0.0
            else:
                # No open positions, no unrealized P&L
                perf['unrealized_pnl'] = 0.0

            print("✓")
        except Exception as e:
            print(f"✗ Failed: {e}")
            perf = {}
        
        # Combine all metrics for strategy_summary table
        try:
            summary_metrics = self._combine_metrics(
                trade_metrics, risk_metrics, dd_metrics, 
                streak_metrics, perf, timestamp
            )
        except Exception as e:
            print(f"   ⚠️  Warning: Failed to combine metrics: {e}")
            return
        
        # Write to database with error handling
        print("   💾 Writing to database...", end=" ", flush=True)
        
        try:
            self._write_strategy_summary(strategy_name, summary_metrics)
        except Exception as e:
            print(f"\n   ⚠️  Failed to write summary: {e}")
        
        try:
            self._write_monthly_returns(strategy_name, monthly_data)
        except Exception as e:
            print(f"\n   ⚠️  Failed to write monthly returns: {e}")
        
        try:
            self._write_drawdown_periods(strategy_name, dd_periods)
        except Exception as e:
            print(f"\n   ⚠️  Failed to write drawdown periods: {e}")
        
        try:
            self._write_streak_periods(strategy_name, streak_periods)
        except Exception as e:
            print(f"\n   ⚠️  Failed to write streak periods: {e}")
        
        try:
            self._write_volume_analysis(strategy_name, volume_metrics)
        except Exception as e:
            print(f"\n   ⚠️  Failed to write volume analysis: {e}")
        
        try:
            self._write_chart_cache(strategy_name, chart_data)
        except Exception as e:
            print(f"\n   ⚠️  Failed to write chart cache: {e}")
        
        try:
            self._write_returns_distribution(strategy_name)
        except Exception as e:
            print(f"\n   ⚠️  Failed to write returns distribution: {e}")
        
        try:
            self._write_stock_performance(strategy_name)
        except Exception as e:
            print(f"\n   ⚠️  Failed to write stock performance: {e}")
        
        print("✓")
        
        try:
            self.conn.commit()
            print(f"   ✅ {strategy_name} complete")
        except Exception as e:
            print(f"   ⚠️  Commit failed: {e}")

    def _combine_metrics(self, trade_metrics, risk_metrics, dd_metrics, 
                        streak_metrics, perf, timestamp):
        """Combine all metrics into strategy_summary format"""
        
        # Get basic portfolio metrics
        initial_capital = perf.get('initial_capital', 100000) if perf else 100000
        final_value = perf.get('final_value', initial_capital) if perf else initial_capital
        # Recompute total return percentage using adjusted final_value (includes unrealized P&L)
        total_return_pct = ((final_value - initial_capital) / initial_capital * 100) if initial_capital else 0
        
        # Calculate annualized return using recomputed total_return_pct
        days = len(self.reader.get_portfolio_history(self.reader.list_strategies()[0]))
        if days > 0:
            annualized_return = ((total_return_pct / 100 + 1) ** (252 / days) - 1) * 100
        else:
            annualized_return = 0
        
        return {
            # Basic Performance
            'total_return_pct': total_return_pct,
            'total_profit_dollars': final_value - initial_capital,
            'unrealized_pnl': perf.get('unrealized_pnl', 0.0) if perf else 0.0,
            'annualized_return_pct': annualized_return,
            
            # Trade Statistics
            'total_trades': trade_metrics['total_trades'],
            'completed_trades': trade_metrics['completed_trades'],
            'open_positions': trade_metrics['open_positions'],
            'winning_trades': trade_metrics['winning_trades'],
            'losing_trades': trade_metrics['losing_trades'],
            'win_rate_pct': trade_metrics['win_rate_pct'],
            
            # Profit Metrics
            'gross_profit': trade_metrics['gross_profit'],
            'gross_loss': trade_metrics['gross_loss'],
            'profit_factor': trade_metrics['profit_factor'],
            'avg_win_dollars': trade_metrics['avg_win_dollars'],
            'avg_loss_dollars': trade_metrics['avg_loss_dollars'],
            'risk_reward_ratio': trade_metrics['risk_reward_ratio'],
            'expectancy_dollars': trade_metrics['expectancy_dollars'],
            
            # Risk Metrics
            'sharpe_ratio': risk_metrics['sharpe_ratio'],
            'sortino_ratio': risk_metrics['sortino_ratio'],
            'calmar_ratio': risk_metrics['calmar_ratio'],
            'omega_ratio': risk_metrics['omega_ratio'],
            'max_drawdown_pct': dd_metrics['max_drawdown_pct'],
            'max_drawdown_dollars': dd_metrics['max_drawdown_dollars'],
            'avg_drawdown_pct': dd_metrics['avg_drawdown_pct'],
            'volatility_annual_pct': risk_metrics['volatility_annual_pct'],
            'downside_deviation_pct': risk_metrics['downside_deviation_pct'],
            
            # Value at Risk
            'var_95_pct': risk_metrics['var_95_pct'],
            'cvar_95_pct': risk_metrics['cvar_95_pct'],
            
            # Market Exposure
            'beta': risk_metrics['beta'],
            'alpha_pct': risk_metrics['alpha_pct'],
            'correlation': risk_metrics['correlation'],
            'information_ratio': risk_metrics['information_ratio'],
            'treynor_ratio': risk_metrics['treynor_ratio'],
            
            # Holding Period
            'avg_hold_days': trade_metrics['avg_hold_days'],
            'max_hold_days': trade_metrics['max_hold_days'],
            'min_hold_days': trade_metrics['min_hold_days'],
            
            # Streaks
            'max_win_streak': streak_metrics['max_win_streak'],
            'max_loss_streak': streak_metrics['max_loss_streak'],
            'current_streak': streak_metrics['current_streak'],
            
            # Metadata
            'computation_timestamp': timestamp,
            'source_simulation_db': str(self.sim_db_path.name),
        }
    
    def _write_strategy_summary(self, strategy_name, metrics):
        """Write to strategy_summary table"""
        cursor = self.conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO strategy_summary (
                strategy_name, total_return_pct, total_profit_dollars, unrealized_pnl, annualized_return_pct,
                total_trades, completed_trades, open_positions, winning_trades, losing_trades, win_rate_pct,
                gross_profit, gross_loss, profit_factor, avg_win_dollars, avg_loss_dollars,
                risk_reward_ratio, expectancy_dollars, sharpe_ratio, sortino_ratio, calmar_ratio,
                omega_ratio, max_drawdown_pct, max_drawdown_dollars, avg_drawdown_pct,
                volatility_annual_pct, downside_deviation_pct, var_95_pct, cvar_95_pct,
                beta, alpha_pct, correlation, information_ratio, treynor_ratio,
                avg_hold_days, max_hold_days, min_hold_days, max_win_streak, max_loss_streak,
                current_streak, computation_timestamp, source_simulation_db
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            strategy_name,
            metrics['total_return_pct'],
            metrics['total_profit_dollars'],
            metrics.get('unrealized_pnl', 0.0),
            metrics['annualized_return_pct'],
            metrics['total_trades'],
            metrics['completed_trades'],
            metrics['open_positions'],
            metrics['winning_trades'],
            metrics['losing_trades'],
            metrics['win_rate_pct'],
            metrics['gross_profit'],
            metrics['gross_loss'],
            metrics['profit_factor'],
            metrics['avg_win_dollars'],
            metrics['avg_loss_dollars'],
            metrics['risk_reward_ratio'],
            metrics['expectancy_dollars'],
            metrics['sharpe_ratio'],
            metrics['sortino_ratio'],
            metrics['calmar_ratio'],
            metrics['omega_ratio'],
            metrics['max_drawdown_pct'],
            metrics['max_drawdown_dollars'],
            metrics['avg_drawdown_pct'],
            metrics['volatility_annual_pct'],
            metrics['downside_deviation_pct'],
            metrics['var_95_pct'],
            metrics['cvar_95_pct'],
            metrics['beta'],
            metrics['alpha_pct'],
            metrics['correlation'],
            metrics['information_ratio'],
            metrics['treynor_ratio'],
            metrics['avg_hold_days'],
            metrics['max_hold_days'],
            metrics['min_hold_days'],
            metrics['max_win_streak'],
            metrics['max_loss_streak'],
            metrics['current_streak'],
            metrics['computation_timestamp'],
            metrics['source_simulation_db']
        ))

    def _write_monthly_returns(self, strategy_name, monthly_data):
        """Write to monthly_returns table"""
        if not monthly_data:
            return
        
        cursor = self.conn.cursor()
        
        for year_month, data in monthly_data.items():
            cursor.execute('''
                INSERT OR REPLACE INTO monthly_returns
                VALUES (?, ?, ?, ?, ?)
            ''', (
                strategy_name,
                year_month,
                data['return_pct'],
                data['num_trades'],
                data['win_rate_pct']
            ))
    
    def _write_drawdown_periods(self, strategy_name, periods):
        """Write to drawdown_periods table"""
        if not periods:
            return
        
        cursor = self.conn.cursor()
        
        for period in periods:
            cursor.execute('''
                INSERT INTO drawdown_periods
                (strategy_name, peak_date, trough_date, recovery_date,
                 drawdown_pct, drawdown_dollars, recovery_days, duration_days)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                strategy_name,
                period['peak_date'],
                period['trough_date'],
                period['recovery_date'],
                period['drawdown_pct'],
                period['drawdown_dollars'],
                period['recovery_days'],
                period['duration_days']
            ))
    
    def _write_streak_periods(self, strategy_name, streaks):
        """Write to trade_streaks table"""
        if not streaks:
            return
        
        cursor = self.conn.cursor()
        
        for streak in streaks:
            cursor.execute('''
                INSERT INTO trade_streaks
                (strategy_name, streak_type, start_date, end_date, length, cumulative_pnl)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                strategy_name,
                streak['streak_type'],
                streak['start_date'],
                streak['end_date'],
                streak['length'],
                streak['cumulative_pnl']
            ))
    
    def _write_volume_analysis(self, strategy_name, volume_metrics):
        """Write to volume_analysis table"""
        if not volume_metrics:
            return
        
        cursor = self.conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO volume_analysis
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            strategy_name,
            volume_metrics['trades_with_volume_data'],
            volume_metrics['avg_entry_volume_ratio'],
            volume_metrics['avg_exit_volume_ratio'],
            volume_metrics['high_volume_trades'],
            volume_metrics['low_volume_trades'],
            volume_metrics['high_vol_win_rate'],
            volume_metrics['low_vol_win_rate']
        ))
    
    def _write_chart_cache(self, strategy_name, chart_data):
        """Write to chart_cache table with UTF-8 safety"""
        if not chart_data:
            return
        
        cursor = self.conn.cursor()
        timestamp = int(time.time())
        
        for chart_type, data in chart_data.items():
            # IMPORTANT: chart_id format must match what dashboard expects
            chart_id = f"{strategy_name}_{chart_type}"
            
            try:
                # Clean data to remove NaN and Inf values
                cleaned_data = self._clean_json_data(data)
                # Ensure JSON is UTF-8 encoded
                chart_json = json.dumps(cleaned_data, ensure_ascii=False)
                # Double-check encoding
                chart_json = chart_json.encode('utf-8', errors='ignore').decode('utf-8', errors='ignore')
            except Exception as e:
                print(f"Warning: Could not encode chart data for {chart_id}: {e}")
                continue
            
            cursor.execute('''
                INSERT OR REPLACE INTO chart_cache
                VALUES (?, ?, ?, ?, ?)
            ''', (
                chart_id,
                strategy_name,
                chart_type,
                chart_json,
                timestamp
            ))
        
        print(f"       Cached {len(chart_data)} charts")

    def _write_returns_distribution(self, strategy_name):
        """Write to returns_distribution table"""
        closed_trades = self.reader.get_closed_trades(strategy_name)
        
        if closed_trades.empty or 'profit_loss_pct' not in closed_trades.columns:
            return
        
        returns = closed_trades['profit_loss_pct'].dropna()
        
        if len(returns) == 0:
            return
        
        # Create histogram bins
        import numpy as np
        bins = np.arange(-20, 25, 5)  # -20%, -15%, ..., +20%
        counts, bin_edges = np.histogram(returns, bins=bins)
        
        cursor = self.conn.cursor()
        
        total = len(returns)
        for i, count in enumerate(counts):
            percentage = (count / total * 100) if total > 0 else 0
            
            cursor.execute('''
                INSERT INTO returns_distribution
                VALUES (?, ?, ?, ?, ?)
            ''', (
                strategy_name,
                bin_edges[i],
                bin_edges[i+1],
                int(count),
                percentage
            ))
    
    def _write_stock_performance(self, strategy_name):
        """Write to stock_performance_cache table"""
        stock_perf = self.reader.get_stock_performance(strategy_name)
        
        if stock_perf.empty:
            return
        
        cursor = self.conn.cursor()
        
        for _, row in stock_perf.iterrows():
            # Ensure symbol is UTF-8 safe
            symbol = row['symbol']
            if isinstance(symbol, bytes):
                symbol = symbol.decode('utf-8', errors='ignore')
            
            cursor.execute('''
                INSERT OR REPLACE INTO stock_performance_cache
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                strategy_name,
                symbol,
                row['total_trades'],
                row['winning_trades'],
                row['losing_trades'],
                row.get('win_rate_pct', 0),
                row['net_profit_loss'],
                row.get('avg_return_pct', 0),
                0,  # best_trade_pct - would need to calculate
                0,  # worst_trade_pct - would need to calculate
                0   # avg_volume_ratio - would need to calculate
            ))
    
    def _empty_trade_metrics(self):
        """Return empty trade metrics"""
        return {
            'total_trades': 0, 'completed_trades': 0, 'open_positions': 0,
            'winning_trades': 0, 'losing_trades': 0, 'win_rate_pct': 0,
            'gross_profit': 0, 'gross_loss': 0, 'net_profit': 0,
            'avg_win_dollars': 0, 'avg_loss_dollars': 0, 'avg_trade_dollars': 0,
            'best_trade_dollars': 0, 'worst_trade_dollars': 0,
            'best_trade_pct': 0, 'worst_trade_pct': 0,
            'profit_factor': 0, 'risk_reward_ratio': 0, 'expectancy_dollars': 0,
            'avg_hold_days': 0, 'max_hold_days': 0, 'min_hold_days': 0,
            'median_return_pct': 0, 'return_std_dev': 0
        }
    
    def _empty_risk_metrics(self):
        """Return empty risk metrics"""
        return {
            'volatility_annual_pct': 0, 'downside_deviation_pct': 0,
            'sharpe_ratio': 0, 'sortino_ratio': 0, 'calmar_ratio': 0,
            'omega_ratio': 0, 'treynor_ratio': None,
            'var_95_pct': 0, 'var_99_pct': 0,
            'cvar_95_pct': 0, 'cvar_99_pct': 0,
            'beta': None, 'alpha_pct': None, 'correlation': None,
            'information_ratio': None, 'skewness': 0, 'kurtosis': 0
        }
    
    def _clean_json_data(self, obj):
        """
        Recursively clean data structures to remove NaN/Inf values
        that can't be JSON serialized
        """
        import math
        
        if isinstance(obj, dict):
            return {k: self._clean_json_data(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._clean_json_data(v) for v in obj]
        elif isinstance(obj, float):
            if math.isnan(obj) or math.isinf(obj):
                return None
            return obj
        else:
            return obj
    
    def _analyze_benchmark(self):
        """Analyze SPY benchmark for comparison"""
        print(f"\n📊 Analyzing SPY benchmark...")
        
        try:
            # Try to get SPY data from simulation database
            spy_trades = self.reader.get_closed_trades('SPY')
            
            if spy_trades.empty:
                print("   ⚠️  No SPY trade data available")
                return
            
            # Get portfolio history for SPY
            try:
                spy_portfolio = self.reader.get_portfolio_history('SPY')
                if spy_portfolio.empty:
                    print("   ⚠️  No SPY portfolio data available")
                    return
            except Exception:
                print("   ⚠️  Could not load SPY portfolio data")
                return
            
            # Create minimal summary for SPY
            initial = spy_portfolio['portfolio_value'].iloc[0]
            final = spy_portfolio['portfolio_value'].iloc[-1]
            total_return = ((final - initial) / initial * 100) if initial > 0 else 0
            
            # Store SPY summary for comparison
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO strategy_summary (
                    strategy_name, total_return_pct, total_profit_dollars, unrealized_pnl,
                    annualized_return_pct, total_trades, completed_trades,
                    winning_trades, losing_trades, win_rate_pct,
                    sharpe_ratio, sortino_ratio, calmar_ratio, max_drawdown_pct
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                'SPY',
                total_return,
                final - initial,
                0.0,  # SPY benchmark has no open positions
                total_return * 0.2,  # Approximate annualized
                len(spy_trades),
                len(spy_trades),  # All trades are closed for benchmark
                len(spy_trades[spy_trades['profit_loss_pct'] > 0]),
                len(spy_trades[spy_trades['profit_loss_pct'] < 0]),
                len(spy_trades[spy_trades['profit_loss_pct'] > 0]) / len(spy_trades) * 100 if len(spy_trades) > 0 else 0,
                0, 0, 0,  # Risk metrics placeholder
                spy_portfolio['portfolio_value'].min() / spy_portfolio['portfolio_value'].max() - 1 * 100
            ))
            
            # Store SPY chart data
            processor = ChartProcessor(self.reader, 'SPY')
            try:
                chart_data = processor.process_all()
                timestamp = int(time.time())
                
                for chart_type, data in chart_data.items():
                    chart_id = f"SPY_{chart_type}"
                    try:
                        cleaned_data = self._clean_json_data(data)
                        chart_json = json.dumps(cleaned_data, ensure_ascii=False)
                    except:
                        continue
                    
                    cursor.execute('''
                        INSERT OR REPLACE INTO chart_cache
                        VALUES (?, ?, ?, ?, ?)
                    ''', (chart_id, 'SPY', chart_type, chart_json, timestamp))
            except Exception as e:
                print(f"   ⚠️  Could not cache SPY charts: {e}")
            
            self.conn.commit()
            print(f"   ✅ SPY benchmark analyzed (Return: {total_return:.2f}%)")
            
        except Exception as e:
            print(f"   ⚠️  Error analyzing SPY: {e}")
        
    def _store_metadata(self):
        """Store analysis metadata with UTF-8 safety"""
        cursor = self.conn.cursor()
        timestamp = int(time.time())
        
        # Ensure database name is UTF-8 safe
        sim_db_name = str(self.sim_db_path.name)
        try:
            if isinstance(sim_db_name, bytes):
                sim_db_name = sim_db_name.decode('utf-8', errors='ignore')
        except Exception:
            sim_db_name = "unknown_database.db"
        
        metadata = [
            ('simulation_db', sim_db_name, timestamp),
            ('source_simulation', sim_db_name, timestamp),  # For trades endpoint
            ('simulation_id', str(self.reader.get_simulation_id()), timestamp),
            ('universe', str(self.reader.get_universe()), timestamp),
            ('num_symbols', str(self.reader.get_num_symbols()), timestamp),
            ('analysis_timestamp', str(timestamp), timestamp),
            ('analysis_version', '1.0', timestamp),
        ]
        
        cursor.executemany('''
            INSERT OR REPLACE INTO analysis_metadata
            VALUES (?, ?, ?)
        ''', metadata)
        
        self.conn.commit()
    
    def _optimize_database(self):
        """Optimize database for fast reading"""
        cursor = self.conn.cursor()
        cursor.execute('PRAGMA optimize')
        cursor.execute('VACUUM')
        self.conn.commit()


# ============================================================================
# COMMAND LINE INTERFACE
# ============================================================================

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Analysis Engine - Pre-compute all metrics')
    parser.add_argument('--sim', type=str, help='Path to simulation database')
    parser.add_argument('--latest', action='store_true', help='Use latest simulation')
    
    args = parser.parse_args()
    
    # Find database
    if args.latest:
        sim_dir = Path('../simulator/simulations')
        if not sim_dir.exists():
            print(f"❌ Simulations directory not found: {sim_dir}")
            return
        
        db_files = list(sim_dir.glob('simulation_*.db'))
        if not db_files:
            print("❌ No simulation databases found")
            return
        
        db_path = sorted(db_files, reverse=True)[0]
        print(f"📊 Using latest: {db_path.name}\n")
    elif args.sim:
        db_path = Path(args.sim)
        if not db_path.exists():
            print(f"❌ Database not found: {db_path}")
            return
    else:
        print("❌ Please specify --sim <path> or --latest")
        parser.print_help()
        return
    
    # Run analysis
    try:
        engine = AnalysisEngine(db_path)
        result = engine.run_analysis()
        
        if result:
            print(f"\n✅ Success! Analysis database: {result}")
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()