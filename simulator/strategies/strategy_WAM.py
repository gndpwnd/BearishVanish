"""
Weekly Threshold Strategy - PURE LOGIC WITH ROLLING WINDOWS
Buy if stock drops 5% over past 7 days or 30 days
Sell if stock rises 10% over past 7 days or 30 days

Uses rolling windows instead of calendar dates
Separate tracking for weekly and monthly signals
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from strategy_base import StrategyBase
import pandas as pd

class Strategy(StrategyBase):
    def __init__(self, color="red", buy_threshold=-0.05, sell_threshold=0.10,
                 initial_capital=100000, position_size_pct=0.05, max_positions=1000):
        super().__init__(
            name="Weekly Threshold", 
            color=color,
            initial_capital=initial_capital,
            position_size_pct=position_size_pct,
            max_positions=max_positions
        )
        self.buy_threshold = buy_threshold      # -5% for buy
        self.sell_threshold = sell_threshold    # +10% for sell
        
    def reset(self):
        super().reset()
        # Track last executed signal per timeframe per symbol
        self.last_weekly_signal = {}   # 'BUY', 'SELL', or None
        self.last_monthly_signal = {}  # 'BUY', 'SELL', or None
    
    def on_data(self, stock_data, spy_data, current_date, symbol):
        # Need at least 30 bars for monthly calculation
        if len(stock_data) < 30:
            return None
        
        # Initialize tracking for this symbol
        if symbol not in self.last_weekly_signal:
            self.last_weekly_signal[symbol] = None
            self.last_monthly_signal[symbol] = None
        
        current_price = stock_data['close'].iloc[-1]
        
        # ==============================================================
        # CALCULATE ROLLING RETURNS
        # ==============================================================
        
        # 7-day return (1 week)
        if len(stock_data) >= 7:
            price_7d_ago = stock_data['close'].iloc[-7]
            return_7d = (current_price - price_7d_ago) / price_7d_ago
        else:
            return_7d = 0
        
        # 30-day return (1 month)
        price_30d_ago = stock_data['close'].iloc[-30]
        return_30d = (current_price - price_30d_ago) / price_30d_ago
        
        # ==============================================================
        # WEEKLY SIGNALS (7-day rolling window)
        # ==============================================================
        
        # BUY if dropped 5%+ in past week AND last weekly signal wasn't BUY
        if return_7d <= self.buy_threshold:
            if self.last_weekly_signal[symbol] != 'BUY' and self.can_generate_signal('BUY', symbol):
                self.last_weekly_signal[symbol] = 'BUY'
                return self.emit_signal('BUY', symbol)
        
        # SELL if rose 10%+ in past week AND had a weekly BUY before
        elif return_7d >= self.sell_threshold:
            if self.last_weekly_signal[symbol] == 'BUY' and self.can_generate_signal('SELL', symbol):
                self.last_weekly_signal[symbol] = 'SELL'
                return self.emit_signal('SELL', symbol)
        
        # ==============================================================
        # MONTHLY SIGNALS (30-day rolling window)
        # ==============================================================
        
        # BUY if dropped 5%+ in past month AND last monthly signal wasn't BUY
        if return_30d <= self.buy_threshold:
            if self.last_monthly_signal[symbol] != 'BUY' and self.can_generate_signal('BUY', symbol):
                self.last_monthly_signal[symbol] = 'BUY'
                return self.emit_signal('BUY', symbol)
        
        # SELL if rose 10%+ in past month AND had a monthly BUY before
        elif return_30d >= self.sell_threshold:
            if self.last_monthly_signal[symbol] == 'BUY' and self.can_generate_signal('SELL', symbol):
                self.last_monthly_signal[symbol] = 'SELL'
                return self.emit_signal('SELL', symbol)
        
        return None