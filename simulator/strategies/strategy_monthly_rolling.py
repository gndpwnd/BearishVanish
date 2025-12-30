"""
Strategy #3: Monthly Rolling Window Only
Simplified version - uses only 30-day rolling window
"""

import pandas as pd
from strategy_base import StrategyBase, StrategyConfig


class Strategy(StrategyBase):
    """
    Rolling Window Threshold Strategy - Monthly Only
    Simpler version than rolling_windows.py
    """
    
    def __init__(self, config: StrategyConfig = None):
        """Initialize with configuration"""
        if config is None:
            config = StrategyConfig(
                name="Monthly Rolling",
                color="#F18F01",
                initial_capital=100000,
                position_size_pct=0.10,
                max_positions=10,
                stop_loss_pct=0.08  # 8% stop-loss
            )

        super().__init__(config)

        # Stop-loss parameter (use config or default 8%)
        self.stop_loss_pct = self.config.stop_loss_pct if self.config.stop_loss_pct else 0.08
        
        # Window parameters (in bars - assuming daily bars)
        self.window = 30  # 30 trading days
        
        # Thresholds
        self.buy_threshold = -0.05  # -5%
        self.sell_threshold = 0.10  # +10%
        
        # State tracking (per symbol)
        self._state = {}

        # Track entry prices for stop-loss
        self._entry_prices = {}
    
    def generate_signal(self, symbol, data, spy_data, bar_index):
        """
        Generate signals based on 30-day rolling window returns
        
        Args:
            symbol: Stock symbol
            data: Historical stock data up to current bar
            spy_data: Historical SPY data (not used)
            bar_index: Current bar index
            
        Returns:
            'BUY', 'SELL', or 'HOLD'
        """
        # Need minimum data
        if len(data) < self.window + 1:
            return 'HOLD'
        
        # Initialize tracking for this symbol
        if symbol not in self._state:
            self._state[symbol] = None
            self._entry_prices[symbol] = None

        try:
            current_price = data['close'].iloc[-1]
            price_30d_ago = data['close'].iloc[-self.window]

            # Calculate 30-day return
            return_30d = (current_price - price_30d_ago) / price_30d_ago

            # ===================================
            # STOP-LOSS CHECK (check first if in position)
            # ===================================
            if self._state[symbol] == 'BUY':
                entry_price = self._entry_prices[symbol]
                if entry_price is not None and current_price < entry_price * (1 - self.stop_loss_pct):
                    self._state[symbol] = 'SELL'
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
                    if self._state[symbol] != 'BUY':
                        return 'HOLD'

            # BUY: Down 5%+ in past 30 days
            if return_30d <= self.buy_threshold:
                if self._state[symbol] is None or self._state[symbol] == 'SELL':
                    self._state[symbol] = 'BUY'
                    self._entry_prices[symbol] = current_price
                    return 'BUY'

            # SELL: Up 10%+ in past 30 days (if we bought)
            elif return_30d >= self.sell_threshold:
                if self._state[symbol] == 'BUY':
                    self._state[symbol] = 'SELL'
                    self._entry_prices[symbol] = None
                    return 'SELL'
            
            # Reset if recovered to neutral (-2% to +2%)
            elif -0.02 < return_30d < 0.02:
                if self._state[symbol] == 'SELL':
                    self._state[symbol] = None
        
        except Exception:
            return 'HOLD'
        
        return 'HOLD'
    
    def get_config(self):
        """Return serializable configuration"""
        base_config = super().get_config()
        base_config.update({
            'window': self.window,
            'buy_threshold': self.buy_threshold,
            'sell_threshold': self.sell_threshold,
            'stop_loss_pct': self.stop_loss_pct
        })
        return base_config
