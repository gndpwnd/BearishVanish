"""
Dynamic Indicator Loader - Automatically loads indicators from ./indicators/
"""

import importlib.util
import sys
import inspect
from pathlib import Path
from typing import Dict, List, Any, Callable, Type
import networkx as nx

from indicator_base import IndicatorBase, BUILTIN_FUNCTIONS, BUILTIN_CLASSES


class IndicatorLibrary:
    """
    Main indicator manager - loads, caches, and runs indicators
    """
    
    def __init__(self, indicators_dir: str = "./indicators"):
        self.indicators_dir = Path(indicators_dir)
        self.indicators_dir.mkdir(exist_ok=True)
        
        # Registry
        self._functions: Dict[str, Callable] = {}
        self._classes: Dict[str, Type[IndicatorBase]] = {}
        self._instances: Dict[str, IndicatorBase] = {}
        
        # Dependency graph
        self._graph = nx.DiGraph()
        
        # Cache for results
        self._cache: Dict[str, Any] = {}
        
        # Load built-in indicators first
        self._load_builtin_indicators()
        
        # Load custom indicators
        self._load_custom_indicators()
        
        # Resolve dependencies
        self._resolve_dependencies()
    
    def _load_builtin_indicators(self):
        """Load built-in indicators"""
        self._functions.update(BUILTIN_FUNCTIONS)
        self._classes.update(BUILTIN_CLASSES)
        
        # Add to dependency graph
        for name in self._functions:
            self._graph.add_node(name, type='function')
        
        for name, cls in self._classes.items():
            self._graph.add_node(name, type='class')
            # Add dependencies
            if hasattr(cls, 'dependencies'):
                for dep in cls.dependencies:
                    self._graph.add_edge(name, dep)
    
    def _load_custom_indicators(self):
        """Dynamically load custom indicators from files"""
        if not self.indicators_dir.exists():
            return
        
        # Scan for indicator files
        for file_path in self.indicators_dir.glob("indicator_*.py"):
            try:
                module_name = f"indicator_{file_path.stem}"
                spec = importlib.util.spec_from_file_location(module_name, file_path)
                module = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = module
                spec.loader.exec_module(module)
                
                # Register functions
                for name, obj in module.__dict__.items():
                    if callable(obj) and not name.startswith('_'):
                        # Check if it's a function (not a class)
                        if not inspect.isclass(obj):
                            self._functions[name] = obj
                            self._graph.add_node(name, type='function')
                        # Check if it's an IndicatorBase subclass
                        elif inspect.isclass(obj) and issubclass(obj, IndicatorBase) and obj != IndicatorBase:
                            self._classes[name] = obj
                            self._graph.add_node(name, type='class')
                            # Add dependencies if declared
                            if hasattr(obj, 'dependencies'):
                                for dep in obj.dependencies:
                                    self._graph.add_edge(name, dep)
                        
            except Exception as e:
                print(f"⚠️  Error loading indicator from {file_path}: {e}")
    
    def _resolve_dependencies(self):
        """Check for circular dependencies and resolve order"""
        try:
            # Check for cycles
            cycles = list(nx.simple_cycles(self._graph))
            if cycles:
                print(f"❌ Circular dependencies detected: {cycles}")
                raise ValueError(f"Circular dependencies: {cycles}")
            
            # Get topological order for dependency resolution
            self._topological_order = list(nx.topological_sort(self._graph))
            
        except nx.NetworkXUnfeasible:
            print("❌ Circular dependencies detected in indicators")
            raise
    
    def get(self, indicator_name: str, data: pd.DataFrame, **params) -> Any:
        """
        Get indicator value with caching and dependency resolution
        """
        import pandas as pd
        
        # Create cache key
        cache_key = f"{indicator_name}_{len(data)}_{hash(frozenset(params.items()))}"
        
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        # Check if it's a function
        if indicator_name in self._functions:
            result = self._functions[indicator_name](data, **params)
            self._cache[cache_key] = result
            return result
        
        # Check if it's a class
        if indicator_name in self._classes:
            # Create or get instance
            if indicator_name not in self._instances:
                self._instances[indicator_name] = self._classes[indicator_name](**params)
            
            instance = self._instances[indicator_name]
            
            # Resolve dependencies before calculation
            if hasattr(instance, 'dependencies'):
                dependency_results = {}
                for dep_name in instance.dependencies:
                    dependency_results[dep_name] = self.get(dep_name, data)
            
            result = instance.calculate(data)
            self._cache[cache_key] = result.value if isinstance(result, IndicatorResult) else result
            return result
        
        raise ValueError(f"Indicator '{indicator_name}' not found")
    
    def list_indicators(self) -> Dict[str, List[str]]:
        """List all available indicators"""
        return {
            'functions': sorted(self._functions.keys()),
            'classes': sorted(self._classes.keys())
        }
    
    def get_dependency_graph(self) -> Dict[str, List[str]]:
        """Get dependency graph for visualization"""
        dependencies = {}
        for node in self._graph.nodes():
            deps = list(self._graph.successors(node))
            if deps:
                dependencies[node] = deps
        return dependencies
    
    def clear_cache(self):
        """Clear indicator cache"""
        self._cache.clear()
    
    def create_example_indicator(self, indicator_type: str = 'function') -> Path:
        """Create example indicator file"""
        
        if indicator_type == 'function':
            example_code = '''"""
Example Volume Indicator Function
Save this as indicators/indicator_volume_example.py
"""

def high_volume_up_trend(data, volume_threshold=1.5, trend_period=5):
    """
    Check if stock is in uptrend with high volume
    Returns: Boolean signal
    """
    if len(data) < max(trend_period, 20):
        return False
    
    # Calculate volume ratio
    current_volume = data['volume'].iloc[-1]
    avg_volume = data['volume'].tail(20).mean()
    volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0
    
    # Calculate price trend
    current_price = data['close'].iloc[-1]
    past_price = data['close'].iloc[-trend_period-1]
    price_change = (current_price - past_price) / past_price
    
    return volume_ratio > volume_threshold and price_change > 0.02


def volume_weighted_rsi(data, rsi_period=14):
    """
    RSI weighted by recent volume
    """
    if len(data) < rsi_period + 1:
        return 50.0
    
    # Get RSI first
    prices = data['close'].tail(rsi_period + 1).values
    deltas = np.diff(prices)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    
    avg_gain = np.mean(gains)
    avg_loss = np.mean(losses)
    
    if avg_loss == 0:
        rsi = 100.0
    else:
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
    
    # Weight by volume
    volume_ratio = data['volume'].iloc[-1] / data['volume'].tail(20).mean() if len(data) >= 20 else 1.0
    weighted_rsi = rsi * min(volume_ratio, 1.5)  # Cap at 1.5x weight
    
    return min(weighted_rsi, 100)  # Cap at 100
'''
        else:
            example_code = '''"""
Example Class-Based Indicator
Save this as indicators/indicator_advanced.py
"""

import numpy as np
from indicator_base import IndicatorBase, IndicatorResult

class VolumeTrendIndicator(IndicatorBase):
    """
    Advanced volume trend indicator with multiple timeframes
    """
    
    def __init__(self, short_period=5, medium_period=20, long_period=50):
        super().__init__(name="VolumeTrend")
        self.short_period = short_period
        self.medium_period = medium_period
        self.long_period = long_period
        
        # Declare dependencies
        self.dependencies = ['volume_sma', 'relative_volume']
    
    def calculate(self, data):
        """
        Calculate volume trend across multiple timeframes
        Returns: -1 (bearish), 0 (neutral), 1 (bullish)
        """
        if len(data) < self.long_period:
            return IndicatorResult(value=0, name=self.name, params=self.__dict__)
        
        # Get volume data
        volumes = data['volume']
        
        # Calculate SMA for different periods
        short_sma = volumes.tail(self.short_period).mean()
        medium_sma = volumes.tail(self.medium_period).mean()
        long_sma = volumes.tail(self.long_period).mean()
        
        # Determine trend
        if short_sma > medium_sma > long_sma:
            trend = 1  # Bullish: volume increasing across timeframes
        elif short_sma < medium_sma < long_sma:
            trend = -1  # Bearish: volume decreasing across timeframes
        else:
            trend = 0  # Neutral
        
        # Add strength based on relative volume
        current_volume = volumes.iloc[-1]
        relative = current_volume / long_sma if long_sma > 0 else 1
        
        # Adjust trend strength
        if abs(trend) == 1 and relative > 1.5:
            trend *= 2  # Strong trend
        
        return IndicatorResult(
            value=trend,
            name=self.name,
            params={'short_period': self.short_period, 
                    'medium_period': self.medium_period,
                    'long_period': self.long_period}
        )


class CombinedSignal(IndicatorBase):
    """
    Combine multiple indicators into a single signal
    """
    
    def __init__(self, rsi_overbought=70, rsi_oversold=30, volume_threshold=1.3):
        super().__init__(name="CombinedSignal")
        self.rsi_overbought = rsi_overbought
        self.rsi_oversold = rsi_oversold
        self.volume_threshold = volume_threshold
        
        # Declare dependencies
        self.dependencies = ['rsi', 'relative_volume']
    
    def calculate(self, data):
        # Get dependency values
        rsi_value = self.get_dependency('rsi', data, period=14)
        rvol = self.get_dependency('relative_volume', data, period=20)
        
        # Generate signal
        signal = 0  # 0 = neutral, 1 = buy, -1 = sell
        
        if rsi_value < self.rsi_oversold and rvol > self.volume_threshold:
            signal = 1  # Oversold with high volume = buy
        elif rsi_value > self.rsi_overbought and rvol > self.volume_threshold:
            signal = -1  # Overbought with high volume = sell
        
        return IndicatorResult(
            value=signal,
            name=self.name,
            params={'rsi_overbought': self.rsi_overbought,
                    'rsi_oversold': self.rsi_oversold,
                    'volume_threshold': self.volume_threshold}
        )
    
    def get_dependency(self, name, data, **params):
        """Helper to get dependency values"""
        # In real implementation, this would call the library
        # For now, use built-ins
        if name == 'rsi':
            from indicator_base import rsi
            return rsi(data, **params)
        elif name == 'relative_volume':
            from indicator_base import relative_volume
            return relative_volume(data, **params)
        return None
'''
        
        example_path = self.indicators_dir / f"indicator_example_{indicator_type}.py"
        example_path.write_text(example_code)
        print(f"📝 Example {indicator_type} indicator created: {example_path}")
        
        return example_path


# Global instance for easy access
_indicator_library = None

def get_indicator_library(indicators_dir: str = "./indicators") -> IndicatorLibrary:
    """Get or create global indicator library"""
    global _indicator_library
    if _indicator_library is None:
        _indicator_library = IndicatorLibrary(indicators_dir)
    return _indicator_library

def load_indicators(indicator_library: IndicatorLibrary):
    """Load indicators and return them for strategy access"""
    return indicator_library