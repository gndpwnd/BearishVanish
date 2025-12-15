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
        
        # Connect to analysis database
        self.conn = sqlite3.connect(str(self.analysis_db_path))
        
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
        
        # Analyze each strategy
        for i, strategy_name in enumerate(strategies, 1):
            print(f"\n[{i}/{len(strategies)}] Analyzing: {strategy_name}")
            self._analyze_strategy(strategy_name)
        
        # Store metadata
        self._store_metadata()
        
        # Optimize database
        self._optimize_database()
        
        # Close connections
        self.conn.close()
        self.reader.close()
        
        elapsed = time.time() - start_time
        
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
        Analyze a single strategy using all calculators
        
        Args:
            strategy_name: Strategy to analyze
        """
        timestamp = int(time.time())
        
        try:
            # 1. Calculate trade metrics
            print("   📊 Trade metrics...", end=" ", flush=True)
            trade_calc = TradeMetricsCalculator(self.reader, strategy_name)
            trade_metrics = trade_calc.calculate()
            print("✓")
            
            # 2. Calculate risk metrics
            print("   ⚠️  Risk metrics...", end=" ", flush=True)
            risk_calc = RiskMetricsCalculator(self.reader, strategy_name)
            risk_metrics = risk_calc.calculate()
            print("✓")
            
            # 3. Calculate drawdown metrics
            print("   📉 Drawdown analysis...", end=" ", flush=True)
            dd_calc = DrawdownMetricsCalculator(self.reader, strategy_name)
            dd_results = dd_calc.calculate()
            dd_metrics = dd_results['metrics']
            dd_periods = dd_results['periods']
            print("✓")
            
            # 4. Calculate streak metrics
            print("   🎯 Streak analysis...", end=" ", flush=True)
            streak_calc = StreakMetricsCalculator(self.reader, strategy_name)
            streak_results = streak_calc.calculate()
            streak_metrics = streak_results['metrics']
            streak_periods = streak_results['streaks']
            print("✓")
            
            # 5. Calculate monthly metrics
            print("   📅 Monthly returns...", end=" ", flush=True)
            monthly_calc = MonthlyMetricsCalculator(self.reader, strategy_name)
            monthly_data = monthly_calc.calculate()
            print("✓")
            
            # 6. Calculate volume metrics
            print("   📊 Volume analysis...", end=" ", flush=True)
            volume_calc = VolumeMetricsCalculator(self.reader, strategy_name)
            volume_metrics = volume_calc.calculate()
            print("✓")
            
            # 7. Pre-compute charts
            print("   📈 Chart preprocessing...", end=" ", flush=True)
            chart_proc = ChartProcessor(self.reader, strategy_name)
            chart_data = chart_proc.process_all()
            print("✓")
            
            # 8. Get portfolio metrics from simulation
            print("   💼 Portfolio metrics...", end=" ", flush=True)
            perf = self.reader.get_strategy_performance(strategy_name)
            print("✓")
            
            # Combine all metrics for strategy_summary table
            summary_metrics = self._combine_metrics(
                trade_metrics, risk_metrics, dd_metrics, 
                streak_metrics, perf, timestamp
            )
            
            # Write to database
            print("   💾 Writing to database...", end=" ", flush=True)
            self._write_strategy_summary(strategy_name, summary_metrics)
            self._write_monthly_returns(strategy_name, monthly_data)
            self._write_drawdown_periods(strategy_name, dd_periods)
            self._write_streak_periods(strategy_name, streak_periods)
            self._write_volume_analysis(strategy_name, volume_metrics)
            self._write_chart_cache(strategy_name, chart_data)
            self._write_returns_distribution(strategy_name)
            self._write_stock_performance(strategy_name)
            print("✓")
            
            self.conn.commit()
            
            print(f"   ✅ {strategy_name} complete")
            
        except Exception as e:
            print(f"\n   ❌ Error analyzing {strategy_name}: {e}")
            import traceback
            traceback.print_exc()
    
    def _combine_metrics(self, trade_metrics, risk_metrics, dd_metrics, 
                        streak_metrics, perf, timestamp):
        """Combine all metrics into strategy_summary format"""
        
        # Get basic portfolio metrics
        initial_capital = perf.get('initial_capital', 100000) if perf else 100000
        final_value = perf.get('final_value', initial_capital) if perf else initial_capital
        total_return_pct = perf.get('total_return_pct', 0) if perf else 0
        
        # Calculate annualized return
        days = len(self.reader.get_portfolio_history(self.reader.list_strategies()[0]))
        if days > 0:
            annualized_return = ((total_return_pct / 100 + 1) ** (252 / days) - 1) * 100
        else:
            annualized_return = 0
        
        return {
            # Basic Performance
            'total_return_pct': total_return_pct,
            'total_profit_dollars': final_value - initial_capital,
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
                strategy_name, total_return_pct, total_profit_dollars, annualized_return_pct,
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
                    ?, ?, ?, ?, ?, ?, ?)
        ''', (
            strategy_name,
            metrics['total_return_pct'],
            metrics['total_profit_dollars'],
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
        """Write to chart_cache table"""
        if not chart_data:
            return
        
        cursor = self.conn.cursor()
        timestamp = int(time.time())
        
        for chart_type, data in chart_data.items():
            # IMPORTANT: chart_id format must match what dashboard expects
            chart_id = f"{strategy_name}_{chart_type}"
            
            cursor.execute('''
                INSERT OR REPLACE INTO chart_cache
                VALUES (?, ?, ?, ?, ?)
            ''', (
                chart_id,
                strategy_name,
                chart_type,
                json.dumps(data),
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
            cursor.execute('''
                INSERT OR REPLACE INTO stock_performance_cache
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                strategy_name,
                row['symbol'],
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
    
    def _store_metadata(self):
        """Store analysis metadata"""
        cursor = self.conn.cursor()
        timestamp = int(time.time())
        
        metadata = [
            ('simulation_db', str(self.sim_db_path.name), timestamp),
            ('simulation_id', self.reader.get_simulation_id(), timestamp),
            ('universe', self.reader.get_universe(), timestamp),
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