"""
Performance Timeline Analysis - REFACTORED FOR DATABASE
NO MockTracker dependency - works directly with SimulationReader

Tracks when strategy outperformed/underperformed benchmark and detects sudden drops
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta


class PerformanceTimelineDB:
    """
    Analyze strategy performance timeline vs benchmark
    Works directly with SimulationReader - NO mock objects
    """
    
    def __init__(self, reader, strategy_name, benchmark='SPY'):
        """
        Initialize timeline analyzer
        
        Args:
            reader: SimulationReader instance
            strategy_name: Strategy to analyze
            benchmark: Benchmark strategy (default: 'SPY')
        """
        self.reader = reader
        self.strategy_name = strategy_name
        self.benchmark = benchmark
        
        # Load data
        self._load_data()
        
        # Calculate timeline metrics
        if not self.timeline_df.empty:
            self._calculate_timeline()
    
    def _load_data(self):
        """Load portfolio histories from database"""
        # Get strategy portfolio
        strategy_portfolio = self.reader.get_portfolio_history(self.strategy_name)
        
        # Get benchmark portfolio
        benchmark_portfolio = self.reader.get_portfolio_history(self.benchmark)
        
        if strategy_portfolio.empty or benchmark_portfolio.empty:
            self.timeline_df = pd.DataFrame()
            return
        
        # Merge on date
        self.timeline_df = pd.merge(
            strategy_portfolio[['date', 'portfolio_value']],
            benchmark_portfolio[['date', 'portfolio_value']],
            on='date',
            suffixes=('_strategy', '_benchmark')
        )
        
        # Ensure datetime
        self.timeline_df['date'] = pd.to_datetime(self.timeline_df['date'])
        
        # Sort by date
        self.timeline_df = self.timeline_df.sort_values('date').reset_index(drop=True)
    
    def _calculate_timeline(self):
        """Calculate timeline metrics"""
        # Calculate returns
        self.timeline_df['strategy_return'] = self.timeline_df['portfolio_value_strategy'].pct_change() * 100
        self.timeline_df['benchmark_return'] = self.timeline_df['portfolio_value_benchmark'].pct_change() * 100
        
        # Calculate cumulative returns (normalized to 100)
        self.timeline_df['strategy_cumulative'] = (1 + self.timeline_df['strategy_return']/100).cumprod() * 100
        self.timeline_df['benchmark_cumulative'] = (1 + self.timeline_df['benchmark_return']/100).cumprod() * 100
        
        # Calculate outperformance
        self.timeline_df['outperformance'] = self.timeline_df['strategy_cumulative'] - self.timeline_df['benchmark_cumulative']
        self.timeline_df['outperforming'] = self.timeline_df['outperformance'] > 0
        
        # Calculate running metrics
        self._calculate_running_metrics()
    
    def _calculate_running_metrics(self):
        """Calculate running performance metrics"""
        # Days outperformed/underperformed
        self.days_outperformed = self.timeline_df['outperforming'].sum()
        self.days_underperformed = len(self.timeline_df) - self.days_outperformed
        self.outperformance_pct = self.days_outperformed / len(self.timeline_df) * 100 if len(self.timeline_df) > 0 else 0
        
        # Streak analysis
        self._calculate_streaks()
        
        # Drawdown vs benchmark drawdown
        self._calculate_relative_drawdowns()
    
    def _calculate_streaks(self):
        """Calculate winning and losing streaks vs benchmark"""
        # Calculate daily win/loss vs benchmark
        daily_outcome = []
        for idx in range(1, len(self.timeline_df)):
            strat_ret = self.timeline_df.iloc[idx]['strategy_return']
            bench_ret = self.timeline_df.iloc[idx]['benchmark_return']
            
            # Handle NaN values
            if pd.isna(strat_ret) or pd.isna(bench_ret):
                continue
            
            daily_outcome.append(1 if strat_ret > bench_ret else 0)
        
        if not daily_outcome:
            self.max_win_streak_days = 0
            self.max_loss_streak_days = 0
            return
        
        # Calculate win streaks
        current_streak = 0
        max_win_streak = 0
        
        for outcome in daily_outcome:
            if outcome == 1:
                current_streak += 1
                max_win_streak = max(max_win_streak, current_streak)
            else:
                current_streak = 0
        
        # Calculate loss streaks
        current_streak = 0
        max_loss_streak = 0
        
        for outcome in daily_outcome:
            if outcome == 0:
                current_streak += 1
                max_loss_streak = max(max_loss_streak, current_streak)
            else:
                current_streak = 0
        
        self.max_win_streak_days = max_win_streak
        self.max_loss_streak_days = max_loss_streak
    
    def _calculate_relative_drawdowns(self):
        """Calculate relative drawdowns vs benchmark"""
        # Strategy drawdown
        strat_values = self.timeline_df['portfolio_value_strategy'].values
        strat_peak = np.maximum.accumulate(strat_values)
        strat_drawdown = (strat_values - strat_peak) / strat_peak * 100
        
        # Benchmark drawdown
        bench_values = self.timeline_df['portfolio_value_benchmark'].values
        bench_peak = np.maximum.accumulate(bench_values)
        bench_drawdown = (bench_values - bench_peak) / bench_peak * 100
        
        # Relative drawdown (how much worse than benchmark)
        relative_dd = strat_drawdown - bench_drawdown
        
        self.timeline_df['strategy_dd'] = strat_drawdown
        self.timeline_df['benchmark_dd'] = bench_drawdown
        self.timeline_df['relative_dd'] = relative_dd
        
        # Count "sudden drops" (>2% drop in a day where benchmark didn't drop as much)
        self.sudden_drops = sum(
            (pd.Series(strat_drawdown).diff() < -2) & 
            (pd.Series(relative_dd).diff() < -1) &
            (pd.Series(strat_drawdown) < -3)
        )
    
    # ============================================================
    # CRASH DETECTION
    # ============================================================
    
    def detect_crashes(self, threshold=5.0):
        """
        Detect significant crashes (> threshold% drop in a day)
        
        Args:
            threshold: Daily drop percentage to qualify as crash
        
        Returns:
            list: List of crash events with details
        """
        if self.timeline_df.empty:
            return []
        
        crashes = []
        
        for i in range(1, len(self.timeline_df)):
            daily_drop = self.timeline_df.iloc[i]['strategy_dd'] - self.timeline_df.iloc[i-1]['strategy_dd']
            
            if daily_drop < -threshold:
                crash = {
                    'date': self.timeline_df.iloc[i]['date'],
                    'drop_pct': abs(daily_drop),
                    'strategy_value': self.timeline_df.iloc[i]['portfolio_value_strategy'],
                    'benchmark_drop': self.timeline_df.iloc[i]['benchmark_dd'] - self.timeline_df.iloc[i-1]['benchmark_dd'],
                    'recovery_date': None,
                    'recovery_days': None
                }
                
                # Find recovery
                pre_crash_value = self.timeline_df.iloc[i-1]['portfolio_value_strategy']
                for j in range(i, len(self.timeline_df)):
                    if self.timeline_df.iloc[j]['portfolio_value_strategy'] >= pre_crash_value:
                        crash['recovery_date'] = self.timeline_df.iloc[j]['date']
                        crash['recovery_days'] = (crash['recovery_date'] - crash['date']).days
                        break
                
                crashes.append(crash)
        
        return crashes
    
    # ============================================================
    # PERFORMANCE SUMMARY
    # ============================================================
    
    def get_performance_summary(self):
        """Get comprehensive performance summary"""
        if self.timeline_df.empty:
            return {}
        
        # Final values
        final_strat = self.timeline_df['portfolio_value_strategy'].iloc[-1]
        final_bench = self.timeline_df['portfolio_value_benchmark'].iloc[-1]
        
        # Initial values (assume 100,000 initial capital)
        initial_capital = self.reader.get_initial_cash()
        
        # Total returns
        total_return_strat = ((final_strat - initial_capital) / initial_capital) * 100
        total_return_bench = ((final_bench - initial_capital) / initial_capital) * 100
        
        # Volatility
        vol_strat = self.timeline_df['strategy_return'].std()
        vol_bench = self.timeline_df['benchmark_return'].std()
        
        # Max drawdowns
        max_dd_strat = self.timeline_df['strategy_dd'].min()
        max_dd_bench = self.timeline_df['benchmark_dd'].min()
        
        # Best/Worst days
        worst_day_strat = self.timeline_df['strategy_return'].min()
        worst_day_bench = self.timeline_df['benchmark_return'].min()
        best_day_strat = self.timeline_df['strategy_return'].max()
        best_day_bench = self.timeline_df['benchmark_return'].max()
        
        # Sharpe ratios (simplified)
        sharpe_strat = self.timeline_df['strategy_return'].mean() / vol_strat if vol_strat != 0 else 0
        sharpe_bench = self.timeline_df['benchmark_return'].mean() / vol_bench if vol_bench != 0 else 0
        
        # Win rate vs benchmark
        wins_vs_bench = sum(self.timeline_df['strategy_return'] > self.timeline_df['benchmark_return'])
        win_rate_vs_bench = wins_vs_bench / len(self.timeline_df) * 100
        
        return {
            'total_return_strategy': total_return_strat,
            'total_return_benchmark': total_return_bench,
            'excess_return': total_return_strat - total_return_bench,
            'days_outperformed': self.days_outperformed,
            'days_underperformed': self.days_underperformed,
            'outperformance_pct': self.outperformance_pct,
            'max_win_streak_days': self.max_win_streak_days,
            'max_loss_streak_days': self.max_loss_streak_days,
            'volatility_strategy': vol_strat,
            'volatility_benchmark': vol_bench,
            'max_drawdown_strategy': max_dd_strat,
            'max_drawdown_benchmark': max_dd_bench,
            'worst_day_strategy': worst_day_strat,
            'worst_day_benchmark': worst_day_bench,
            'best_day_strategy': best_day_strat,
            'best_day_benchmark': best_day_bench,
            'sharpe_strategy': sharpe_strat,
            'sharpe_benchmark': sharpe_bench,
            'sudden_drops': self.sudden_drops,
            'average_daily_return_strategy': self.timeline_df['strategy_return'].mean(),
            'average_daily_return_benchmark': self.timeline_df['benchmark_return'].mean(),
            'win_rate_vs_benchmark': win_rate_vs_bench
        }
    
    # ============================================================
    # REPORTING
    # ============================================================
    
    def print_detailed_report(self):
        """Print detailed timeline report"""
        if self.timeline_df.empty:
            print("\n⚠️ No timeline data available")
            return None
        
        summary = self.get_performance_summary()
        
        print("\n" + "="*80)
        print(f"PERFORMANCE TIMELINE ANALYSIS: {self.strategy_name}")
        print("="*80)
        
        print(f"\n📅 PERIOD COVERED:")
        print(f"   Start: {self.timeline_df['date'].iloc[0].date()}")
        print(f"   End: {self.timeline_df['date'].iloc[-1].date()}")
        print(f"   Total Days: {len(self.timeline_df)}")
        
        print(f"\n🏆 FINAL PERFORMANCE:")
        print(f"   Strategy Return: {summary['total_return_strategy']:+.2f}%")
        print(f"   {self.benchmark} Return: {summary['total_return_benchmark']:+.2f}%")
        print(f"   Excess Return: {summary['excess_return']:+.2f}%")
        
        print(f"\n📊 DAY-BY-DAY PERFORMANCE:")
        print(f"   Days Outperforming {self.benchmark}: {summary['days_outperformed']} ({summary['outperformance_pct']:.1f}%)")
        print(f"   Days Underperforming {self.benchmark}: {summary['days_underperformed']} ({100-summary['outperformance_pct']:.1f}%)")
        print(f"   Daily Win Rate vs {self.benchmark}: {summary['win_rate_vs_benchmark']:.1f}%")
        print(f"   Max Winning Streak: {summary['max_win_streak_days']} days")
        print(f"   Max Losing Streak: {summary['max_loss_streak_days']} days")
        
        print(f"\n⚡ SUDDEN DROPS & CRASHES:")
        print(f"   Sudden drops detected (>2% daily drop worse than {self.benchmark}): {summary['sudden_drops']}")
        
        crashes = self.detect_crashes(threshold=3.0)
        if crashes:
            print(f"   Major crashes (>3% daily drop): {len(crashes)}")
            for i, crash in enumerate(crashes[:3]):  # Show top 3
                print(f"     {i+1}. {crash['date'].date()}: -{crash['drop_pct']:.1f}%")
                if crash['recovery_date']:
                    print(f"        Recovery: {crash['recovery_days']} days later")
                else:
                    print(f"        Recovery: Not yet recovered")
        
        print(f"\n📈 RISK METRICS:")
        print(f"   Strategy Volatility: {summary['volatility_strategy']:.2f}%")
        print(f"   {self.benchmark} Volatility: {summary['volatility_benchmark']:.2f}%")
        print(f"   Strategy Max Drawdown: {summary['max_drawdown_strategy']:.2f}%")
        print(f"   {self.benchmark} Max Drawdown: {summary['max_drawdown_benchmark']:.2f}%")
        print(f"   Worst Day (Strategy): {summary['worst_day_strategy']:.2f}%")
        print(f"   Worst Day ({self.benchmark}): {summary['worst_day_benchmark']:.2f}%")
        
        print(f"\n🎯 INTERPRETATION:")
        if summary['total_return_strategy'] > summary['total_return_benchmark']:
            print(f"   ✅ Strategy BEAT the market by {summary['excess_return']:+.2f}%")
        else:
            print(f"   ❌ Strategy LOST to the market by {abs(summary['excess_return']):.2f}%")
        
        if summary['outperformance_pct'] > 50:
            print(f"   ✅ Strategy outperformed {self.benchmark} most days ({summary['outperformance_pct']:.1f}%)")
        else:
            print(f"   ⚠️ Strategy underperformed {self.benchmark} most days ({100-summary['outperformance_pct']:.1f}%)")
        
        if summary['sudden_drops'] > 5:
            print(f"   ⚠️ High number of sudden drops ({summary['sudden_drops']}) - strategy may be volatile")
        
        print("\n" + "="*80 + "\n")
        
        return summary
    
    # ============================================================
    # VISUALIZATION
    # ============================================================
    
    def create_timeline_chart(self, save_path=None):
        """Create comprehensive timeline chart"""
        if self.timeline_df.empty:
            print("⚠️ No data to plot")
            return None, None
        
        fig, axes = plt.subplots(3, 1, figsize=(14, 12), sharex=True)
        
        dates = self.timeline_df['date']
        
        # Plot 1: Cumulative performance
        axes[0].plot(dates, self.timeline_df['strategy_cumulative'], 
                    label='Strategy', color='blue', linewidth=2)
        axes[0].plot(dates, self.timeline_df['benchmark_cumulative'],
                    label=f'{self.benchmark}', color='gray', linewidth=2, alpha=0.7)
        
        # Fill outperformance areas
        mask_outperform = self.timeline_df['outperformance'] > 0
        axes[0].fill_between(dates, 
                           self.timeline_df['strategy_cumulative'],
                           self.timeline_df['benchmark_cumulative'],
                           where=mask_outperform,
                           color='green', alpha=0.2, label='Outperforming')
        
        axes[0].fill_between(dates,
                           self.timeline_df['strategy_cumulative'],
                           self.timeline_df['benchmark_cumulative'],
                           where=~mask_outperform,
                           color='red', alpha=0.2, label='Underperforming')
        
        axes[0].set_title(f'Cumulative Performance vs {self.benchmark}', fontweight='bold', fontsize=12)
        axes[0].set_ylabel('Cumulative Return (Indexed to 100)')
        axes[0].legend()
        axes[0].grid(True, alpha=0.3)
        
        # Plot 2: Daily returns comparison
        axes[1].bar(dates[1:], 
                   self.timeline_df['strategy_return'][1:],
                   color=['green' if x > 0 else 'red' for x in self.timeline_df['strategy_return'][1:]],
                   alpha=0.6, label='Strategy', width=0.8)
        axes[1].bar(dates[1:],
                   self.timeline_df['benchmark_return'][1:],
                   color=['gray' if x > 0 else 'darkgray' for x in self.timeline_df['benchmark_return'][1:]],
                   alpha=0.4, label=f'{self.benchmark}', width=0.4)
        axes[1].axhline(0, color='black', linewidth=0.5)
        axes[1].set_title('Daily Returns Comparison', fontweight='bold', fontsize=12)
        axes[1].set_ylabel('Daily Return (%)')
        axes[1].legend()
        axes[1].grid(True, alpha=0.3, axis='y')
        
        # Plot 3: Drawdown comparison
        axes[2].plot(dates, self.timeline_df['strategy_dd'],
                    label='Strategy Drawdown', color='red', linewidth=1.5)
        axes[2].plot(dates, self.timeline_df['benchmark_dd'],
                    label=f'{self.benchmark} Drawdown', color='gray', linewidth=1.5, alpha=0.7)
        axes[2].fill_between(dates, self.timeline_df['strategy_dd'], 
                           color='red', alpha=0.2)
        axes[2].fill_between(dates, self.timeline_df['benchmark_dd'],
                           color='gray', alpha=0.2)
        axes[2].axhline(0, color='black', linewidth=0.5)
        axes[2].set_title('Drawdown Comparison', fontweight='bold', fontsize=12)
        axes[2].set_ylabel('Drawdown (%)')
        axes[2].set_xlabel('Date')
        axes[2].legend()
        axes[2].grid(True, alpha=0.3)
        
        # Format x-axis
        for ax in axes:
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            print(f"✅ Timeline chart saved to: {save_path}")
        
        return fig, axes


# ============================================================
# CONVENIENCE FUNCTIONS
# ============================================================

def analyze_performance_timeline(reader, strategy_name, benchmark='SPY'):
    """
    Convenience function to analyze performance timeline
    
    Usage:
        analyzer = analyze_performance_timeline(reader, 'My Strategy')
        summary = analyzer.print_detailed_report()
        fig, axes = analyzer.create_timeline_chart()
        plt.show()
    """
    analyzer = PerformanceTimelineDB(reader, strategy_name, benchmark)
    return analyzer