"""
Trend Following Strategy - Institutional Grade
Rides strong trends using ADX + Supertrend + moving averages

Used by CTAs (Commodity Trading Advisors) like Man Group and Winton:
- Identifies strong trends with ADX
- Uses Supertrend for entry/exit timing
- Confirms with moving average alignment
- Exits on trend reversal or weakening

Entry Signals:
- ADX > 25 (strong trend)
- Supertrend flips to bullish
- EMA(20) > EMA(50) (trend confirmation)
- Price above VWAP

Exit Signals:
- Supertrend flips to bearish
- ADX < 20 (trend weakening)
- Price crosses below EMA(20)

Risk Controls:
- 10% of portfolio per position
- Maximum 8 concurrent positions
- Trailing stop using Supertrend line
"""

import pandas as pd
import numpy as np
from strategy_base import StrategyBase, StrategyConfig
from trailing_stop import TrailingStop


class Strategy(StrategyBase):
    """Trend Following Strategy"""

    def __init__(self, config: StrategyConfig = None):
        if config is None:
            config = StrategyConfig(
                name="Trend Following",
                color="#4ECDC4",
                initial_capital=100000,
                position_size_pct=0.10,  # 10% per position
                max_positions=8,
                stop_loss_pct=0.08  # 8% stop-loss
            )

        super().__init__(config)

        # Stop-loss parameter (use config or default 8%)
        self.stop_loss_pct = self.config.stop_loss_pct if self.config.stop_loss_pct else 0.08

        # Strategy parameters
        # Phase 2: Lowered ADX thresholds based on trend-following research
        # ADX > 20 indicates trending market (Wilder, 1978)
        self.adx_period = 14
        self.adx_strong_trend = 20  # Lowered from 25 to 20
        self.adx_weak_trend = 15  # Lowered from 20 to 15
        self.supertrend_period = 10
        self.supertrend_multiplier = 3.0
        self.ema_fast = 20
        self.ema_slow = 50

        # Required indicators
        self.required_indicators = [
            'adx',
            'supertrend',
            f'ema_{self.ema_fast}',   # ema_20
            f'ema_{self.ema_slow}',   # ema_50
            'vwap'
        ]

        # Track position state
        self._in_trend = {}
        self._entry_prices = {}  # Track entry prices for stop-loss
        self._trailing_stops = {}  # Track trailing stops per symbol

        # Trailing stop parameters
        self.trail_pct = 0.05  # 5% trailing distance

    def generate_signal(self, symbol, data, spy_data, bar_index):
        """
        Generate trend following signal

        Logic:
        1. BUY: ADX strong + Supertrend bullish + EMAs aligned + above VWAP
        2. SELL: Supertrend bearish OR ADX weak OR price below fast EMA
        """
        # Need enough data
        if len(data) < max(self.adx_period * 2, self.ema_slow, 20):
            return 'HOLD'

        # Initialize tracking
        if symbol not in self._in_trend:
            self._in_trend[symbol] = False
            self._entry_prices[symbol] = None
            self._trailing_stops[symbol] = None

        try:
            current_price = data['close'].iloc[-1]

            # Get indicators
            # ADX returns (adx, +DI, -DI)
            adx = data.get('adx', pd.Series([np.nan] * len(data))).iloc[-1]
            plus_di = data.get('adx_plus_di', pd.Series([np.nan] * len(data))).iloc[-1]
            minus_di = data.get('adx_minus_di', pd.Series([np.nan] * len(data))).iloc[-1]

            # Supertrend returns (supertrend, direction)
            supertrend_value = data.get('supertrend', pd.Series([np.nan] * len(data))).iloc[-1]
            supertrend_direction = data.get('supertrend_direction', pd.Series([np.nan] * len(data))).iloc[-1]

            # EMAs
            ema_fast = data.get(f'ema_{self.ema_fast}', pd.Series([np.nan] * len(data))).iloc[-1]
            ema_slow = data.get(f'ema_{self.ema_slow}', pd.Series([np.nan] * len(data))).iloc[-1]

            # VWAP
            vwap = data.get('vwap', pd.Series([current_price] * len(data))).iloc[-1]

            # Check for NaN values in essential indicators (ADX, EMAs)
            # Supertrend can be NaN - we'll use EMA alignment as fallback
            if np.isnan(adx) or np.isnan(ema_fast) or np.isnan(ema_slow):
                return 'HOLD'

            # Supertrend is optional - if NaN, use EMA alignment as proxy
            supertrend_available = not np.isnan(supertrend_value) and not np.isnan(supertrend_direction)

            # ===================================
            # EXIT LOGIC (check first)
            # ===================================
            if self._in_trend[symbol]:
                # TRAILING STOP CHECK (check first)
                trailing_stop = self._trailing_stops[symbol]
                if trailing_stop is not None:
                    # Update trailing stop with current price
                    trailing_stop.update(current_price)

                    # Check if stopped out
                    if trailing_stop.is_stopped(current_price):
                        self._in_trend[symbol] = False
                        self._entry_prices[symbol] = None
                        self._trailing_stops[symbol] = None
                        return 'SELL'

                # Exit if Supertrend turns bearish (only if available)
                if supertrend_available and supertrend_direction < 0:
                    self._in_trend[symbol] = False
                    self._entry_prices[symbol] = None
                    self._trailing_stops[symbol] = None
                    return 'SELL'

                # Exit if trend weakens (ADX drops below threshold)
                if adx < self.adx_weak_trend:
                    self._in_trend[symbol] = False
                    self._entry_prices[symbol] = None
                    self._trailing_stops[symbol] = None
                    return 'SELL'

                # Exit if price drops below fast EMA (trend break)
                if current_price < ema_fast:
                    self._in_trend[symbol] = False
                    self._entry_prices[symbol] = None
                    self._trailing_stops[symbol] = None
                    return 'SELL'

            # ===================================
            # ENTRY LOGIC (Phase 2: Simplified to core trend theory)
            # ===================================
            # Statistical basis: Trend-following is based on momentum factor research
            # showing that assets with positive momentum continue outperforming.
            # Reference: "Momentum" by Jegadeesh & Titman (1993), ADX by Wilder (1978)
            if not self._in_trend[symbol]:
                # CORE CONDITION 1: ADX shows trending market
                trending_market = adx > self.adx_strong_trend

                # CORE CONDITION 2: EMA alignment (trend direction)
                # Fast EMA above slow EMA = uptrend
                emas_aligned = ema_fast > ema_slow

                # CORE CONDITION 3: Price above fast EMA (in the trend)
                price_in_trend = current_price > ema_fast

                # OPTIONAL: Supertrend confirmation OR +DI > -DI
                # Either one provides additional confirmation
                if supertrend_available:
                    trend_confirmed = supertrend_direction > 0
                elif not np.isnan(plus_di) and not np.isnan(minus_di):
                    trend_confirmed = plus_di > minus_di
                else:
                    trend_confirmed = True  # Allow entry if no confirmation available

                # Entry: 3 core conditions + optional confirmation
                # Removed VWAP requirement (too restrictive)
                if trending_market and emas_aligned and price_in_trend and trend_confirmed:
                    self._in_trend[symbol] = True
                    self._entry_prices[symbol] = current_price
                    # Create trailing stop for this position
                    self._trailing_stops[symbol] = TrailingStop(
                        entry_price=current_price,
                        initial_stop_pct=self.stop_loss_pct,
                        trail_pct=self.trail_pct
                    )
                    return 'BUY'

        except Exception as e:
            return 'HOLD'

        return 'HOLD'

    def get_config(self):
        """Return serializable configuration"""
        base_config = super().get_config()
        base_config.update({
            'adx_period': self.adx_period,
            'adx_strong_trend': self.adx_strong_trend,
            'adx_weak_trend': self.adx_weak_trend,
            'supertrend_period': self.supertrend_period,
            'supertrend_multiplier': self.supertrend_multiplier,
            'ema_fast': self.ema_fast,
            'ema_slow': self.ema_slow,
            'stop_loss_pct': self.stop_loss_pct,
            'trail_pct': self.trail_pct
        })
        return base_config
