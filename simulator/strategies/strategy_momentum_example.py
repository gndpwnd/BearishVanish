"""
Momentum Strategy - REFACTORED FOR OPTIMIZATION
Golden Cross / Death Cross with RSI filter
Uses pre-computed indicators for maximum performance
"""

import pandas as pd
import numpy as np
from strategy_base import StrategyBase, StrategyConfig

class Strategy(StrategyBase):
    """
    Momentum strategy using moving average crossovers
    
    BUY: Fast MA crosses above Slow MA, RSI < 70
    SELL: Fast MA crosses below Slow MA, RSI > 30
    """
    
    def __init__(self, config: StrategyConfig = None):
        """Initialize with configuration"""
        if config is None:
            config = StrategyConfig(
                name="Momentum Example",
                color="#1f77b4",
                initial_capital=100000,
                position_size_pct=0.10,
                max_positions=10,
                # Stop-loss widened to 10% to account for:
                # - 0.1% entry slippage (effectively 9.9% from true entry)
                # - Intraday volatility and gap risk
                # - Allow trades room to breathe before triggering stops
                stop_loss_pct=0.10  # 10% stop-loss
            )

        super().__init__(config)

        # Stop-loss widened to 10% to account for:
        # - 0.1% entry slippage (effectively 9.9% from true entry)
        # - Intraday volatility and gap risk
        # - Allow trades room to breathe before triggering stops
        self.stop_loss_pct = self.config.stop_loss_pct if self.config.stop_loss_pct else 0.10
        
        # Strategy parameters (configurable)
        self.fast_period = 20
        self.slow_period = 50
        self.rsi_period = 14
        self.rsi_overbought = 70
        self.rsi_oversold = 30
        
        # Declare required indicators (pre-computed)
        self.required_indicators = [
            f'sma_{self.fast_period}',
            f'sma_{self.slow_period}',
            f'rsi_{self.rsi_period}'
        ]

        # Track entry prices and positions for stop-loss
        self._entry_prices = {}
        self._in_position = {}
    
    def generate_signal(self, symbol, data, spy_data, bar_index):
        """
        Generate signal using pre-computed indicators
        
        Args:
            symbol: Stock symbol
            data: Historical data up to current bar (includes pre-computed indicators)
            spy_data: SPY data (optional)
            bar_index: Current bar index
            
        Returns:
            'BUY', 'SELL', or 'HOLD'
        """
        # Need at least slow_period + 1 bars
        if len(data) < self.slow_period + 1:
            return 'HOLD'

        # Initialize tracking for this symbol
        if symbol not in self._in_position:
            self._in_position[symbol] = False
            self._entry_prices[symbol] = None

        # Column names for indicators
        fast_ma_col = f'sma_{self.fast_period}'
        slow_ma_col = f'sma_{self.slow_period}'
        rsi_col = f'rsi_{self.rsi_period}'
        
        try:
            # Current bar (last in historical data)
            fast_ma_now = data[fast_ma_col].iloc[-1]
            slow_ma_now = data[slow_ma_col].iloc[-1]
            rsi_now = data[rsi_col].iloc[-1]
            
            # Previous bar (for crossover detection)
            fast_ma_prev = data[fast_ma_col].iloc[-2]
            slow_ma_prev = data[slow_ma_col].iloc[-2]
            
            # Check for NaN
            if pd.isna(fast_ma_now) or pd.isna(slow_ma_now) or pd.isna(rsi_now):
                return 'HOLD'
            if pd.isna(fast_ma_prev) or pd.isna(slow_ma_prev):
                return 'HOLD'
            
        except (KeyError, IndexError):
            # Indicator columns don't exist or not enough data
            return 'HOLD'

        # Get current price for stop-loss check
        current_price = data['close'].iloc[-1]

        # ===================================
        # STOP-LOSS CHECK (check first if in position)
        # ===================================
        if self._in_position[symbol]:
            entry_price = self._entry_prices[symbol]
            if entry_price is not None and current_price < entry_price * (1 - self.stop_loss_pct):
                self._in_position[symbol] = False
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
                if not self._in_position.get(symbol, False):
                    return 'HOLD'

        # ===================================
        # BUY SIGNAL: Golden Cross
        # ===================================
        # Fast MA crosses ABOVE Slow MA
        # AND RSI is not overbought
        if (fast_ma_prev <= slow_ma_prev and
            fast_ma_now > slow_ma_now and
            rsi_now < 80 and  # Relaxed from 70 - allow entries in stronger trends
            not self._in_position[symbol]):
            # Volume confirmation - only buy on above-average volume
            if 'volume' in data.columns and len(data) >= 20:
                avg_volume = data['volume'].iloc[-20:].mean()
                current_volume = data['volume'].iloc[-1]
                if current_volume < avg_volume * 1.0:  # At least average volume
                    return 'HOLD'  # Wait for better volume
            self._in_position[symbol] = True
            self._entry_prices[symbol] = current_price
            return 'BUY'

        # ===================================
        # SELL SIGNAL: Death Cross
        # ===================================
        # Fast MA crosses BELOW Slow MA
        # AND RSI is not oversold
        elif (fast_ma_prev >= slow_ma_prev and
              fast_ma_now < slow_ma_now and
              rsi_now > self.rsi_oversold and
              self._in_position[symbol]):
            self._in_position[symbol] = False
            self._entry_prices[symbol] = None
            return 'SELL'

        return 'HOLD'
    
    def get_config(self):
        """Return serializable configuration"""
        base_config = super().get_config()
        base_config.update({
            'fast_period': self.fast_period,
            'slow_period': self.slow_period,
            'rsi_period': self.rsi_period,
            'rsi_overbought': self.rsi_overbought,
            'rsi_oversold': self.rsi_oversold,
            'stop_loss_pct': self.stop_loss_pct
        })
        return base_config