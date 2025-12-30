"""
500 Intersection Strategy - REFACTORED FOR OPTIMIZATION
Detects crossovers between stock and S&P 500, then waits for slope reversals

BUY: Stock crosses BELOW S&P 500, then slope reverses from negative to positive
SELL: Stock crosses ABOVE S&P 500, then slope reverses from positive to negative

Uses pre-computed indicators for performance
"""

import pandas as pd
import numpy as np
from strategy_base import StrategyBase, StrategyConfig

class Strategy(StrategyBase):
    """
    S&P 500 Intersection strategy with slope reversal detection
    """
    
    def __init__(self, config: StrategyConfig = None):
        """Initialize with configuration"""
        if config is None:
            config = StrategyConfig(
                name="500 Intersection",
                color="#FF6B6B",
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
        
        # Strategy parameters
        self.min_bars_after_cross = 1  # Minimum bars after crossover before signal
        self.atr_period = 14  # ATR period for volatility measurement
        self.cooldown_bars = 24  # 24-hour cooldown between signals (replaces one-signal-per-cross)

        # This strategy uses cumulative returns and slope calculations
        # We don't pre-compute these as they're simple operations
        # Note: 'atr' loads from indicator_atr.py (Numba JIT optimized)
        self.required_indicators = [
            'atr'  # Used for volatility-adjusted position sizing
        ]

        # State tracking (per symbol)
        # Note: This is OK because we're tracking historical events
        self._last_cross_index = {}
        self._last_cross_was_below = {}
        self._last_signal_bar = {}  # Track bar index when we last emitted a signal (for cooldown)

        # Track entry prices and positions for stop-loss
        self._entry_prices = {}
        self._in_position = {}
    
    def generate_signal(self, symbol, data, spy_data, bar_index):
        """
        Generate signal based on crossover and slope reversal
        
        Args:
            symbol: Stock symbol
            data: Historical stock data up to current bar
            spy_data: Historical SPY data up to current bar
            bar_index: Current bar index
            
        Returns:
            'BUY', 'SELL', or 'HOLD'
        """
        # Need minimum data
        if len(data) < 3 or spy_data is None or len(spy_data) < 3:
            return 'HOLD'
        
        # Initialize tracking for this symbol
        if symbol not in self._last_cross_index:
            self._last_cross_index[symbol] = -1
            self._last_cross_was_below[symbol] = None
            self._last_signal_bar[symbol] = -100  # Start with negative to allow first signal
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

            # Calculate cumulative returns (simple, fast operation)
            stock_returns = data['close'].pct_change().fillna(0)
            spy_returns = spy_data['close'].pct_change().fillna(0)
            
            # Ensure same length
            min_len = min(len(stock_returns), len(spy_returns))
            stock_returns = stock_returns.iloc[-min_len:]
            spy_returns = spy_returns.iloc[-min_len:]
            
            stock_cum = (stock_returns.cumsum() * 100).values
            spy_cum = (spy_returns.cumsum() * 100).values
            
            # Calculate slope (gradient of cumulative returns)
            stock_slope = np.gradient(stock_cum)
            
            # Current position in arrays
            current_idx = len(stock_cum) - 1
            
            # Need at least 2 points for slope comparison
            if current_idx < 2:
                return 'HOLD'
            
            # ===================================
            # DETECT CROSSOVER
            # ===================================
            # Check if crossover occurred at current bar
            if current_idx >= 1:
                prev_diff = stock_cum[current_idx - 1] - spy_cum[current_idx - 1]
                curr_diff = stock_cum[current_idx] - spy_cum[current_idx]
                
                # Crossover: signs change
                if prev_diff * curr_diff < 0:
                    self._last_cross_index[symbol] = current_idx
                    self._last_cross_was_below[symbol] = (curr_diff < 0)
            
            # Check if we've had a crossover
            if self._last_cross_index[symbol] == -1:
                return 'HOLD'
            
            # Get slope values
            prev_slope = stock_slope[current_idx - 1]
            curr_slope = stock_slope[current_idx]
            
            # Current position relative to S&P
            currently_below_sp500 = (stock_cum[current_idx] < spy_cum[current_idx])
            
            # Check cooldown - must wait 24 bars between signals
            bars_since_last_signal = bar_index - self._last_signal_bar[symbol]
            cooldown_passed = bars_since_last_signal >= self.cooldown_bars

            # ===================================
            # BUY SIGNAL (Phase 2: Simplified relative strength logic)
            # ===================================
            # Statistical basis: Relative strength reversion
            # When a stock underperforms and starts recovering, it may mean-revert
            # Reference: "On Persistence in Mutual Fund Performance" by Carhart (1997)
            if cooldown_passed and not self._in_position[symbol]:
                # Original pattern: crossover + slope reversal
                original_buy = (self._last_cross_was_below[symbol] and
                               prev_slope < 0 and curr_slope > 0 and currently_below_sp500)

                # Phase 2 SIMPLE pattern: Stock underperforming but slope turning positive
                # This is based on relative strength reversion theory
                simple_buy = (currently_below_sp500 and curr_slope > 0 and
                             stock_cum[current_idx] < stock_cum[current_idx - 1] * 1.02)  # Was flat/down

                # Enter if EITHER pattern matches
                if original_buy or simple_buy:
                    self._last_signal_bar[symbol] = bar_index
                    self._in_position[symbol] = True
                    self._entry_prices[symbol] = current_price
                    return 'BUY'

            # ===================================
            # SELL SIGNAL
            # ===================================
            # Exit when in position and:
            # 1. Slope turns negative (momentum lost)
            # 2. Stock outperforms S&P (mean reversion complete)
            if self._in_position[symbol] and cooldown_passed:
                # Original sell: crossover + slope reversal
                original_sell = (self._last_cross_was_below[symbol] is not None and
                                not self._last_cross_was_below[symbol] and
                                prev_slope > 0 and curr_slope < 0 and not currently_below_sp500)

                # Simple sell: Now outperforming S&P (goal achieved) or slope negative
                simple_sell = not currently_below_sp500 or curr_slope < -0.5

                if original_sell or simple_sell:
                    self._last_signal_bar[symbol] = bar_index
                    self._in_position[symbol] = False
                    self._entry_prices[symbol] = None
                    return 'SELL'
            
        except Exception as e:
            # Handle any calculation errors gracefully
            return 'HOLD'
        
        return 'HOLD'
    
    def get_config(self):
        """Return serializable configuration"""
        base_config = super().get_config()
        base_config.update({
            'min_bars_after_cross': self.min_bars_after_cross,
            'stop_loss_pct': self.stop_loss_pct,
            'atr_period': self.atr_period,
            'cooldown_bars': self.cooldown_bars
        })
        return base_config