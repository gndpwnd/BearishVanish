"""
Advanced Multi-Indicator Strategy - OPTIMIZATION SHOWCASE
Combines multiple indicators with volume confirmation

BUY: Multiple bullish signals align
SELL: Multiple bearish signals align

Demonstrates:
- Multiple indicator types
- Volume confirmation
- SPY market filter
- Complex signal logic
- Full pre-computation advantage
"""

import pandas as pd
import numpy as np
from strategy_base import StrategyBase, StrategyConfig

class Strategy(StrategyBase):
    """
    Advanced strategy combining trend, momentum, and volume
    """
    
    def __init__(self, config: StrategyConfig = None):
        """Initialize with configuration"""
        if config is None:
            config = StrategyConfig(
                name="Advanced Multi-Indicator",
                color="#96CEB4",
                initial_capital=100000,
                position_size_pct=0.08,
                max_positions=12
            )
        
        super().__init__(config)
        
        # ===================================
        # Strategy Parameters
        # ===================================
        
        # Moving averages
        self.fast_ma = 20
        self.slow_ma = 50
        self.trend_ma = 200
        
        # Momentum
        self.rsi_period = 14
        self.rsi_oversold = 35
        self.rsi_overbought = 65
        
        # Volatility
        self.bb_period = 20
        self.bb_std = 2.0
        
        # Volume
        self.volume_period = 20
        self.min_relative_volume = 1.2
        
        # Market filter (SPY)
        self.spy_ma = 200
        
        # ===================================
        # Required Indicators (pre-computed)
        # ===================================
        self.required_indicators = [
            # Stock indicators
            f'sma_{self.fast_ma}',
            f'sma_{self.slow_ma}',
            f'sma_{self.trend_ma}',
            f'rsi_{self.rsi_period}',
            f'bollinger_{self.bb_period}_{int(self.bb_std)}',
            f'relative_volume_{self.volume_period}',
            f'atr_14'
        ]
    
    def _check_market_regime(self, spy_data):
        """
        Check if market is in bull regime (SPY above 200 MA)
        
        Args:
            spy_data: SPY historical data
            
        Returns:
            bool: True if bullish market
        """
        if spy_data is None or len(spy_data) < self.spy_ma:
            return True  # Neutral if no data
        
        try:
            spy_price = spy_data['close'].iloc[-1]
            spy_ma_200 = spy_data['close'].rolling(self.spy_ma).mean().iloc[-1]
            
            return spy_price > spy_ma_200
            
        except:
            return True
    
    def generate_signal(self, symbol, data, spy_data, bar_index):
        """
        Generate signal using multiple indicators
        
        All indicators are pre-computed - just read and combine!
        
        Args:
            symbol: Stock symbol
            data: Historical stock data with pre-computed indicators
            spy_data: Historical SPY data
            bar_index: Current bar index
            
        Returns:
            'BUY', 'SELL', or 'HOLD'
        """
        # Need minimum data
        if len(data) < max(self.slow_ma, self.trend_ma) + 1:
            return 'HOLD'
        
        # ===================================
        # ACCESS PRE-COMPUTED INDICATORS
        # ===================================
        try:
            # Current bar
            price = data['close'].iloc[-1]
            
            # Moving averages
            fast_ma = data[f'sma_{self.fast_ma}'].iloc[-1]
            slow_ma = data[f'sma_{self.slow_ma}'].iloc[-1]
            trend_ma = data[f'sma_{self.trend_ma}'].iloc[-1]
            
            # Previous MAs for crossover
            fast_ma_prev = data[f'sma_{self.fast_ma}'].iloc[-2]
            slow_ma_prev = data[f'sma_{self.slow_ma}'].iloc[-2]
            
            # RSI
            rsi = data[f'rsi_{self.rsi_period}'].iloc[-1]
            
            # Bollinger Bands
            bb_col = f'bollinger_{self.bb_period}_{int(self.bb_std)}'
            bb_upper = data[f'{bb_col}_upper'].iloc[-1]
            bb_middle = data[f'{bb_col}_middle'].iloc[-1]
            bb_lower = data[f'{bb_col}_lower'].iloc[-1]
            
            # Volume
            rel_volume = data[f'relative_volume_{self.volume_period}'].iloc[-1]
            
            # Volatility
            atr = data['atr_14'].iloc[-1]
            
            # Check for NaN
            if pd.isna(fast_ma) or pd.isna(slow_ma) or pd.isna(trend_ma):
                return 'HOLD'
            if pd.isna(rsi) or pd.isna(bb_lower) or pd.isna(rel_volume):
                return 'HOLD'
            
        except (KeyError, IndexError):
            return 'HOLD'
        
        # ===================================
        # MARKET REGIME FILTER
        # ===================================
        bull_market = self._check_market_regime(spy_data)
        
        # ===================================
        # SIGNAL COMPONENTS
        # ===================================
        
        # Trend: Above 200 MA
        uptrend = price > trend_ma
        downtrend = price < trend_ma
        
        # Momentum: Golden/Death Cross
        golden_cross = (fast_ma_prev <= slow_ma_prev and fast_ma > slow_ma)
        death_cross = (fast_ma_prev >= slow_ma_prev and fast_ma < slow_ma)
        
        # RSI conditions
        rsi_not_overbought = rsi < self.rsi_overbought
        rsi_oversold_bounce = rsi < self.rsi_oversold
        rsi_not_oversold = rsi > self.rsi_oversold
        rsi_overbought_reject = rsi > self.rsi_overbought
        
        # Bollinger Bands
        bb_lower_touch = price < bb_lower * 1.02  # Within 2% of lower band
        bb_upper_touch = price > bb_upper * 0.98  # Within 2% of upper band
        
        # Volume confirmation
        volume_confirmed = rel_volume > self.min_relative_volume
        
        # ===================================
        # BUY SIGNAL (Multiple confirmations)
        # ===================================
        buy_signals = 0
        buy_reasons = []
        
        if uptrend:
            buy_signals += 1
            buy_reasons.append("uptrend")
        
        if golden_cross:
            buy_signals += 2  # Strong signal
            buy_reasons.append("golden_cross")
        
        if rsi_oversold_bounce:
            buy_signals += 1
            buy_reasons.append("rsi_oversold")
        
        if bb_lower_touch:
            buy_signals += 1
            buy_reasons.append("bb_lower")
        
        if volume_confirmed:
            buy_signals += 1
            buy_reasons.append("volume")
        
        if bull_market:
            buy_signals += 1
            buy_reasons.append("bull_market")
        
        # Need at least 3 signals to buy
        if buy_signals >= 3 and rsi_not_overbought:
            return 'BUY'
        
        # ===================================
        # SELL SIGNAL (Multiple confirmations)
        # ===================================
        sell_signals = 0
        sell_reasons = []
        
        if downtrend:
            sell_signals += 1
            sell_reasons.append("downtrend")
        
        if death_cross:
            sell_signals += 2  # Strong signal
            sell_reasons.append("death_cross")
        
        if rsi_overbought_reject:
            sell_signals += 1
            sell_reasons.append("rsi_overbought")
        
        if bb_upper_touch:
            sell_signals += 1
            sell_reasons.append("bb_upper")
        
        if volume_confirmed:
            sell_signals += 1
            sell_reasons.append("volume")
        
        if not bull_market:
            sell_signals += 1
            sell_reasons.append("bear_market")
        
        # Need at least 3 signals to sell
        if sell_signals >= 3 and rsi_not_oversold:
            return 'SELL'
        
        return 'HOLD'
    
    def get_config(self):
        """Return serializable configuration"""
        base_config = super().get_config()
        base_config.update({
            'fast_ma': self.fast_ma,
            'slow_ma': self.slow_ma,
            'trend_ma': self.trend_ma,
            'rsi_period': self.rsi_period,
            'rsi_oversold': self.rsi_oversold,
            'rsi_overbought': self.rsi_overbought,
            'bb_period': self.bb_period,
            'bb_std': self.bb_std,
            'volume_period': self.volume_period,
            'min_relative_volume': self.min_relative_volume,
            'spy_ma': self.spy_ma
        })
        return base_config