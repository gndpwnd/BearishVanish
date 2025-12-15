# ============================================================================
# FILE 6: calculators/streak_metrics.py
# ============================================================================

"""
Streak Metrics Calculator
Win/loss streaks and patterns
"""

from .base_calculator import BaseCalculator
import numpy as np


class StreakMetricsCalculator(BaseCalculator):
    """Calculate win/loss streaks"""
    
    def calculate(self):
        """
        Calculate streak metrics
        
        Returns:
            dict: Streak statistics
            list: List of significant streaks
        """
        if self.closed_trades.empty:
            return {'metrics': self._empty_metrics(), 'streaks': []}
        
        # Create outcomes array (1 = win, 0 = loss)
        outcomes = (self.closed_trades['profit_loss_dollars'] > 0).astype(int).values
        
        # Calculate streaks
        win_streaks = self._find_streaks(outcomes, 1)
        loss_streaks = self._find_streaks(outcomes, 0)
        
        # Current streak
        current_streak_len = self._calculate_current_streak(outcomes)
        current_streak_type = 'WIN' if outcomes[-1] == 1 else 'LOSS'
        
        metrics = {
            'max_win_streak': max(win_streaks) if win_streaks else 0,
            'max_loss_streak': max(loss_streaks) if loss_streaks else 0,
            'avg_win_streak': np.mean(win_streaks) if win_streaks else 0,
            'avg_loss_streak': np.mean(loss_streaks) if loss_streaks else 0,
            'current_streak': current_streak_len,
            'current_streak_type': current_streak_type,
            'num_win_streaks_3plus': sum(1 for s in win_streaks if s >= 3),
            'num_loss_streaks_3plus': sum(1 for s in loss_streaks if s >= 3),
        }
        
        # Detailed streak periods
        streaks = self._identify_streak_periods(outcomes)
        
        return {'metrics': metrics, 'streaks': streaks}
    
    def _find_streaks(self, outcomes, target):
        """Find all streaks of target value"""
        streaks = []
        current_streak = 0
        
        for outcome in outcomes:
            if outcome == target:
                current_streak += 1
            else:
                if current_streak > 0:
                    streaks.append(current_streak)
                current_streak = 0
        
        if current_streak > 0:
            streaks.append(current_streak)
        
        return streaks
    
    def _calculate_current_streak(self, outcomes):
        """Calculate current streak length"""
        if len(outcomes) == 0:
            return 0
        
        target = outcomes[-1]
        streak = 0
        
        for i in range(len(outcomes) - 1, -1, -1):
            if outcomes[i] == target:
                streak += 1
            else:
                break
        
        return streak
    
    def _identify_streak_periods(self, outcomes):
        """Identify streak periods with dates and P&L"""
        streaks = []
        current_streak = []
        current_type = None
        
        for i, outcome in enumerate(outcomes):
            outcome_type = 'WIN' if outcome == 1 else 'LOSS'
            
            if current_type is None:
                current_type = outcome_type
                current_streak = [i]
            elif outcome_type == current_type:
                current_streak.append(i)
            else:
                # Streak ended
                if len(current_streak) >= 3:  # Only record streaks of 3+
                    streak_data = self._create_streak_data(current_streak, current_type)
                    streaks.append(streak_data)
                
                current_type = outcome_type
                current_streak = [i]
        
        # Handle last streak
        if len(current_streak) >= 3:
            streak_data = self._create_streak_data(current_streak, current_type)
            streaks.append(streak_data)
        
        return streaks
    
    def _create_streak_data(self, indices, streak_type):
        """Create streak data dict"""
        trades = self.closed_trades.iloc[indices]
        
        return {
            'streak_type': streak_type,
            'length': len(indices),
            'start_date': str(trades.iloc[0]['entry_date']),
            'end_date': str(trades.iloc[-1]['exit_date']) if 'exit_date' in trades.columns else None,
            'cumulative_pnl': trades['profit_loss_dollars'].sum(),
        }
    
    def _empty_metrics(self):
        """Return empty metrics structure"""
        return {
            'max_win_streak': 0,
            'max_loss_streak': 0,
            'avg_win_streak': 0,
            'avg_loss_streak': 0,
            'current_streak': 0,
            'current_streak_type': None,
            'num_win_streaks_3plus': 0,
            'num_loss_streaks_3plus': 0,
        }