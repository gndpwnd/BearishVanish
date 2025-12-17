"""
Trade Metrics Calculator
Computes all trade-level statistics
"""

from .base_calculator import BaseCalculator
import pandas as pd
import numpy as np


class TradeMetricsCalculator(BaseCalculator):
    """Calculate comprehensive trade statistics"""
    
    def calculate(self):
        """
        Calculate all trade metrics
        
        Returns:
            dict: Complete trade statistics
        """
        if self.closed_trades.empty:
            return self._empty_metrics()
        
        wins = self.closed_trades[self.closed_trades['profit_loss_dollars'] > 0]
        losses = self.closed_trades[self.closed_trades['profit_loss_dollars'] < 0]
        
        total_trades = len(self.closed_trades)
        
        metrics = {
            # Basic counts
            'total_trades': len(self.trades),
            'completed_trades': total_trades,
            'open_positions': len(self.trades[self.trades['trade_status'] == 'OPEN']),
            
            # Win/Loss breakdown
            'winning_trades': len(wins),
            'losing_trades': len(losses),
            'win_rate_pct': (len(wins) / total_trades * 100) if total_trades > 0 else 0,
            
            # Profit metrics
            'gross_profit': wins['profit_loss_dollars'].sum() if not wins.empty else 0,
            'gross_loss': abs(losses['profit_loss_dollars'].sum()) if not losses.empty else 0,
            'net_profit': self.closed_trades['profit_loss_dollars'].sum(),
            
            # Average trades
            'avg_win_dollars': wins['profit_loss_dollars'].mean() if not wins.empty else 0,
            'avg_loss_dollars': losses['profit_loss_dollars'].mean() if not losses.empty else 0,
            'avg_trade_dollars': self.closed_trades['profit_loss_dollars'].mean(),
            
            # Best/Worst
            'best_trade_dollars': wins['profit_loss_dollars'].max() if not wins.empty else 0,
            'worst_trade_dollars': losses['profit_loss_dollars'].min() if not losses.empty else 0,
            'best_trade_pct': wins['profit_loss_pct'].max() if not wins.empty else 0,
            'worst_trade_pct': losses['profit_loss_pct'].min() if not losses.empty else 0,
            
            # Ratios
            'profit_factor': self._calculate_profit_factor(wins, losses),
            'risk_reward_ratio': self._calculate_risk_reward(wins, losses),
            'expectancy_dollars': self._calculate_expectancy(wins, losses, total_trades),
            
            # Holding period
            'avg_hold_days': self.closed_trades['holding_days'].mean() if 'holding_days' in self.closed_trades else 0,
            'max_hold_days': self.closed_trades['holding_days'].max() if 'holding_days' in self.closed_trades else 0,
            'min_hold_days': self.closed_trades['holding_days'].min() if 'holding_days' in self.closed_trades else 0,
            
            # Distribution
            'median_return_pct': self.closed_trades['profit_loss_pct'].median() if 'profit_loss_pct' in self.closed_trades else 0,
            'return_std_dev': self.closed_trades['profit_loss_pct'].std() if 'profit_loss_pct' in self.closed_trades else 0,
        }
        
        return metrics
    
    def _calculate_profit_factor(self, wins, losses):
        """Calculate profit factor (SQLite-safe)"""
        gross_profit = wins['profit_loss_dollars'].sum() if not wins.empty else 0
        gross_loss = abs(losses['profit_loss_dollars'].sum()) if not losses.empty else 0
        
        if gross_loss == 0:
            return 999999.0 if gross_profit > 0 else 0  # SQLite-safe large number
        
        return gross_profit / gross_loss
    
    def _calculate_risk_reward(self, wins, losses):
        """Calculate risk/reward ratio (SQLite-safe)"""
        avg_win = wins['profit_loss_dollars'].mean() if not wins.empty else 0
        avg_loss = abs(losses['profit_loss_dollars'].mean()) if not losses.empty else 0
        
        if avg_loss == 0:
            return 999999.0 if avg_win > 0 else 0  # SQLite-safe large number
        
        return avg_win / avg_loss

    def _calculate_expectancy(self, wins, losses, total_trades):
        """Calculate expectancy per trade"""
        if total_trades == 0:
            return 0
        
        win_rate = len(wins) / total_trades
        avg_win = wins['profit_loss_dollars'].mean() if not wins.empty else 0
        avg_loss = losses['profit_loss_dollars'].mean() if not losses.empty else 0
        
        return (win_rate * avg_win) + ((1 - win_rate) * avg_loss)
    
    def _empty_metrics(self):
        """Return empty metrics structure"""
        return {k: 0 for k in [
            'total_trades', 'completed_trades', 'open_positions',
            'winning_trades', 'losing_trades', 'win_rate_pct',
            'gross_profit', 'gross_loss', 'net_profit',
            'avg_win_dollars', 'avg_loss_dollars', 'avg_trade_dollars',
            'best_trade_dollars', 'worst_trade_dollars',
            'best_trade_pct', 'worst_trade_pct',
            'profit_factor', 'risk_reward_ratio', 'expectancy_dollars',
            'avg_hold_days', 'max_hold_days', 'min_hold_days',
            'median_return_pct', 'return_std_dev'
        ]}