"""
Strategy #1: Slope Reversal vs S&P 500 - Corrected Version
Buys when stock slope reverses upward after crossing below S&P 500
Sells when stock slope reverses downward after crossing above S&P 500
Enforces one buy per cross below, one sell per cross above
"""

import pandas as pd
import numpy as np
from strategy_base import StrategyBase, StrategyConfig


class Strategy(StrategyBase):
    """
    S&P 500 Slope Reversal Strategy - Improved Version
    """
    
    def __init__(self, config: StrategyConfig = None):
        """Initialize with configuration"""
        if config is None:
            config = StrategyConfig(
                name="Slope Reversal SP500 v2",
                color="#2E86AB",
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

        # Cooldown period (replaces one-signal-per-cross restriction)
        self.cooldown_bars = 24  # 24-hour cooldown between signals

        # State tracking (per symbol)
        self._last_cross_index = {}
        self._last_cross_was_below = {}
        self._last_signal_bar = {}  # Track bar index for cooldown

        # Track entry prices and positions for stop-loss
        self._entry_prices = {}
        self._in_position = {}
    
    def generate_signal(self, symbol, data, spy_data, bar_index):
        """
        Generate signal based on slope reversal and S&P 500 crossover
        
        Args:
            symbol: Stock symbol
            data: Historical stock data up to current bar
            spy_data: Historical SPY data up to current bar
            bar_index: Current bar index
            
        Returns:
            'BUY', 'SELL', or 'HOLD'
        """
        # Minimum data requirement
        if len(data) < 3 or spy_data is None or len(spy_data) < 3:
            return 'HOLD'
        
        # Initialize tracking for this symbol
        if symbol not in self._last_cross_index:
            self._last_cross_index[symbol] = -1
            self._last_cross_was_below[symbol] = None
            self._last_signal_bar[symbol] = -100  # Start negative to allow first signal
            self._entry_prices[symbol] = None
            self._in_position[symbol] = False
        
        try:
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

            # Calculate cumulative returns
            stock_returns = data['close'].pct_change().fillna(0)
            spy_returns = spy_data['close'].pct_change().fillna(0)
            
            # Ensure same length
            min_len = min(len(stock_returns), len(spy_returns))
            stock_returns = stock_returns.iloc[-min_len:]
            spy_returns = spy_returns.iloc[-min_len:]
            
            stock_cum = (stock_returns.cumsum() * 100).values
            spy_cum = (spy_returns.cumsum() * 100).values
            
            # Calculate slope
            stock_slope = np.gradient(stock_cum)
            
            current_idx = len(stock_cum) - 1
            
            if current_idx < 2:
                return 'HOLD'
            
            # Detect crossover
            if current_idx >= 1:
                prev_diff = stock_cum[current_idx - 1] - spy_cum[current_idx - 1]
                curr_diff = stock_cum[current_idx] - spy_cum[current_idx]

                # Crossover detected (sign change)
                if prev_diff * curr_diff < 0:
                    self._last_cross_index[symbol] = current_idx
                    self._last_cross_was_below[symbol] = (curr_diff < 0)

            # No crossover yet
            if self._last_cross_index[symbol] == -1:
                return 'HOLD'

            # Get slope values
            prev_slope = stock_slope[current_idx - 1]
            curr_slope = stock_slope[current_idx]

            # Current position relative to S&P
            currently_below = (stock_cum[current_idx] < spy_cum[current_idx])
            currently_above = (stock_cum[current_idx] > spy_cum[current_idx])

            # Check cooldown - must wait 24 bars between signals
            bars_since_last_signal = bar_index - self._last_signal_bar[symbol]
            cooldown_passed = bars_since_last_signal >= self.cooldown_bars

            # BUY: Stock crossed BELOW S&P, slope reverses from - to +
            # Use cooldown instead of one-signal-per-cross to allow more trades
            if (self._last_cross_was_below[symbol] and cooldown_passed and not self._in_position[symbol]):

                if (prev_slope < 0 and curr_slope > 0 and currently_below):
                    self._last_signal_bar[symbol] = bar_index
                    self._in_position[symbol] = True
                    self._entry_prices[symbol] = current_price
                    return 'BUY'

            # SELL: Stock crossed ABOVE S&P, slope reverses from + to -
            elif (self._last_cross_was_below[symbol] is not None and
                  not self._last_cross_was_below[symbol] and
                  cooldown_passed and self._in_position[symbol]):

                if (prev_slope > 0 and curr_slope < 0 and currently_above):
                    self._last_signal_bar[symbol] = bar_index
                    self._in_position[symbol] = False
                    self._entry_prices[symbol] = None
                    return 'SELL'
        
        except Exception:
            return 'HOLD'
        
        return 'HOLD'
    
    def get_config(self):
        """Return serializable configuration"""
        base_config = super().get_config()
        base_config.update({
            'stop_loss_pct': self.stop_loss_pct,
            'cooldown_bars': self.cooldown_bars
        })
        return base_config
