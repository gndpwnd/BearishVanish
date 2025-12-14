"""
Mock Tracker Classes
For compatibility with existing analysis modules
"""

import numpy as np
import pandas as pd

class MockTracker:
    """Mock StrategyTracker for database analysis"""
    def __init__(self, name, trades_df, portfolio_df):
        self.name = name
        self.trades = trades_df.to_dict('records')
        self.dates = portfolio_df['date'].tolist() if not portfolio_df.empty else []
        self.portfolio_value_history = portfolio_df['portfolio_value'].tolist() if not portfolio_df.empty else []
        self.cash = portfolio_df['cash'].iloc[-1] if 'cash' in portfolio_df.columns and not portfolio_df.empty else 100000
        
    def get_return_pct(self):
        if len(self.portfolio_value_history) < 2:
            return 0.0
        return ((self.portfolio_value_history[-1] - self.portfolio_value_history[0]) / 
                self.portfolio_value_history[0]) * 100
    
    def get_profit_dollars(self):
        if len(self.portfolio_value_history) < 2:
            return 0.0
        return self.portfolio_value_history[-1] - self.portfolio_value_history[0]
    
    def get_winning_trades(self):
        closed = [t for t in self.trades if t.get('trade_status') == 'CLOSED']
        return [t for t in closed if t.get('profit_loss_dollars', 0) > 0]
    
    def get_losing_trades(self):
        closed = [t for t in self.trades if t.get('trade_status') == 'CLOSED']
        return [t for t in closed if t.get('profit_loss_dollars', 0) < 0]
    
    def get_max_drawdown(self):
        if len(self.portfolio_value_history) == 0:
            return 0.0
        values = np.array(self.portfolio_value_history)
        running_max = np.maximum.accumulate(values)
        drawdowns = (values - running_max) / running_max * 100
        return np.min(drawdowns) if len(drawdowns) > 0 else 0.0
    
    def get_current_position_count(self):
        open_trades = [t for t in self.trades if t.get('trade_status') == 'OPEN']
        return len(open_trades)
    
    def get_final_value(self):
        return self.portfolio_value_history[-1] if self.portfolio_value_history else 0

class MockStrategy:
    """Mock Strategy for compatibility"""
    def __init__(self, name):
        self.name = name