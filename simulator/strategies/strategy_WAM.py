"""
Weekly Threshold Strategy - WEEK-BY-WEEK ONLY
Buy on drops, sell on rises over 7-day rolling window

BUY: Stock drops 5%+ over past 7 days
SELL: Stock rises 10%+ over past 7 days

Uses simple price comparisons for maximum performance
"""

import pandas as pd
import numpy as np
from strategy_base import StrategyBase, StrategyConfig

class Strategy(StrategyBase):
    """
    Rolling window threshold strategy
    """
    
    def __init__(self, config: StrategyConfig = None):
        """Initialize with configuration"""
        if config is None:
            config = StrategyConfig(
                name="Weekly Threshold",
                color="#4ECDC4",
                initial_capital=100000,
                position_size_pct=0.05,
                max_positions=20,  # More positions since shorter holds
                # Stop-loss widened to 8% to account for:
                # - 0.1% entry slippage (effectively 7.9% from true entry)
                # - Intraday volatility and gap risk
                # - Allow trades room to breathe before triggering stops
                stop_loss_pct=0.08  # 8% stop-loss
            )

        super().__init__(config)

        # Stop-loss widened to 8% to account for:
        # - 0.1% entry slippage (effectively 7.9% from true entry)
        # - Intraday volatility and gap risk
        # - Allow trades room to breathe before triggering stops
        self.stop_loss_pct = self.config.stop_loss_pct if self.config.stop_loss_pct else 0.08
        
        # Strategy parameters
        # Entry threshold relaxed to -0.02 to capture more opportunities
        # Original -0.05 was too restrictive, missing many recoveries
        self.buy_threshold = -0.02    # -2% drop to buy (relaxed from -5%)
        self.sell_threshold = 0.10    # +10% rise to sell
        self.window = 7               # Weekly window ONLY

        # No indicators needed - we calculate returns directly
        self.required_indicators = []

        # Track last signal (to prevent repeated signals)
        self._last_signal = {}

        # Track entry prices for stop-loss
        self._entry_prices = {}
    
    def generate_signal(self, symbol, data, spy_data, bar_index):
        """
        Generate signal based on 7-day rolling window returns

        Args:
            symbol: Stock symbol
            data: Historical stock data up to current bar
            spy_data: Historical SPY data (not used)
            bar_index: Current bar index

        Returns:
            'BUY', 'SELL', or 'HOLD'
        """
        # Need at least window bars
        if len(data) < self.window:
            return 'HOLD'

        # Initialize tracking for this symbol
        if symbol not in self._last_signal:
            self._last_signal[symbol] = None
            self._entry_prices[symbol] = None

        try:
            # Get current price
            current_price = data['close'].iloc[-1]
            
            # ===================================
            # CALCULATE 7-DAY ROLLING RETURN
            # ===================================

            price_7d_ago = data['close'].iloc[-self.window]
            return_7d = (current_price - price_7d_ago) / price_7d_ago

            # ===================================
            # STOP-LOSS CHECK (check first if in position)
            # ===================================
            if self._last_signal[symbol] == 'BUY':
                entry_price = self._entry_prices[symbol]
                if entry_price is not None and current_price < entry_price * (1 - self.stop_loss_pct):
                    self._last_signal[symbol] = 'SELL'
                    self._entry_prices[symbol] = None
                    return 'SELL'

            # ===================================
            # MARKET REGIME FILTER - Only buy in bull markets
            # ===================================
            if spy_data is not None and len(spy_data) >= 200:
                spy_sma_200 = spy_data['close'].rolling(200).mean().iloc[-1]
                spy_price = spy_data['close'].iloc[-1]
                if spy_price < spy_sma_200:
                    # Bear market - don't open new positions
                    if self._last_signal[symbol] != 'BUY':
                        return 'HOLD'

            # ===================================
            # WEEKLY WINDOW SIGNALS (ONLY)
            # ===================================

            # BUY: Dropped 5%+ in past week
            if return_7d <= self.buy_threshold:
                if self._last_signal[symbol] is None or self._last_signal[symbol] == 'SELL':
                    # Volume confirmation - only buy on above-average volume
                    if 'volume' in data.columns and len(data) >= 20:
                        avg_volume = data['volume'].iloc[-20:].mean()
                        current_volume = data['volume'].iloc[-1]
                        if current_volume < avg_volume * 1.0:  # At least average volume
                            return 'HOLD'  # Wait for better volume
                    self._last_signal[symbol] = 'BUY'
                    self._entry_prices[symbol] = current_price
                    return 'BUY'

            # SELL: Rose 10%+ in past week (if we bought)
            elif return_7d >= self.sell_threshold:
                if self._last_signal[symbol] == 'BUY':
                    self._last_signal[symbol] = 'SELL'
                    self._entry_prices[symbol] = None
                    return 'SELL'

            # Reset if price recovers to neutral (-2% to +2%)
            elif -0.02 < return_7d < 0.02:
                if self._last_signal[symbol] == 'SELL':
                    self._last_signal[symbol] = None
            
        except Exception as e:
            return 'HOLD'
        
        return 'HOLD'
    
    def get_config(self):
        """Return serializable configuration"""
        base_config = super().get_config()
        base_config.update({
            'buy_threshold': self.buy_threshold,
            'sell_threshold': self.sell_threshold,
            'window': self.window,
            'stop_loss_pct': self.stop_loss_pct
        })
        return base_config