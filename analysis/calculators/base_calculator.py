"""
Base Calculator Class
All calculators inherit from this
"""

from abc import ABC, abstractmethod
import pandas as pd
import numpy as np


class BaseCalculator(ABC):
    """
    Abstract base class for all metric calculators
    
    Each calculator:
    - Takes SimulationReader as input
    - Computes specific metrics
    - Returns structured dict/dataframe
    """
    
    def __init__(self, reader, strategy_name):
        """
        Initialize calculator
        
        Args:
            reader: SimulationReader instance
            strategy_name: Strategy to analyze
        """
        self.reader = reader
        self.strategy_name = strategy_name
        
        # Load common data
        self._load_data()
    
    def _load_data(self):
        """Load data from simulation database"""
        self.trades = self.reader.get_trade_history(self.strategy_name)
        self.closed_trades = self.reader.get_closed_trades(self.strategy_name)
        self.portfolio = self.reader.get_portfolio_history(self.strategy_name)
        self.performance = self.reader.get_strategy_performance(self.strategy_name)
    
    @abstractmethod
    def calculate(self):
        """
        Calculate metrics
        
        Returns:
            dict or DataFrame with calculated metrics
        """
        pass
    
    def get_returns_series(self):
        """Helper: Get returns series"""
        if self.portfolio.empty:
            return pd.Series()
        return self.portfolio['portfolio_value'].pct_change().dropna()
    
    def get_trading_days(self):
        """Helper: Get number of trading days"""
        if self.portfolio.empty:
            return 0
        return len(self.portfolio)