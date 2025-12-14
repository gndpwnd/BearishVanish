"""
Vectorized Strategy Base Class
Optimized for performance while maintaining bar-by-bar simulation
Strategies can use pre-computed indicators for massive speedup
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any, Union
from dataclasses import dataclass
import warnings
import time

# Type definitions
FloatArray = np.ndarray

@dataclass
class StrategyConfig:
    """Configuration for strategies"""
    name: str = "Strategy"
    initial_capital: float = 100000.0
    position_size_pct: float = 0.10
    max_positions: int = 10
    color: str = "#1f77b4"
    
    # Optimization settings
    use_numba: bool = True
    precompute_indicators: bool = True
    cache_signals: bool = True
    
    # Risk management
    stop_loss_pct: Optional[float] = None
    take_profit_pct: Optional[float] = None
    trailing_stop_pct: Optional[float] = None
    
    # Position management
    allow_partial_sells: bool = True
    allow_shorting: bool = False
    max_leverage: float = 1.0

@dataclass
class StrategyPerformance:
    """Performance metrics for strategy"""
    total_return_pct: float
    total_profit_dollars: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate_pct: float
    profit_factor: float
    sharpe_ratio: float
    max_drawdown_pct: float
    avg_trade_duration_days: float
    expectancy_dollars: float
    
    # Additional metrics
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0
    ulcer_index: float = 0.0
    recovery_factor: float = 0.0


class StrategyBase:
    """
    Base class for all trading strategies
    Optimized for performance while maintaining modularity
    """
    
    def __init__(self, config: StrategyConfig = None):
        """Initialize strategy with configuration"""
        self.config = config or StrategyConfig()
        self.name = self.config.name
        self.color = self.config.color
        self.initial_capital = self.config.initial_capital
        self.position_size_pct = self.config.position_size_pct
        self.max_positions = self.config.max_positions
        
        # Performance tracking
        self.calculation_time_ms = 0.0
        self.indicators_used = []
        self.last_signal = None
        
        # Indicator library reference
        self.indicator_library = None
        
        # Cache for indicators and signals
        self._indicator_cache = {}
        self._signal_cache = {}
        
        # Strategy state
        self.required_indicators = self._get_required_indicators()
        
        print(f"✅ Strategy initialized: {self.name}")
        print(f"   Required indicators: {len(self.required_indicators)}")
    
    def _get_required_indicators(self) -> List[str]:
        """
        Get list of indicators required by this strategy
        Override in subclasses to specify required indicators
        """
        return ['sma_20', 'sma_50', 'rsi_14']  # Default indicators
    
    def set_indicator_library(self, library):
        """Set indicator library for indicator calculations"""
        self.indicator_library = library
    
    def precompute_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Pre-compute all indicators needed by the strategy
        This is called once per symbol before simulation
        """
        if self.indicator_library is None:
            return data
        
        if not self.required_indicators:
            return data
        
        # Create indicator configuration
        indicators_config = {}
        for indicator_spec in self.required_indicators:
            # Parse indicator name and parameters
            if '_' in indicator_spec:
                # Format: indicator_period (e.g., sma_20)
                parts = indicator_spec.split('_')
                indicator_name = parts[0]
                params = {'period': int(parts[1])}
                
                # Handle special cases
                if indicator_name == 'bollinger':
                    params['std_dev'] = 2.0
                    indicator_name = 'bollinger_bands'
                elif indicator_name == 'macd':
                    # Default MACD parameters
                    params = {'fast_period': 12, 'slow_period': 26, 'signal_period': 9}
                elif indicator_name == 'stochastic':
                    params = {'period': 14, 'smooth_k': 3, 'smooth_d': 3}
            else:
                indicator_name = indicator_spec
                params = {}
            
            indicators_config[indicator_name] = params
        
        # Pre-compute indicators
        try:
            from indicator_base import create_indicator_dataframe
            enriched_data = create_indicator_dataframe(data, indicators_config)
            return enriched_data
        except ImportError:
            # Fallback to individual calculations
            return self._precompute_indicators_fallback(data, indicators_config)
    
    def _precompute_indicators_fallback(self, data: pd.DataFrame, indicators_config: Dict) -> pd.DataFrame:
        """Fallback method for indicator pre-computation"""
        result_df = data.copy()
        
        for indicator_name, params in indicators_config.items():
            if self.indicator_library and indicator_name in self.indicator_library._functions:
                try:
                    indicator_func = self.indicator_library._functions[indicator_name]
                    result = indicator_func(data, **params)
                    
                    if isinstance(result, tuple):
                        # Multiple outputs
                        for i, arr in enumerate(result):
                            suffix = ['', '_signal', '_hist'][i] if indicator_name == 'macd' else ['_upper', '_middle', '_lower'][i]
                            col_name = f"{indicator_name}{suffix}"
                            result_df[col_name] = arr
                    else:
                        result_df[indicator_name] = result
                except Exception as e:
                    print(f"⚠️  Error computing {indicator_name}: {e}")
        
        return result_df
    
    def generate_signal(self, 
                       symbol: str,
                       data: pd.DataFrame,
                       spy_data: pd.DataFrame,
                       bar_index: int) -> str:
        """
        Generate trading signal for current bar
        
        Args:
            symbol: Stock symbol
            data: Historical data up to current bar (includes pre-computed indicators)
            spy_data: SPY historical data
            bar_index: Current bar index (0-based)
            
        Returns:
            'BUY', 'SELL', or 'HOLD'
        
        Note: This method MUST be implemented by subclasses
        """
        raise NotImplementedError(
            f"Strategy {self.name} must implement generate_signal()"
        )
    
    def simulate_strategy(self,
                         symbol: str,
                         data: pd.DataFrame,
                         spy_data: pd.DataFrame,
                         tracker) -> Dict[str, Any]:
        """
        Simulate strategy on a single symbol
        This runs bar-by-bar to prevent look-ahead bias
        
        Args:
            symbol: Stock symbol
            data: Complete historical data with pre-computed indicators
            spy_data: SPY data
            tracker: StrategyTracker instance
            
        Returns:
            Dict with simulation results
        """
        start_time = time.time()
        
        # Pre-compute indicators if needed
        if self.config.precompute_indicators:
            enriched_data = self.precompute_indicators(data)
        else:
            enriched_data = data
        
        # Bar-by-bar simulation (prevents look-ahead bias)
        signals_generated = 0
        buy_signals = 0
        sell_signals = 0
        
        for i in range(len(enriched_data)):
            current_date = enriched_data.index[i]
            current_price = enriched_data['close'].iloc[i]
            
            # Get historical data up to current bar
            historical_data = enriched_data.iloc[:i+1]
            historical_spy = spy_data.iloc[:i+1] if spy_data is not None else None
            
            # Generate signal
            signal = self.generate_signal(symbol, historical_data, historical_spy, i)
            
            # Record signal for telemetry
            signals_generated += 1
            if signal == 'BUY':
                buy_signals += 1
            elif signal == 'SELL':
                sell_signals += 1
            
            # Execute trade if we have a tracker
            if tracker is not None and signal in ['BUY', 'SELL']:
                volume = enriched_data['volume'].iloc[i] if 'volume' in enriched_data.columns else 0
                
                # Get volume metrics
                volume_data = {}
                if 'relative_volume' in enriched_data.columns:
                    volume_data['volume'] = volume
                    volume_data['avg_volume_20d'] = enriched_data['volume'].iloc[max(0, i-19):i+1].mean()
                    volume_data['relative_volume'] = enriched_data['relative_volume'].iloc[i]
                
                tracker.execute_trade(
                    symbol, signal, current_price, current_date,
                    volume=volume_data.get('volume')
                )
            
            # Update portfolio value
            if tracker is not None:
                current_prices = {symbol: current_price}
                tracker.update_portfolio_value(current_date, current_prices)
        
        # Calculate performance
        self.calculation_time_ms = (time.time() - start_time) * 1000
        
        result = {
            'strategy': self.name,
            'symbol': symbol,
            'signals_generated': signals_generated,
            'buy_signals': buy_signals,
            'sell_signals': sell_signals,
            'calculation_time_ms': self.calculation_time_ms,
            'bars_processed': len(enriched_data)
        }
        
        return result
    
    def calculate_performance_metrics(self, tracker, spy_returns=None) -> StrategyPerformance:
        """
        Calculate comprehensive performance metrics
        """
        from strategy_tracker import StrategyTracker
        
        if not isinstance(tracker, StrategyTracker):
            return StrategyPerformance(
                total_return_pct=0.0,
                total_profit_dollars=0.0,
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                win_rate_pct=0.0,
                profit_factor=0.0,
                sharpe_ratio=0.0,
                max_drawdown_pct=0.0,
                avg_trade_duration_days=0.0,
                expectancy_dollars=0.0
            )
        
        # Basic metrics
        total_return = tracker.get_return_pct()
        total_profit = tracker.get_profit_dollars()
        total_trades = tracker.get_num_trades()
        
        # Win rate
        winning = tracker.get_winning_trades()
        losing = tracker.get_losing_trades()
        winning_trades = len(winning)
        losing_trades = len(losing)
        win_rate = (winning_trades / (winning_trades + losing_trades) * 100) if (winning_trades + losing_trades) > 0 else 0
        
        # Profit factor
        gross_profit = sum(trade['profit'] for trade in winning) if winning else 0
        gross_loss = abs(sum(trade['loss'] for trade in losing)) if losing else 0
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
        
        # Other metrics
        sharpe = tracker.get_sharpe_ratio()
        max_dd = tracker.get_max_drawdown()
        avg_duration = tracker.get_avg_trade_duration()
        expectancy = tracker.get_expectancy()
        
        # Additional metrics
        sortino = tracker.get_sortino_ratio()
        calmar = tracker.get_calmar_ratio()
        ulcer = tracker.get_ulcer_index()
        recovery = tracker.get_recovery_factor()
        
        return StrategyPerformance(
            total_return_pct=total_return,
            total_profit_dollars=total_profit,
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate_pct=win_rate,
            profit_factor=profit_factor,
            sharpe_ratio=sharpe,
            max_drawdown_pct=max_dd,
            avg_trade_duration_days=avg_duration,
            expectancy_dollars=expectancy,
            sortino_ratio=sortino,
            calmar_ratio=calmar,
            ulcer_index=ulcer,
            recovery_factor=recovery
        )
    
    def get_config(self) -> Dict[str, Any]:
        """Get strategy configuration for telemetry"""
        return {
            'name': self.name,
            'color': self.color,
            'initial_capital': self.initial_capital,
            'position_size_pct': self.position_size_pct,
            'max_positions': self.max_positions,
            'use_numba': self.config.use_numba,
            'precompute_indicators': self.config.precompute_indicators,
            'cache_signals': self.config.cache_signals,
            'stop_loss_pct': self.config.stop_loss_pct,
            'take_profit_pct': self.config.take_profit_pct,
            'trailing_stop_pct': self.config.trailing_stop_pct,
            'required_indicators': self.required_indicators
        }
    
    def print_performance_summary(self, performance: StrategyPerformance):
        """Print strategy performance summary"""
        print(f"\n{'='*70}")
        print(f"STRATEGY PERFORMANCE: {self.name}")
        print(f"{'='*70}")
        print(f"📊 Returns:")
        print(f"   Total Return: {performance.total_return_pct:+.2f}%")
        print(f"   Total Profit: ${performance.total_profit_dollars:+,.2f}")
        
        print(f"\n📈 Trade Statistics:")
        print(f"   Total Trades: {performance.total_trades}")
        print(f"   Win Rate: {performance.win_rate_pct:.1f}%")
        print(f"   Winning Trades: {performance.winning_trades}")
        print(f"   Losing Trades: {performance.losing_trades}")
        print(f"   Profit Factor: {performance.profit_factor:.2f}")
        
        print(f"\n⚠️  Risk Metrics:")
        print(f"   Sharpe Ratio: {performance.sharpe_ratio:.2f}")
        print(f"   Max Drawdown: {performance.max_drawdown_pct:.1f}%")
        print(f"   Sortino Ratio: {performance.sortino_ratio:.2f}")
        
        print(f"\n⚡ Performance:")
        print(f"   Avg Trade Duration: {performance.avg_trade_duration_days:.1f} days")
        print(f"   Expectancy: ${performance.expectancy_dollars:.2f}")
        print(f"   Calculation Time: {self.calculation_time_ms:.1f}ms")
        print(f"{'='*70}\n")