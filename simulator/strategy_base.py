"""
Vectorized Strategy Base Class
All strategies process entire time series at once using NumPy operations
Expected performance: 5-20x faster than bar-by-bar strategies
"""

import numpy as np
import pandas as pd
from numba import jit, prange
from typing import Dict, List, Tuple, Optional, Union, Any
from dataclasses import dataclass
import warnings
import time

# Type definitions
FloatArray = np.ndarray
BoolArray = np.ndarray
IntArray = np.ndarray
SignalArray = np.ndarray  # -1 = SELL, 0 = HOLD, 1 = BUY


@dataclass
class StrategyConfig:
    """Configuration for vectorized strategies"""
    name: str = "VectorizedStrategy"
    initial_capital: float = 100000.0
    position_size_pct: float = 0.10  # 10% per position
    max_positions: int = 10
    commission_rate: float = 0.0  # Percentage per trade
    slippage_pct: float = 0.0  # Percentage slippage
    min_position_size: float = 100.0  # Minimum $ position
    color: str = "#1f77b4"  # For visualization
    
    # Risk management
    stop_loss_pct: Optional[float] = None
    take_profit_pct: Optional[float] = None
    trailing_stop_pct: Optional[float] = None
    
    # Position management
    allow_partial_sells: bool = True
    allow_shorting: bool = False
    max_leverage: float = 1.0  # 1.0 = no leverage
    
    # Optimization flags
    use_numba: bool = True
    precompute_indicators: bool = True
    cache_signals: bool = True


@dataclass
class StrategyResult:
    """Results from strategy simulation"""
    signals: SignalArray  # Buy/Sell/Hold signals
    positions: FloatArray  # Shares held at each timestep
    entry_prices: FloatArray  # Entry prices for positions
    exit_prices: FloatArray  # Exit prices for positions
    portfolio_values: FloatArray  # Total portfolio value
    cash_history: FloatArray  # Cash balance over time
    trades: List[Dict]  # List of trade dictionaries
    metrics: Dict[str, float]  # Performance metrics
    
    # Timing information
    calculation_time_ms: float
    indicators_used: List[str]


class VectorizedStrategyBase:
    """
    Base class for all vectorized trading strategies
    All strategies MUST implement generate_signals_vectorized()
    """
    
    def __init__(self, config: StrategyConfig = None):
        """Initialize strategy with configuration"""
        self.config = config or StrategyConfig()
        self.name = self.config.name
        
        # Performance tracking
        self.calculation_time = 0.0
        self.indicators_calculated = 0
        self.cache = {}
        
        # Results storage
        self.last_result: Optional[StrategyResult] = None
        
        # Initialize with default indicator library
        self.indicator_library = None
        
        # Signal cache
        self._signal_cache = {}
    
    def set_indicator_library(self, library):
        """Set indicator library for indicator calculations"""
        self.indicator_library = library
    
    def generate_signals_vectorized(self, 
                                   stock_data: pd.DataFrame,
                                   spy_data: pd.DataFrame,
                                   symbol: str) -> SignalArray:
        """
        MAIN METHOD: Generate trading signals for entire time series
        
        Args:
            stock_data: DataFrame with OHLCV + indicators
            spy_data: DataFrame with SPY data + indicators
            symbol: Stock symbol
            
        Returns:
            SignalArray: -1=SELL, 0=HOLD, 1=BUY for each timestamp
            
        Note: This method MUST be implemented by subclasses
        """
        raise NotImplementedError(
            f"Strategy {self.name} must implement generate_signals_vectorized()"
        )
    
    def simulate_vectorized(self,
                           stock_data: pd.DataFrame,
                           spy_data: pd.DataFrame,
                           symbol: str,
                           initial_cash: Optional[float] = None) -> StrategyResult:
        """
        Complete vectorized simulation: signals + portfolio simulation
        
        Args:
            stock_data: DataFrame with OHLCV data
            spy_data: SPY benchmark data
            symbol: Stock symbol
            initial_cash: Override initial cash amount
            
        Returns:
            StrategyResult with all simulation results
        """
        start_time = time.time()
        
        # Use provided cash or config cash
        cash = initial_cash or self.config.initial_capital
        
        # Pre-compute indicators if needed
        if self.config.precompute_indicators and self.indicator_library:
            stock_data = self._precompute_indicators(stock_data)
        
        # Generate signals (vectorized)
        signals = self.generate_signals_vectorized(stock_data, spy_data, symbol)
        
        # Simulate portfolio with vectorized trade execution
        result = self._simulate_portfolio_vectorized(
            signals=signals,
            prices=stock_data['close'].values,
            volumes=stock_data['volume'].values if 'volume' in stock_data.columns else None,
            initial_cash=cash,
            symbol=symbol
        )
        
        # Calculate performance metrics
        metrics = self._calculate_metrics(result, spy_data)
        
        # Store timing
        self.calculation_time = (time.time() - start_time) * 1000
        
        # Create result object
        strategy_result = StrategyResult(
            signals=signals,
            positions=result['positions'],
            entry_prices=result['entry_prices'],
            exit_prices=result['exit_prices'],
            portfolio_values=result['portfolio_values'],
            cash_history=result['cash_history'],
            trades=result['trades'],
            metrics=metrics,
            calculation_time_ms=self.calculation_time,
            indicators_used=self._get_indicators_used()
        )
        
        self.last_result = strategy_result
        return strategy_result
    
    def _precompute_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """Pre-compute all indicators needed by the strategy"""
        if self.indicator_library is None:
            return data
        
        # Get list of indicators this strategy uses
        required_indicators = self._get_required_indicators()
        
        if not required_indicators:
            return data
        
        # Calculate indicators in batch
        results = self.indicator_library.calculate_all(data, required_indicators)
        
        # Add indicator columns to dataframe
        data = data.copy()
        for indicator_name, indicator_result in results.items():
            col_name = f"{indicator_name}"
            data[col_name] = indicator_result.values
        
        self.indicators_calculated = len(results)
        return data
    
    def _get_required_indicators(self) -> List[str]:
        """
        Get list of indicators required by this strategy
        Override in subclasses to specify required indicators
        """
        return ['sma_20', 'sma_50', 'rsi']  # Default indicators
    
    def _get_indicators_used(self) -> List[str]:
        """Get list of indicators actually used"""
        return self._get_required_indicators()
    
    @staticmethod
    @jit(nopython=True, cache=True, parallel=False)
    def _simulate_portfolio_vectorized_numba(signals: SignalArray,
                                            prices: FloatArray,
                                            initial_cash: float,
                                            position_size_pct: float,
                                            max_positions: int,
                                            min_position_size: float,
                                            commission_rate: float,
                                            allow_partial_sells: bool) -> Dict[str, Any]:
        """
        Numba-optimized portfolio simulation
        Processes entire time series at once
        """
        n = len(signals)
        
        # Initialize arrays
        positions = np.zeros(n, dtype=np.float32)  # Shares held
        entry_prices = np.zeros(n, dtype=np.float32)  # Entry price for current position
        exit_prices = np.zeros(n, dtype=np.float32)  # Exit price for last position
        portfolio_values = np.zeros(n, dtype=np.float32)
        cash_history = np.zeros(n, dtype=np.float32)
        
        # Track trades
        trades = []
        trade_id = 0
        
        # Current state
        cash = initial_cash
        in_position = False
        current_entry_price = 0.0
        
        for i in range(n):
            price = prices[i]
            signal = signals[i]
            
            # Calculate portfolio value
            position_value = positions[i-1] * price if i > 0 else 0
            portfolio_value = cash + position_value
            
            # Handle signals
            if signal == 1 and not in_position and cash >= min_position_size:
                # BUY signal
                portfolio_value_before = cash  # No position yet
                allocation = portfolio_value_before * position_size_pct
                allocation = min(allocation, cash)
                
                if allocation >= min_position_size:
                    # Calculate shares and commission
                    shares = allocation / price
                    commission = shares * price * commission_rate
                    
                    # Execute buy
                    cost = (shares * price) + commission
                    if cost <= cash:
                        positions[i] = shares
                        entry_prices[i] = price
                        current_entry_price = price
                        cash -= cost
                        in_position = True
                        
                        # Record trade
                        trades.append({
                            'id': trade_id,
                            'type': 'BUY',
                            'timestamp': i,
                            'price': price,
                            'shares': shares,
                            'cost': cost,
                            'commission': commission
                        })
                        trade_id += 1
            
            elif signal == -1 and in_position:
                # SELL signal
                current_shares = positions[i-1] if i > 0 else positions[i]
                
                if current_shares > 0:
                    # Calculate proceeds and commission
                    proceeds = current_shares * price
                    commission = proceeds * commission_rate
                    
                    # Execute sell
                    net_proceeds = proceeds - commission
                    cash += net_proceeds
                    positions[i] = 0
                    exit_prices[i] = price
                    in_position = False
                    
                    # Record trade
                    trades.append({
                        'id': trade_id,
                        'type': 'SELL',
                        'timestamp': i,
                        'price': price,
                        'shares': current_shares,
                        'proceeds': proceeds,
                        'commission': commission,
                        'net_proceeds': net_proceeds
                    })
                    trade_id += 1
            
            # Carry position forward if no action
            if signal == 0 and in_position and i > 0:
                positions[i] = positions[i-1]
                entry_prices[i] = entry_prices[i-1]
            
            # Update tracking arrays
            portfolio_values[i] = cash + (positions[i] * price)
            cash_history[i] = cash
        
        return {
            'positions': positions,
            'entry_prices': entry_prices,
            'exit_prices': exit_prices,
            'portfolio_values': portfolio_values,
            'cash_history': cash_history,
            'trades': trades
        }
    
    def _simulate_portfolio_vectorized(self,
                                      signals: SignalArray,
                                      prices: FloatArray,
                                      volumes: Optional[FloatArray],
                                      initial_cash: float,
                                      symbol: str) -> Dict[str, Any]:
        """
        Vectorized portfolio simulation with full feature set
        """
        if self.config.use_numba:
            # Use Numba-optimized version
            result = self._simulate_portfolio_vectorized_numba(
                signals=signals,
                prices=prices,
                initial_cash=initial_cash,
                position_size_pct=self.config.position_size_pct,
                max_positions=self.config.max_positions,
                min_position_size=self.config.min_position_size,
                commission_rate=self.config.commission_rate,
                allow_partial_sells=self.config.allow_partial_sells
            )
        else:
            # Pure Python version (slower but more debuggable)
            result = self._simulate_portfolio_python(
                signals, prices, volumes, initial_cash, symbol
            )
        
        return result
    
    def _simulate_portfolio_python(self,
                                  signals: SignalArray,
                                  prices: FloatArray,
                                  volumes: Optional[FloatArray],
                                  initial_cash: float,
                                  symbol: str) -> Dict[str, Any]:
        """
        Pure Python portfolio simulation (for debugging)
        """
        n = len(signals)
        
        # Initialize arrays
        positions = np.zeros(n, dtype=np.float32)
        entry_prices = np.zeros(n, dtype=np.float32)
        exit_prices = np.zeros(n, dtype=np.float32)
        portfolio_values = np.zeros(n, dtype=np.float32)
        cash_history = np.zeros(n, dtype=np.float32)
        
        cash = initial_cash
        current_position = 0.0
        current_entry_price = 0.0
        
        trades = []
        
        for i in range(n):
            price = prices[i]
            
            # Update portfolio value
            portfolio_value = cash + (current_position * price)
            
            # Process signal
            signal = signals[i]
            
            if signal == 1 and current_position == 0:
                # BUY signal
                allocation = portfolio_value * self.config.position_size_pct
                allocation = min(allocation, cash)
                
                if allocation >= self.config.min_position_size:
                    shares = allocation / price
                    commission = shares * price * self.config.commission_rate
                    
                    if (shares * price) + commission <= cash:
                        current_position = shares
                        current_entry_price = price
                        cash -= (shares * price) + commission
                        
                        trades.append({
                            'timestamp': i,
                            'action': 'BUY',
                            'symbol': symbol,
                            'price': price,
                            'shares': shares,
                            'commission': commission
                        })
            
            elif signal == -1 and current_position > 0:
                # SELL signal
                proceeds = current_position * price
                commission = proceeds * self.config.commission_rate
                cash += proceeds - commission
                
                trades.append({
                    'timestamp': i,
                    'action': 'SELL',
                    'symbol': symbol,
                    'price': price,
                    'shares': current_position,
                    'proceeds': proceeds,
                    'commission': commission,
                    'profit': (price - current_entry_price) * current_position
                })
                
                current_position = 0
                current_entry_price = 0.0
            
            # Update arrays
            positions[i] = current_position
            entry_prices[i] = current_entry_price if current_position > 0 else 0.0
            exit_prices[i] = price if signal == -1 and current_position == 0 else 0.0
            portfolio_values[i] = cash + (current_position * price)
            cash_history[i] = cash
        
        return {
            'positions': positions,
            'entry_prices': entry_prices,
            'exit_prices': exit_prices,
            'portfolio_values': portfolio_values,
            'cash_history': cash_history,
            'trades': trades
        }
    
    def _calculate_metrics(self, result: Dict, spy_data: pd.DataFrame) -> Dict[str, float]:
        """Calculate performance metrics from simulation results"""
        portfolio_values = result['portfolio_values']
        
        if len(portfolio_values) < 2:
            return {}
        
        # Basic metrics
        initial_value = portfolio_values[0] if portfolio_values[0] > 0 else portfolio_values[1]
        final_value = portfolio_values[-1]
        total_return = (final_value - initial_value) / initial_value * 100
        
        # Calculate returns
        returns = np.diff(portfolio_values) / portfolio_values[:-1]
        
        # Sharpe Ratio (assuming 0% risk-free rate)
        sharpe = 0.0
        if len(returns) > 1 and returns.std() > 0:
            sharpe = (returns.mean() / returns.std()) * np.sqrt(252)
        
        # Maximum Drawdown
        peak = np.maximum.accumulate(portfolio_values)
        drawdown = (peak - portfolio_values) / peak * 100
        max_drawdown = np.max(drawdown) if len(drawdown) > 0 else 0
        
        # Win rate
        trades = result['trades']
        winning_trades = 0
        total_trades = len(trades) // 2  # Assuming buy-sell pairs
        
        for i in range(0, len(trades) - 1, 2):
            if i + 1 < len(trades):
                buy = trades[i]
                sell = trades[i + 1]
                if sell.get('price', 0) > buy.get('price', 0):
                    winning_trades += 1
        
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        
        # Average trade metrics
        trade_returns = []
        for i in range(0, len(trades) - 1, 2):
            if i + 1 < len(trades):
                buy_price = trades[i].get('price', 0)
                sell_price = trades[i + 1].get('price', 0)
                if buy_price > 0:
                    trade_return = (sell_price - buy_price) / buy_price * 100
                    trade_returns.append(trade_return)
        
        avg_trade_return = np.mean(trade_returns) if trade_returns else 0
        
        metrics = {
            'total_return_pct': total_return,
            'sharpe_ratio': sharpe,
            'max_drawdown_pct': max_drawdown,
            'win_rate_pct': win_rate,
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': total_trades - winning_trades,
            'avg_trade_return_pct': avg_trade_return,
            'final_portfolio_value': final_value,
            'initial_portfolio_value': initial_value,
            'profit_loss': final_value - initial_value,
            'volatility_pct': returns.std() * np.sqrt(252) * 100 if len(returns) > 0 else 0,
            'calmar_ratio': total_return / max_drawdown if max_drawdown > 0 else 0,
            'sortino_ratio': self._calculate_sortino(returns),
            'profit_factor': self._calculate_profit_factor(trades),
            'expectancy': self._calculate_expectancy(trades),
        }
        
        return metrics
    
    @staticmethod
    def _calculate_sortino(returns: FloatArray, risk_free: float = 0.0) -> float:
        """Calculate Sortino ratio"""
        if len(returns) == 0:
            return 0.0
        
        excess_returns = returns - risk_free
        downside_returns = excess_returns[excess_returns < 0]
        
        if len(downside_returns) == 0 or downside_returns.std() == 0:
            return 0.0
        
        return excess_returns.mean() / downside_returns.std() * np.sqrt(252)
    
    @staticmethod
    def _calculate_profit_factor(trades: List[Dict]) -> float:
        """Calculate profit factor (gross profit / gross loss)"""
        gross_profit = 0.0
        gross_loss = 0.0
        
        for i in range(0, len(trades) - 1, 2):
            if i + 1 < len(trades):
                buy = trades[i]
                sell = trades[i + 1]
                profit = sell.get('proceeds', 0) - buy.get('cost', 0)
                
                if profit > 0:
                    gross_profit += profit
                else:
                    gross_loss += abs(profit)
        
        if gross_loss == 0:
            return float('inf') if gross_profit > 0 else 0.0
        
        return gross_profit / gross_loss
    
    @staticmethod
    def _calculate_expectancy(trades: List[Dict]) -> float:
        """Calculate expectancy per trade"""
        if len(trades) < 2:
            return 0.0
        
        profits = []
        for i in range(0, len(trades) - 1, 2):
            if i + 1 < len(trades):
                buy = trades[i]
                sell = trades[i + 1]
                profit = sell.get('proceeds', 0) - buy.get('cost', 0)
                profits.append(profit)
        
        if not profits:
            return 0.0
        
        return np.mean(profits)
    
    def get_config(self) -> Dict[str, Any]:
        """Get strategy configuration for telemetry"""
        return {
            'name': self.config.name,
            'initial_capital': self.config.initial_capital,
            'position_size_pct': self.config.position_size_pct,
            'max_positions': self.config.max_positions,
            'commission_rate': self.config.commission_rate,
            'slippage_pct': self.config.slippage_pct,
            'min_position_size': self.config.min_position_size,
            'stop_loss_pct': self.config.stop_loss_pct,
            'take_profit_pct': self.config.take_profit_pct,
            'trailing_stop_pct': self.config.trailing_stop_pct,
            'allow_shorting': self.config.allow_shorting,
            'max_leverage': self.config.max_leverage,
            'use_numba': self.config.use_numba,
            'precompute_indicators': self.config.precompute_indicators,
            'cache_signals': self.config.cache_signals,
        }
    
    def print_performance(self):
        """Print strategy performance summary"""
        if self.last_result is None:
            print(f"❌ {self.name}: No simulation results available")
            return
        
        metrics = self.last_result.metrics
        
        print(f"\n{'='*70}")
        print(f"STRATEGY PERFORMANCE: {self.name}")
        print(f"{'='*70}")
        print(f"📊 Returns:")
        print(f"   Total Return: {metrics.get('total_return_pct', 0):+.2f}%")
        print(f"   Final Value: ${metrics.get('final_portfolio_value', 0):,.2f}")
        print(f"   Profit/Loss: ${metrics.get('profit_loss', 0):+,.2f}")
        
        print(f"\n📈 Risk Metrics:")
        print(f"   Sharpe Ratio: {metrics.get('sharpe_ratio', 0):.2f}")
        print(f"   Sortino Ratio: {metrics.get('sortino_ratio', 0):.2f}")
        print(f"   Max Drawdown: {metrics.get('max_drawdown_pct', 0):.1f}%")
        print(f"   Volatility: {metrics.get('volatility_pct', 0):.1f}%")
        
        print(f"\n🎯 Trade Statistics:")
        print(f"   Total Trades: {metrics.get('total_trades', 0)}")
        print(f"   Win Rate: {metrics.get('win_rate_pct', 0):.1f}%")
        print(f"   Profit Factor: {metrics.get('profit_factor', 0):.2f}")
        print(f"   Expectancy: ${metrics.get('expectancy', 0):.2f}")
        
        print(f"\n⚡ Performance:")
        print(f"   Calculation Time: {self.calculation_time:.1f}ms")
        print(f"   Indicators Used: {self.indicators_calculated}")
        print(f"   Bars Processed: {len(self.last_result.signals):,}")
        print(f"   Speed: {len(self.last_result.signals)/self.calculation_time*1000:,.0f} bars/sec")
        print(f"{'='*70}\n")


# ============================================================
# EXAMPLE VECTORIZED STRATEGIES
# ============================================================

class VectorizedMomentumStrategy(VectorizedStrategyBase):
    """
    Example: Vectorized momentum strategy using moving average crossovers
    """
    
    def __init__(self, 
                 fast_period: int = 20,
                 slow_period: int = 50,
                 rsi_period: int = 14,
                 rsi_oversold: float = 30,
                 rsi_overbought: float = 70,
                 **kwargs):
        
        # Create config
        config = StrategyConfig(
            name=f"Momentum_{fast_period}_{slow_period}",
            **kwargs
        )
        
        super().__init__(config)
        
        # Strategy parameters
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.rsi_period = rsi_period
        self.rsi_oversold = rsi_oversold
        self.rsi_overbought = rsi_overbought
    
    def _get_required_indicators(self) -> List[str]:
        """Indicators required by this strategy"""
        return [
            f'sma_{self.fast_period}',
            f'sma_{self.slow_period}',
            f'rsi_{self.rsi_period}'
        ]
    
    @staticmethod
    @jit(nopython=True, cache=True, parallel=True)
    def _generate_signals_numba(prices: FloatArray,
                                sma_fast: FloatArray,
                                sma_slow: FloatArray,
                                rsi: FloatArray,
                                rsi_oversold: float,
                                rsi_overbought: float) -> SignalArray:
        """
        Numba-optimized signal generation
        """
        n = len(prices)
        signals = np.zeros(n, dtype=np.int8)
        
        # Minimum bars needed
        min_bars = max(50, len(sma_fast) - np.count_nonzero(np.isnan(sma_fast)))
        
        for i in prange(min_bars, n):
            # Skip if indicators are NaN
            if np.isnan(sma_fast[i]) or np.isnan(sma_slow[i]) or np.isnan(rsi[i]):
                continue
            
            # Golden Cross: Fast crosses above Slow
            if (sma_fast[i] > sma_slow[i] and 
                sma_fast[i-1] <= sma_slow[i-1] and
                rsi[i] < rsi_overbought):
                signals[i] = 1  # BUY
            
            # Death Cross: Fast crosses below Slow
            elif (sma_fast[i] < sma_slow[i] and 
                  sma_fast[i-1] >= sma_slow[i-1] and
                  rsi[i] > rsi_oversold):
                signals[i] = -1  # SELL
        
        return signals
    
    def generate_signals_vectorized(self, 
                                   stock_data: pd.DataFrame,
                                   spy_data: pd.DataFrame,
                                   symbol: str) -> SignalArray:
        """
        Generate momentum signals using MA crossovers and RSI
        """
        # Extract required columns
        prices = stock_data['close'].values
        
        # Get indicator columns (they should be precomputed)
        sma_fast_col = f'sma_{self.fast_period}'
        sma_slow_col = f'sma_{self.slow_period}'
        rsi_col = f'rsi_{self.rsi_period}'
        
        if sma_fast_col not in stock_data.columns:
            # Calculate on the fly if not precomputed
            warnings.warn(f"Indicator {sma_fast_col} not found, calculating...")
            if self.indicator_library:
                indicators = self.indicator_library.calculate_all(
                    stock_data, 
                    ['sma', 'rsi']
                )
                sma_fast = indicators['sma'].values
                sma_slow = indicators['sma'].values  # Would need different period
                rsi = indicators['rsi'].values
            else:
                # Fallback to pandas (slower)
                sma_fast = stock_data['close'].rolling(self.fast_period).mean().values
                sma_slow = stock_data['close'].rolling(self.slow_period).mean().values
                rsi = self._calculate_rsi_pandas(stock_data, self.rsi_period)
        else:
            # Use precomputed indicators
            sma_fast = stock_data[sma_fast_col].values
            sma_slow = stock_data[sma_slow_col].values
            rsi = stock_data[rsi_col].values
        
        # Generate signals using Numba
        if self.config.use_numba:
            signals = self._generate_signals_numba(
                prices=prices,
                sma_fast=sma_fast,
                sma_slow=sma_slow,
                rsi=rsi,
                rsi_oversold=self.rsi_oversold,
                rsi_overbought=self.rsi_overbought
            )
        else:
            # Python fallback
            signals = self._generate_signals_python(
                prices, sma_fast, sma_slow, rsi
            )
        
        return signals
    
    def _generate_signals_python(self,
                                prices: FloatArray,
                                sma_fast: FloatArray,
                                sma_slow: FloatArray,
                                rsi: FloatArray) -> SignalArray:
        """Python implementation (for comparison)"""
        n = len(prices)
        signals = np.zeros(n, dtype=np.int8)
        
        for i in range(50, n):
            # Skip NaN values
            if (np.isnan(sma_fast[i]) or np.isnan(sma_slow[i]) or 
                np.isnan(rsi[i])):
                continue
            
            # Buy signal: Golden cross and RSI not overbought
            if (sma_fast[i] > sma_slow[i] and 
                sma_fast[i-1] <= sma_slow[i-1] and
                rsi[i] < self.rsi_overbought):
                signals[i] = 1
            
            # Sell signal: Death cross and RSI not oversold
            elif (sma_fast[i] < sma_slow[i] and 
                  sma_fast[i-1] >= sma_slow[i-1] and
                  rsi[i] > self.rsi_oversold):
                signals[i] = -1
        
        return signals
    
    @staticmethod
    def _calculate_rsi_pandas(data: pd.DataFrame, period: int = 14) -> FloatArray:
        """Calculate RSI using pandas (fallback)"""
        delta = data['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi.values


class VectorizedMeanReversionStrategy(VectorizedStrategyBase):
    """
    Example: Vectorized mean reversion strategy using Bollinger Bands
    """
    
    def __init__(self,
                 bb_period: int = 20,
                 bb_std: float = 2.0,
                 rsi_period: int = 14,
                 rsi_oversold: float = 30,
                 rsi_overbought: float = 70,
                 **kwargs):
        
        config = StrategyConfig(
            name=f"MeanReversion_BB{bb_period}",
            **kwargs
        )
        super().__init__(config)
        
        self.bb_period = bb_period
        self.bb_std = bb_std
        self.rsi_period = rsi_period
        self.rsi_oversold = rsi_oversold
        self.rsi_overbought = rsi_overbought
    
    def _get_required_indicators(self) -> List[str]:
        return [
            f'bollinger_bands_{self.bb_period}',
            f'rsi_{self.rsi_period}'
        ]
    
    def generate_signals_vectorized(self,
                                   stock_data: pd.DataFrame,
                                   spy_data: pd.DataFrame,
                                   symbol: str) -> SignalArray:
        """Generate mean reversion signals using Bollinger Bands"""
        prices = stock_data['close'].values
        
        # Get Bollinger Bands
        bb_upper_col = f'bb_upper_{self.bb_period}'
        bb_middle_col = f'bb_middle_{self.bb_period}'
        bb_lower_col = f'bb_lower_{self.bb_period}'
        rsi_col = f'rsi_{self.rsi_period}'
        
        if bb_upper_col not in stock_data.columns:
            # Calculate indicators
            if self.indicator_library:
                indicators = self.indicator_library.calculate_all(
                    stock_data,
                    ['bollinger_bands', 'rsi']
                )
                bb_upper = indicators['bollinger_bands'].values[0]  # First array
                bb_lower = indicators['bollinger_bands'].values[2]  # Third array
                rsi = indicators['rsi'].values
            else:
                # Fallback
                bb_upper, bb_middle, bb_lower = self._calculate_bollinger_pandas(
                    stock_data, self.bb_period, self.bb_std
                )
                rsi = self._calculate_rsi_pandas(stock_data, self.rsi_period)
        else:
            bb_upper = stock_data[bb_upper_col].values
            bb_lower = stock_data[bb_lower_col].values
            rsi = stock_data[rsi_col].values
        
        n = len(prices)
        signals = np.zeros(n, dtype=np.int8)
        
        # Vectorized signal generation
        buy_signal = (prices < bb_lower) & (rsi < self.rsi_oversold)
        sell_signal = (prices > bb_upper) & (rsi > self.rsi_overbought)
        
        signals[buy_signal] = 1
        signals[sell_signal] = -1
        
        return signals
    
    @staticmethod
    def _calculate_bollinger_pandas(data: pd.DataFrame, period: int, std_dev: float):
        """Calculate Bollinger Bands using pandas"""
        middle = data['close'].rolling(period).mean()
        std = data['close'].rolling(period).std()
        upper = middle + (std * std_dev)
        lower = middle - (std * std_dev)
        return upper.values, middle.values, lower.values


# Factory function for creating strategies
def create_vectorized_strategy(strategy_type: str, **kwargs) -> VectorizedStrategyBase:
    """Factory function to create vectorized strategies"""
    strategies = {
        'momentum': VectorizedMomentumStrategy,
        'mean_reversion': VectorizedMeanReversionStrategy,
    }
    
    if strategy_type not in strategies:
        raise ValueError(f"Unknown strategy type: {strategy_type}. "
                         f"Available: {list(strategies.keys())}")
    
    return strategies[strategy_type](**kwargs)