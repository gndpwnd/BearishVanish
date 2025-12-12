"""
Enhanced Strategies with Improved SELL Signal Logic
Addresses flat-line issue by ensuring strategies generate exit signals
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from strategy_base import StrategyBase
import numpy as np
import pandas as pd

# ============================================================
# ENHANCED 500 INTERSECTION STRATEGY
# ============================================================

class Strategy500IntersectionEnhanced(StrategyBase):
    def __init__(self, color="blue"):
        super().__init__(name="500 Intersection Enhanced", color=color)
        self.holding_periods = {}  # Track how long we've held each position
        self.entry_prices = {}     # Track entry prices for profit/loss calculation
        
    def reset(self):
        super().reset()
        self.last_cross_index = {}
        self.last_cross_was_below = {}
        self.holding_periods = {}
        self.entry_prices = {}
    
    def detect_cross(self, stock_cum, sp500_cum):
        """Check if a crossover occurred at the last index"""
        if len(stock_cum) < 2:
            return False
        
        prev_diff = stock_cum.iloc[-2] - sp500_cum.iloc[-2]
        curr_diff = stock_cum.iloc[-1] - sp500_cum.iloc[-1]
        
        return prev_diff * curr_diff < 0
    
    def on_data(self, stock_data, spy_data, current_date, symbol):
        if len(stock_data) < 3:
            return None
        
        # Initialize tracking for this symbol
        if symbol not in self.last_cross_index:
            self.last_cross_index[symbol] = -1
            self.last_cross_was_below[symbol] = None
            self.holding_periods[symbol] = 0
            self.entry_prices[symbol] = None
        
        # Calculate cumulative returns
        stock_returns = stock_data['close'].pct_change().fillna(0)
        sp500_returns = spy_data['close'].pct_change().fillna(0)
        
        stock_cum = np.cumsum(stock_returns) * 100
        sp500_cum = np.cumsum(sp500_returns) * 100
        
        # Calculate slope
        stock_slope = np.gradient(stock_cum)
        
        current_idx = len(stock_cum) - 1
        current_price = stock_data['close'].iloc[-1]
        
        # Update holding period if we have a position
        if self.last_executed_signal.get(symbol) == 'BUY':
            self.holding_periods[symbol] += 1
        
        # Detect crossover
        if self.detect_cross(stock_cum, sp500_cum):
            self.last_cross_index[symbol] = current_idx
            self.last_cross_was_below[symbol] = stock_cum.iloc[-1] < sp500_cum.iloc[-1]
        
        # Need at least 2 slope values
        if current_idx < 2:
            return None
        
        prev_slope = stock_slope[-2]
        curr_slope = stock_slope[-1]
        
        # IMPROVED SELL LOGIC - Multiple exit conditions
        if self.last_executed_signal.get(symbol) == 'BUY':
            # Store entry price if not stored
            if self.entry_prices[symbol] is None:
                self.entry_prices[symbol] = stock_data['close'].iloc[self.last_cross_index[symbol]] if self.last_cross_index[symbol] != -1 else current_price
            
            entry_price = self.entry_prices[symbol]
            profit_pct = (current_price - entry_price) / entry_price * 100
            
            # Exit conditions (ANY of these trigger SELL):
            # 1. Take profit: +15% gain
            if profit_pct >= 15:
                if self.can_generate_signal('SELL', symbol):
                    self.holding_periods[symbol] = 0
                    self.entry_prices[symbol] = None
                    return self.emit_signal('SELL', symbol)
            
            # 2. Stop loss: -10% loss
            if profit_pct <= -10:
                if self.can_generate_signal('SELL', symbol):
                    self.holding_periods[symbol] = 0
                    self.entry_prices[symbol] = None
                    return self.emit_signal('SELL', symbol)
            
            # 3. Time-based exit: Held for 20+ bars (roughly 3 days) with any profit
            if self.holding_periods[symbol] >= 20 and profit_pct > 0:
                if self.can_generate_signal('SELL', symbol):
                    self.holding_periods[symbol] = 0
                    self.entry_prices[symbol] = None
                    return self.emit_signal('SELL', symbol)
            
            # 4. Original condition: crossed above SPY and slope turning down
            if (self.last_cross_index[symbol] != -1 and
                not self.last_cross_was_below[symbol] and
                prev_slope > 0 and curr_slope < 0 and
                stock_cum.iloc[-1] > sp500_cum.iloc[-1]):
                if self.can_generate_signal('SELL', symbol):
                    self.holding_periods[symbol] = 0
                    self.entry_prices[symbol] = None
                    return self.emit_signal('SELL', symbol)
        
        # BUY signal: crossed below SPY, now sloping up from negative
        if (self.last_cross_index[symbol] != -1 and
            self.last_cross_was_below[symbol] and
            prev_slope < 0 and curr_slope > 0 and
            stock_cum.iloc[-1] < sp500_cum.iloc[-1] and
            self.can_generate_signal('BUY', symbol)):
            self.entry_prices[symbol] = current_price
            self.holding_periods[symbol] = 0
            return self.emit_signal('BUY', symbol)
        
        return None


# ============================================================
# ENHANCED WEEKLY THRESHOLD STRATEGY
# ============================================================

class StrategyWeeklyThresholdEnhanced(StrategyBase):
    def __init__(self, color="red", buy_threshold=-0.05, sell_threshold=0.10):
        super().__init__(name="Weekly Threshold Enhanced", color=color)
        self.buy_threshold = buy_threshold
        self.sell_threshold = sell_threshold
        self.holding_periods = {}
        self.entry_prices = {}
        
    def reset(self):
        super().reset()
        self.last_monday_price = {}
        self.last_monday_date = {}
        self.holding_periods = {}
        self.entry_prices = {}
    
    def on_data(self, stock_data, spy_data, current_date, symbol):
        if len(stock_data) < 2:
            return None
        
        # Initialize tracking for this symbol
        if symbol not in self.last_monday_price:
            self.last_monday_price[symbol] = None
            self.last_monday_date[symbol] = None
            self.holding_periods[symbol] = 0
            self.entry_prices[symbol] = None
        
        current_price = stock_data['close'].iloc[-1]
        
        # Update holding period if we have a position
        if self.last_executed_signal.get(symbol) == 'BUY':
            self.holding_periods[symbol] += 1
        
        # IMPROVED SELL LOGIC - Check on every bar, not just Mondays
        if self.last_executed_signal.get(symbol) == 'BUY':
            if self.entry_prices[symbol] is None:
                self.entry_prices[symbol] = current_price
            
            entry_price = self.entry_prices[symbol]
            profit_pct = (current_price - entry_price) / entry_price * 100
            
            # Exit conditions (checked every bar):
            # 1. Take profit: +12% gain (slightly higher than original 10%)
            if profit_pct >= 12:
                if self.can_generate_signal('SELL', symbol):
                    self.holding_periods[symbol] = 0
                    self.entry_prices[symbol] = None
                    return self.emit_signal('SELL', symbol)
            
            # 2. Stop loss: -8% loss
            if profit_pct <= -8:
                if self.can_generate_signal('SELL', symbol):
                    self.holding_periods[symbol] = 0
                    self.entry_prices[symbol] = None
                    return self.emit_signal('SELL', symbol)
            
            # 3. Time-based exit: Held for 30+ bars (roughly 5 days) with any profit
            if self.holding_periods[symbol] >= 30 and profit_pct > 0:
                if self.can_generate_signal('SELL', symbol):
                    self.holding_periods[symbol] = 0
                    self.entry_prices[symbol] = None
                    return self.emit_signal('SELL', symbol)
        
        # BUY/SELL signals on Mondays (original logic)
        if current_date.weekday() == 0:  # Monday
            # If we have a previous Monday, check thresholds
            if self.last_monday_price[symbol] is not None:
                pct_change = (current_price - self.last_monday_price[symbol]) / self.last_monday_price[symbol]
                
                if pct_change <= self.buy_threshold and self.can_generate_signal('BUY', symbol):
                    self.entry_prices[symbol] = current_price
                    self.holding_periods[symbol] = 0
                    # Update for next week
                    self.last_monday_price[symbol] = current_price
                    self.last_monday_date[symbol] = current_date
                    return self.emit_signal('BUY', symbol)
                
                elif pct_change >= self.sell_threshold and self.can_generate_signal('SELL', symbol):
                    self.holding_periods[symbol] = 0
                    self.entry_prices[symbol] = None
                    # Update for next week
                    self.last_monday_price[symbol] = current_price
                    self.last_monday_date[symbol] = current_date
                    return self.emit_signal('SELL', symbol)
            
            # Update last Monday price
            self.last_monday_price[symbol] = current_price
            self.last_monday_date[symbol] = current_date
        
        return None


# ============================================================
# ALTERNATIVE: SIMPLER MOMENTUM STRATEGY
# ============================================================

class StrategySimpleMomentum(StrategyBase):
    """
    Simple momentum strategy with clear entry/exit rules
    Good for testing - should generate lots of trades
    """
    def __init__(self, color="green"):
        super().__init__(name="Simple Momentum", color=color)
        self.holding_periods = {}
        self.entry_prices = {}
        
    def reset(self):
        super().reset()
        self.holding_periods = {}
        self.entry_prices = {}
    
    def on_data(self, stock_data, spy_data, current_date, symbol):
        if len(stock_data) < 21:  # Need 20 bars for lookback
            return None
        
        # Initialize tracking
        if symbol not in self.holding_periods:
            self.holding_periods[symbol] = 0
            self.entry_prices[symbol] = None
        
        current_price = stock_data['close'].iloc[-1]
        sma_20 = stock_data['close'].iloc[-20:].mean()
        
        # Update holding period
        if self.last_executed_signal.get(symbol) == 'BUY':
            self.holding_periods[symbol] += 1
        
        # SELL conditions (check on every bar)
        if self.last_executed_signal.get(symbol) == 'BUY':
            if self.entry_prices[symbol] is None:
                self.entry_prices[symbol] = current_price
            
            entry_price = self.entry_prices[symbol]
            profit_pct = (current_price - entry_price) / entry_price * 100
            
            # Exit if:
            # 1. Take profit: +10% gain
            # 2. Stop loss: -5% loss
            # 3. Price crosses below 20-period SMA
            # 4. Held for 50+ bars (roughly 8 days)
            if (profit_pct >= 10 or 
                profit_pct <= -5 or 
                current_price < sma_20 or 
                self.holding_periods[symbol] >= 50):
                
                if self.can_generate_signal('SELL', symbol):
                    self.holding_periods[symbol] = 0
                    self.entry_prices[symbol] = None
                    return self.emit_signal('SELL', symbol)
        
        # BUY signal: Price crosses above 20-period SMA
        if current_price > sma_20 and stock_data['close'].iloc[-2] <= sma_20:
            if self.can_generate_signal('BUY', symbol):
                self.entry_prices[symbol] = current_price
                self.holding_periods[symbol] = 0
                return self.emit_signal('BUY', symbol)
        
        return None


# ============================================================
# HOW TO USE THESE STRATEGIES
# ============================================================

"""
OPTION 1: Replace existing strategies

In your strategies/ folder:
- Replace strategy_500_intersection.py with Strategy500IntersectionEnhanced
- Replace strategy_weekly.py with StrategyWeeklyThresholdEnhanced

OPTION 2: Add as new strategies

Create new files:
- strategies/strategy_500_intersection_enhanced.py
- strategies/strategy_weekly_threshold_enhanced.py
- strategies/strategy_simple_momentum.py

Each file should contain:

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from strategy_base import StrategyBase
import numpy as np

class Strategy(StrategyBase):
    # Copy the enhanced strategy code here
    # Change class name from Strategy500IntersectionEnhanced to Strategy
    pass

OPTION 3: Test with just Simple Momentum first

Create strategies/strategy_test.py:

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from strategy_base import StrategyBase

class Strategy(StrategyBase):
    def __init__(self, color="green"):
        super().__init__(name="Test Momentum", color=color)
        self.holding_periods = {}
        self.entry_prices = {}
    
    # ... copy StrategySimpleMomentum code here ...

Then run:
python simulator.py --universe sp500 --db-workers 21

You should see LOTS of trades and active portfolio movement!
"""