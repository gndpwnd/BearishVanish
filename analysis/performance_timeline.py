"""
Performance Timeline Analysis
Tracks when strategy outperformed/underperformed SPY and detects sudden drops
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta

class PerformanceTimeline:
    """Analyze strategy performance timeline vs benchmark"""
    
    def __init__(self, strategy_tracker, spy_tracker):
        self.strategy_tracker = strategy_tracker
        self.spy_tracker = spy_tracker
        
        # Calculate performance metrics
        self._calculate_timeline()
    
    def _calculate_timeline(self):
        """Calculate timeline metrics"""
        # Create DataFrame for analysis
        self.timeline_df = pd.DataFrame({
            'date': self.strategy_tracker.dates,
            'strategy_value': self.strategy_tracker.portfolio_value_history,
            'spy_value': self.spy_tracker.portfolio_value_history
        })
        
        # Calculate returns
        self.timeline_df['strategy_return'] = self.timeline_df['strategy_value'].pct_change() * 100
        self.timeline_df['spy_return'] = self.timeline_df['spy_value'].pct_change() * 100
        
        # Calculate cumulative returns
        self.timeline_df['strategy_cumulative'] = (1 + self.timeline_df['strategy_return']/100).cumprod() * 100
        self.timeline_df['spy_cumulative'] = (1 + self.timeline_df['spy_return']/100).cumprod() * 100
        
        # Calculate outperformance
        self.timeline_df['outperformance'] = self.timeline_df['strategy_cumulative'] - self.timeline_df['spy_cumulative']
        self.timeline_df['outperforming'] = self.timeline_df['outperformance'] > 0
        
        # Calculate running metrics
        self._calculate_running_metrics()
    
    def _calculate_running_metrics(self):
        """Calculate running performance metrics"""
        # Days outperformed/underperformed
        self.days_outperformed = self.timeline_df['outperforming'].sum()
        self.days_underperformed = len(self.timeline_df) - self.days_outperformed
        self.outperformance_pct = self.days_outperformed / len(self.timeline_df) * 100
        
        # Streak analysis
        self._calculate_streaks()
        
        # Drawdown vs SPY drawdown
        self._calculate_relative_drawdowns()
    
    def _calculate_streaks(self):
        """Calculate winning and losing streaks vs SPY"""
        # Calculate daily win/loss vs SPY
        daily_outcome = []
        for idx in range(1, len(self.timeline_df)):
            strat_ret = self.timeline_df.iloc[idx]['strategy_return']
            spy_ret = self.timeline_df.iloc[idx]['spy_return']
            daily_outcome.append(1 if strat_ret > spy_ret else 0)
        
        # Calculate streaks
        current_streak = 0
        max_win_streak = 0
        max_loss_streak = 0
        
        for outcome in daily_outcome:
            if outcome == 1:
                current_streak += 1
                max_win_streak = max(max_win_streak, current_streak)
            else:
                current_streak = 0
        
        current_streak = 0
        for outcome in daily_outcome:
            if outcome == 0:
                current_streak += 1
                max_loss_streak = max(max_loss_streak, current_streak)
            else:
                current_streak = 0
        
        self.max_win_streak_days = max_win_streak
        self.max_loss_streak_days = max_loss_streak
    
    def _calculate_relative_drawdowns(self):
        """Calculate relative drawdowns vs SPY"""
        # Strategy drawdown
        strat_peak = np.maximum.accumulate(self.timeline_df['strategy_value'])
        strat_drawdown = (self.timeline_df['strategy_value'] - strat_peak) / strat_peak * 100
        
        # SPY drawdown
        spy_peak = np.maximum.accumulate(self.timeline_df['spy_value'])
        spy_drawdown = (self.timeline_df['spy_value'] - spy_peak) / spy_peak * 100
        
        # Relative drawdown (how much worse than SPY)
        relative_dd = strat_drawdown - spy_drawdown
        
        self.timeline_df['strategy_dd'] = strat_drawdown
        self.timeline_df['spy_dd'] = spy_drawdown
        self.timeline_df['relative_dd'] = relative_dd
        
        # Count "sudden drops" (>2% drop in a day where SPY didn't drop as much)
        self.sudden_drops = sum(
            (strat_drawdown.diff() < -2) & 
            (relative_dd.diff() < -1) &
            (strat_drawdown < -3)
        )
    
    def detect_crashes(self, threshold=5.0):
        """
        Detect significant crashes (> threshold% drop in a day)
        """
        crashes = []
        
        for i in range(1, len(self.timeline_df)):
            daily_drop = self.timeline_df.iloc[i]['strategy_dd'] - self.timeline_df.iloc[i-1]['strategy_dd']
            
            if daily_drop < -threshold:
                crash = {
                    'date': self.timeline_df.iloc[i]['date'],
                    'drop_pct': abs(daily_drop),
                    'strategy_value': self.timeline_df.iloc[i]['strategy_value'],
                    'spy_drop': self.timeline_df.iloc[i]['spy_dd'] - self.timeline_df.iloc[i-1]['spy_dd'],
                    'recovery_date': None,
                    'recovery_days': None
                }
                
                # Find recovery
                for j in range(i, len(self.timeline_df)):
                    if self.timeline_df.iloc[j]['strategy_value'] >= self.timeline_df.iloc[i-1]['strategy_value']:
                        crash['recovery_date'] = self.timeline_df.iloc[j]['date']
                        crash['recovery_days'] = (crash['recovery_date'] - crash['date']).days
                        break
                
                crashes.append(crash)
        
        return crashes
    
    def get_performance_summary(self):
        """Get comprehensive performance summary"""
        # Final values
        final_strat = self.timeline_df['strategy_value'].iloc[-1]
        final_spy = self.timeline_df['spy_value'].iloc[-1]
        
        # Total returns
        total_return_strat = ((final_strat - 100000) / 100000) * 100
        total_return_spy = ((final_spy - 100000) / 100000) * 100
        
        # Volatility
        vol_strat = self.timeline_df['strategy_return'].std()
        vol_spy = self.timeline_df['spy_return'].std()
        
        # Max drawdowns
        max_dd_strat = self.timeline_df['strategy_dd'].min()
        max_dd_spy = self.timeline_df['spy_dd'].min()
        
        # Worst day
        worst_day_strat = self.timeline_df['strategy_return'].min()
        worst_day_spy = self.timeline_df['spy_return'].min()
        
        # Best day
        best_day_strat = self.timeline_df['strategy_return'].max()
        best_day_spy = self.timeline_df['spy_return'].max()
        
        # Sharpe ratios (simplified)
        sharpe_strat = self.timeline_df['strategy_return'].mean() / vol_strat if vol_strat != 0 else 0
        sharpe_spy = self.timeline_df['spy_return'].mean() / vol_spy if vol_spy != 0 else 0
        
        return {
            'total_return_strategy': total_return_strat,
            'total_return_spy': total_return_spy,
            'excess_return': total_return_strat - total_return_spy,
            'days_outperformed': self.days_outperformed,
            'days_underperformed': self.days_underperformed,
            'outperformance_pct': self.outperformance_pct,
            'max_win_streak_days': self.max_win_streak_days,
            'max_loss_streak_days': self.max_loss_streak_days,
            'volatility_strategy': vol_strat,
            'volatility_spy': vol_spy,
            'max_drawdown_strategy': max_dd_strat,
            'max_drawdown_spy': max_dd_spy,
            'worst_day_strategy': worst_day_strat,
            'worst_day_spy': worst_day_spy,
            'best_day_strategy': best_day_strat,
            'best_day_spy': best_day_spy,
            'sharpe_strategy': sharpe_strat,
            'sharpe_spy': sharpe_spy,
            'sudden_drops': self.sudden_drops,
            'average_daily_return_strategy': self.timeline_df['strategy_return'].mean(),
            'average_daily_return_spy': self.timeline_df['spy_return'].mean(),
            'win_rate_vs_spy': sum(self.timeline_df['strategy_return'] > self.timeline_df['spy_return']) / len(self.timeline_df) * 100
        }
    
    def print_detailed_report(self):
        """Print detailed timeline report"""
        summary = self.get_performance_summary()
        
        print("\n" + "="*80)
        print("PERFORMANCE TIMELINE ANALYSIS")
        print("="*80)
        
        print(f"\n📅 PERIOD COVERED:")
        print(f"   Start: {self.timeline_df['date'].iloc[0]}")
        print(f"   End: {self.timeline_df['date'].iloc[-1]}")
        print(f"   Total Days: {len(self.timeline_df)}")
        
        print(f"\n🏆 FINAL PERFORMANCE:")
        print(f"   Strategy Return: {summary['total_return_strategy']:+.2f}%")
        print(f"   S&P 500 Return: {summary['total_return_spy']:+.2f}%")
        print(f"   Excess Return: {summary['excess_return']:+.2f}%")
        
        print(f"\n📊 DAY-BY-DAY PERFORMANCE:")
        print(f"   Days Outperforming SPY: {summary['days_outperformed']} ({summary['outperformance_pct']:.1f}%)")
        print(f"   Days Underperforming SPY: {summary['days_underperformed']} ({100-summary['outperformance_pct']:.1f}%)")
        print(f"   Daily Win Rate vs SPY: {summary['win_rate_vs_spy']:.1f}%")
        print(f"   Max Winning Streak: {summary['max_win_streak_days']} days")
        print(f"   Max Losing Streak: {summary['max_loss_streak_days']} days")
        
        print(f"\n⚡ SUDDEN DROPS & CRASHES:")
        print(f"   Sudden drops detected (>2% daily drop worse than SPY): {summary['sudden_drops']}")
        
        crashes = self.detect_crashes(threshold=3.0)
        if crashes:
            print(f"   Major crashes (>3% daily drop): {len(crashes)}")
            for i, crash in enumerate(crashes[:3]):  # Show top 3
                print(f"     {i+1}. {crash['date'].date()}: -{crash['drop_pct']:.1f}%")
                if crash['recovery_date']:
                    print(f"        Recovery: {crash['recovery_days']} days later")
        
        print(f"\n📈 RISK METRICS:")
        print(f"   Strategy Volatility: {summary['volatility_strategy']:.2f}%")
        print(f"   SPY Volatility: {summary['volatility_spy']:.2f}%")
        print(f"   Strategy Max Drawdown: {summary['max_drawdown_strategy']:.2f}%")
        print(f"   SPY Max Drawdown: {summary['max_drawdown_spy']:.2f}%")
        print(f"   Worst Day (Strategy): {summary['worst_day_strategy']:.2f}%")
        print(f"   Worst Day (SPY): {summary['worst_day_spy']:.2f}%")
        
        print(f"\n🎯 INTERPRETATION:")
        if summary['total_return_strategy'] > summary['total_return_spy']:
            print(f"   ✅ Strategy BEAT the market by {summary['excess_return']:+.2f}%")
        else:
            print(f"   ❌ Strategy LOST to the market by {abs(summary['excess_return']):.2f}%")
        
        if summary['outperformance_pct'] > 50:
            print(f"   ✅ Strategy outperformed SPY most days ({summary['outperformance_pct']:.1f}%)")
        else:
            print(f"   ⚠️  Strategy underperformed SPY most days ({100-summary['outperformance_pct']:.1f}%)")
        
        if summary['sudden_drops'] > 5:
            print(f"   ⚠️  High number of sudden drops ({summary['sudden_drops']}) - strategy may be volatile")
        
        print("\n" + "="*80)
        
        # Return summary for use in other analysis
        return summary
    
    def create_timeline_chart(self, save_path=None):
        """Create comprehensive timeline chart"""
        fig, axes = plt.subplots(3, 1, figsize=(14, 12), sharex=True)
        
        # Plot 1: Cumulative performance
        axes[0].plot(self.timeline_df['date'], self.timeline_df['strategy_cumulative'], 
                    label='Strategy', color='blue', linewidth=2)
        axes[0].plot(self.timeline_df['date'], self.timeline_df['spy_cumulative'],
                    label='S&P 500', color='gray', linewidth=2, alpha=0.7)
        
        # Fill outperformance areas
        mask_outperform = self.timeline_df['outperformance'] > 0
        axes[0].fill_between(self.timeline_df['date'], 
                           self.timeline_df['strategy_cumulative'],
                           self.timeline_df['spy_cumulative'],
                           where=mask_outperform,
                           color='green', alpha=0.2, label='Outperforming')
        
        axes[0].fill_between(self.timeline_df['date'],
                           self.timeline_df['strategy_cumulative'],
                           self.timeline_df['spy_cumulative'],
                           where=~mask_outperform,
                           color='red', alpha=0.2, label='Underperforming')
        
        axes[0].set_title('Cumulative Performance vs S&P 500', fontweight='bold', fontsize=12)
        axes[0].set_ylabel('Cumulative Return (%)')
        axes[0].legend()
        axes[0].grid(True, alpha=0.3)
        
        # Plot 2: Daily returns comparison
        axes[1].bar(self.timeline_df['date'][1:], 
                   self.timeline_df['strategy_return'][1:],
                   color=['green' if x > 0 else 'red' for x in self.timeline_df['strategy_return'][1:]],
                   alpha=0.6, label='Strategy', width=0.8)
        axes[1].bar(self.timeline_df['date'][1:],
                   self.timeline_df['spy_return'][1:],
                   color=['gray' if x > 0 else 'darkgray' for x in self.timeline_df['spy_return'][1:]],
                   alpha=0.4, label='S&P 500', width=0.4)
        axes[1].axhline(0, color='black', linewidth=0.5)
        axes[1].set_title('Daily Returns Comparison', fontweight='bold', fontsize=12)
        axes[1].set_ylabel('Daily Return (%)')
        axes[1].legend()
        axes[1].grid(True, alpha=0.3, axis='y')
        
        # Plot 3: Drawdown comparison
        axes[2].plot(self.timeline_df['date'], self.timeline_df['strategy_dd'],
                    label='Strategy Drawdown', color='red', linewidth=1.5)
        axes[2].plot(self.timeline_df['date'], self.timeline_df['spy_dd'],
                    label='S&P 500 Drawdown', color='gray', linewidth=1.5, alpha=0.7)
        axes[2].fill_between(self.timeline_df['date'], self.timeline_df['strategy_dd'], 
                           color='red', alpha=0.2)
        axes[2].fill_between(self.timeline_df['date'], self.timeline_df['spy_dd'],
                           color='gray', alpha=0.2)
        axes[2].axhline(0, color='black', linewidth=0.5)
        axes[2].set_title('Drawdown Comparison', fontweight='bold', fontsize=12)
        axes[2].set_ylabel('Drawdown (%)')
        axes[2].set_xlabel('Date')
        axes[2].legend()
        axes[2].grid(True, alpha=0.3)
        
        # Format x-axis
        for ax in axes:
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            print(f"✅ Timeline chart saved to: {save_path}")
        
        return fig, axes