# 📊 Indicator Development Guide

## Overview

This guide shows you how to create custom technical indicators for the BearishVanish trading system. Indicators are automatically discovered, computed, and made available to your strategies.

---

## Quick Start: Your First Indicator

Here's a minimal working indicator:

```python
# File: simulator/indicators/indicator_my_first_indicator.py

import numpy as np
import pandas as pd
from indicator_base import IndicatorBase, IndicatorResult

class Indicator(IndicatorBase):
    """My first custom indicator"""
    
    def __init__(self):
        super().__init__(name="My First Indicator", version="1.0")
    
    def calculate(self, data: pd.DataFrame, **params) -> IndicatorResult:
        """
        Calculate the indicator
        
        Args:
            data: DataFrame with OHLCV data up to current bar
            **params: Additional parameters (period, multiplier, etc.)
        
        Returns:
            IndicatorResult with calculated values
        """
        if len(data) < 2:
            return self._error("Insufficient data")
        
        # Simple momentum: current close - close from N periods ago
        period = params.get('period', 5)
        
        if len(data) < period + 1:
            return self._error(f"Need at least {period + 1} bars")
        
        close = data['close'].values
        momentum = close[-1] - close[-period]
        
        return IndicatorResult(
            name=self.name,
            value=momentum,
            params={'period': period},
            success=True
        )
```

Save this as `simulator/indicators/indicator_my_first_indicator.py` and your indicator will be automatically available to all strategies!

---

## Understanding the Indicator System

### Indicator Architecture

```
IndicatorBase (parent class)
├── name: str              # Unique identifier
├── version: str           # Version number
├── dependencies: List[str] # Other indicators this depends on
└── calculate()            # Main calculation method
```

### Indicator Lifecycle

1. **Discovery** - System finds all `indicator_*.py` files in `./indicators/`
2. **Instantiation** - Creates an instance of your `Indicator` class
3. **Pre-computation** - Calculates values for entire historical data
4. **Caching** - Results cached to avoid recalculation
5. **Integration** - Added to DataFrame passed to strategies as new column

---

## Available Data in `calculate()`

When your `calculate()` method is called, the `data` parameter contains:

### OHLCV Data (Always Available)
```python
data['open']       # Open price
data['high']       # High price
data['low']        # Low price
data['close']      # Close price
data['volume']     # Trading volume
data['trade_count'] # Number of trades
```

### Pre-existing Indicators
If your indicator depends on others, they will already be in `data`:

```python
# These will be available if defined as dependencies
data['sma_20']     # Simple moving average
data['rsi_14']     # Relative strength index
# etc.
```

### Index Information
```python
data.index         # DatetimeIndex (trading dates)
len(data)          # Number of historical bars
```

---

## Common Indicator Patterns

### 1. Simple Moving Average

```python
import numpy as np
import pandas as pd
from indicator_base import IndicatorBase, IndicatorResult

class Indicator(IndicatorBase):
    """Simple Moving Average"""
    
    def __init__(self):
        super().__init__(name="SMA", version="1.0")
    
    def calculate(self, data: pd.DataFrame, **params) -> IndicatorResult:
        period = params.get('period', 20)
        
        if len(data) < period:
            return self._error(f"Need at least {period} bars")
        
        close = data['close'].values
        
        # Use rolling window
        sma = pd.Series(close).rolling(window=period).mean().values
        
        # Return result as array (one value per bar)
        return IndicatorResult(
            name=f"{self.name}_{period}",
            value=sma,
            params={'period': period},
            success=True
        )
```

### 2. Relative Strength Index (RSI)

```python
from indicator_base import IndicatorBase, IndicatorResult
import numpy as np
import pandas as pd

class Indicator(IndicatorBase):
    """Relative Strength Index"""
    
    def __init__(self):
        super().__init__(name="RSI", version="1.0")
    
    def calculate(self, data: pd.DataFrame, **params) -> IndicatorResult:
        period = params.get('period', 14)
        
        if len(data) < period + 1:
            return self._error(f"Need at least {period + 1} bars")
        
        close = data['close'].values
        deltas = np.diff(close)
        
        # Separate gains and losses
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        # Calculate RSI
        avg_gain = pd.Series(gains).rolling(window=period).mean()
        avg_loss = pd.Series(losses).rolling(window=period).mean()
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return IndicatorResult(
            name=f"{self.name}_{period}",
            value=rsi.values,
            params={'period': period},
            success=True
        )
```

### 3. Bollinger Bands

```python
from indicator_base import IndicatorBase, IndicatorResult
import numpy as np
import pandas as pd

class Indicator(IndicatorBase):
    """Bollinger Bands"""
    
    def __init__(self):
        super().__init__(name="BollingerBands", version="1.0")
    
    def calculate(self, data: pd.DataFrame, **params) -> IndicatorResult:
        period = params.get('period', 20)
        std_dev = params.get('std_dev', 2)
        
        if len(data) < period:
            return self._error(f"Need at least {period} bars")
        
        close = data['close'].values
        
        # Calculate middle band (SMA)
        sma = pd.Series(close).rolling(window=period).mean()
        
        # Calculate standard deviation
        std = pd.Series(close).rolling(window=period).std()
        
        # Calculate bands
        upper = sma + (std * std_dev)
        lower = sma - (std * std_dev)
        
        # Return as multi-value result
        # You need to save multiple outputs
        result_dict = {
            'middle': sma.values,
            'upper': upper.values,
            'lower': lower.values,
            'width': (upper - lower).values
        }
        
        return IndicatorResult(
            name=f"{self.name}_{period}",
            value=result_dict,
            params={'period': period, 'std_dev': std_dev},
            success=True
        )
```

### 4. On-Balance Volume (OBV)

```python
from indicator_base import IndicatorBase, IndicatorResult
import numpy as np
import pandas as pd

class Indicator(IndicatorBase):
    """On-Balance Volume"""
    
    def __init__(self):
        super().__init__(name="OBV", version="1.0")
    
    def calculate(self, data: pd.DataFrame, **params) -> IndicatorResult:
        if len(data) < 2:
            return self._error("Need at least 2 bars")
        
        close = data['close'].values
        volume = data['volume'].values
        
        obv = np.zeros(len(close))
        obv[0] = volume[0]
        
        for i in range(1, len(close)):
            if close[i] > close[i-1]:
                obv[i] = obv[i-1] + volume[i]
            elif close[i] < close[i-1]:
                obv[i] = obv[i-1] - volume[i]
            else:
                obv[i] = obv[i-1]
        
        return IndicatorResult(
            name=self.name,
            value=obv,
            params={},
            success=True
        )
```

---

## Indicator Dependencies (Advanced)

Indicators can depend on other indicators! Build complex indicators from simple building blocks:

### Example: MACD (Depends on EMA)

```python
from indicator_base import IndicatorBase, IndicatorResult
import pandas as pd

class Indicator(IndicatorBase):
    """MACD (Moving Average Convergence Divergence)"""
    
    def __init__(self):
        super().__init__(
            name="MACD",
            version="1.0",
            dependencies=['EMA']  # Depends on EMA indicator
        )
    
    def calculate(self, data: pd.DataFrame, **params) -> IndicatorResult:
        # Use pre-calculated EMAs if available
        if 'ema_12' not in data.columns or 'ema_26' not in data.columns:
            return self._error("EMA indicators required")
        
        ema_12 = data['ema_12'].values
        ema_26 = data['ema_26'].values
        
        # MACD line = 12-period EMA - 26-period EMA
        macd = ema_12 - ema_26
        
        # Signal line = 9-period EMA of MACD
        signal = pd.Series(macd).ewm(span=9).mean().values
        
        # MACD Histogram
        histogram = macd - signal
        
        result_dict = {
            'macd': macd,
            'signal': signal,
            'histogram': histogram
        }
        
        return IndicatorResult(
            name=self.name,
            value=result_dict,
            params={},
            success=True
        )
```

---

## Working with Multi-Value Indicators

Some indicators return multiple series (like Bollinger Bands). Handle this in your strategy:

```python
# In your indicator's calculate() method:
def calculate(self, data: pd.DataFrame, **params):
    # Return dictionary for multi-value indicators
    result = {
        'upper': upper_band,
        'middle': middle_band,
        'lower': lower_band
    }
    
    return IndicatorResult(
        name=self.name,
        value=result,
        params=params,
        success=True
    )
```

Then in your strategy:

```python
def generate_signal(self, symbol, data, spy_data, bar_index):
    # Access multi-value indicator
    if 'bb_upper' in data.columns:  # When saved in DataFrame
        upper = data['bb_upper'].iloc[-1]
        lower = data['bb_lower'].iloc[-1]
        # Use the values
```

---

## Indicator Base Class Methods

### Available Methods in `IndicatorBase`

```python
class Indicator(IndicatorBase):
    def __init__(self):
        super().__init__(
            name="MyIndicator",           # Required
            version="1.0",                # Required
            dependencies=[]               # Optional: other indicators needed
        )
    
    def calculate(self, data: pd.DataFrame, **params):
        # Main calculation method
        # Return IndicatorResult
        pass
    
    # Helper methods:
    def _success(self, value, params):
        """Create successful result"""
        return IndicatorResult(
            name=self.name,
            value=value,
            params=params,
            success=True
        )
    
    def _error(self, message):
        """Create error result"""
        return IndicatorResult(
            name=self.name,
            value=None,
            params={},
            success=False,
            error=message
        )
    
    def validate_data(self, data, min_length=1):
        """Check if data has minimum length"""
        if len(data) < min_length:
            return False
        return True
```

---

## Performance Optimization

### 1. Use NumPy for Speed

```python
import numpy as np

# ❌ SLOW: Python loop
result = []
for i in range(len(close)):
    result.append((close[i] + close[i-1]) / 2)

# ✅ FAST: NumPy vectorized
result = (close + np.roll(close, 1)) / 2
```

### 2. Use Pandas Efficiently

```python
import pandas as pd

# Calculate moving average
sma = pd.Series(close).rolling(window=20).mean()

# Calculate returns
returns = pd.Series(close).pct_change()

# Calculate cumulative sum
cumsum = pd.Series(values).cumsum()
```

### 3. Numba JIT Compilation

For CPU-intensive indicators, use Numba:

```python
from numba import jit
import numpy as np

@jit(nopython=True)
def fast_calculation(prices, window):
    """Numba-compiled indicator (10-100x faster)"""
    result = np.zeros(len(prices))
    for i in range(window, len(prices)):
        result[i] = np.mean(prices[i-window:i])
    return result

class Indicator(IndicatorBase):
    def calculate(self, data, **params):
        result = fast_calculation(data['close'].values, params.get('period', 20))
        return IndicatorResult(...)
```

---

## Testing Your Indicator

### Manual Testing

```python
import pandas as pd
from pathlib import Path
import sys

# Add simulator to path
sys.path.insert(0, '/home/dev/BearishVanish/simulator')

from indicators.indicator_my_custom import Indicator
from data_manager import DataManager

# Load sample data
dm = DataManager()
data = dm.get_stock_data('AAPL', days=100)

# Create indicator
ind = Indicator()

# Calculate
result = ind.calculate(data, period=20)

if result.success:
    print(f"Indicator: {result.name}")
    print(f"Last value: {result.value[-1]}")
    print(f"Type: {type(result.value)}")
else:
    print(f"Error: {result.error}")
```

### System Testing

Run full simulation to see indicator in action:

```bash
cd /home/dev/BearishVanish/simulator
python3 main.py --offline --tickers AAPL,MSFT

# Your indicator will be automatically computed and available
# Check in strategy if using the indicator name
```

---

## Indicator Naming Convention

When your indicator returns a single value, it becomes a DataFrame column:

```python
# In your indicator:
return IndicatorResult(name="MyIndicator_20", value=result_array, ...)

# In strategy, access as:
data['myindicator_20']  # Lowercase, underscores preserved
```

For multi-value indicators, each key becomes a column:

```python
# In your indicator:
result = {'upper': upper_array, 'lower': lower_array}
return IndicatorResult(name="Bands", value=result, ...)

# In strategy, access as:
data['bands_upper']
data['bands_lower']
```

---

## Common Indicators Reference

Here's what's already built in:

| Indicator | Column Name | Parameters | Description |
|-----------|------------|------------|-------------|
| SMA | `sma_20`, `sma_50`, `sma_200` | `period` | Simple Moving Average |
| EMA | `ema_12`, `ema_26` | `period` | Exponential Moving Average |
| RSI | `rsi_14` | `period` | Relative Strength Index |
| BB | `bb_upper`, `bb_middle`, `bb_lower` | `period`, `std_dev` | Bollinger Bands |
| OBV | `on_balance_volume` | - | On-Balance Volume |
| Fib | (see indicator file) | `window` | Fibonacci Levels |

---

## Building New Indicators - Strategy

Follow this process:

1. **Identify the calculation** - What mathematical operation?
2. **Prototype in Python** - Write the basic logic
3. **Optimize** - Vectorize with NumPy/Pandas
4. **Create indicator class** - Inherit from IndicatorBase
5. **Test manually** - Verify calculations
6. **Test in system** - Run full simulation
7. **Use in strategies** - Implement trading logic

---

## Advanced: Indicators with State

Some indicators need to maintain state between calculations:

```python
from indicator_base import IndicatorBase, IndicatorResult

class Indicator(IndicatorBase):
    """Indicator that tracks state"""
    
    def __init__(self):
        super().__init__(name="Stateful", version="1.0")
        self.state = 0
    
    def calculate(self, data: pd.DataFrame, **params):
        # Access state from previous calculation
        current_state = self.state
        
        # Calculate new state
        new_state = current_state + data['close'].iloc[-1]
        
        # Update for next calculation
        self.state = new_state
        
        return IndicatorResult(
            name=self.name,
            value=new_state,
            params={},
            success=True
        )
```

---

## Troubleshooting

### Indicator Not Appearing in Data

1. Check filename: Must be `indicator_*.py` in `./indicators/`
2. Check class name: Must be exactly `class Indicator(IndicatorBase)`
3. Check `calculate()` method signature
4. Return `IndicatorResult` object, not raw values
5. Check console for error messages during pre-computation

### Indicator Returns All NaN

1. Check data length requirement
2. Verify column names exist in input data
3. Use `self._error()` for insufficient data
4. Test with sample data manually

### Dependency Not Available

1. Ensure dependency indicator exists as file
2. Check dependency spelling matches indicator name
3. Dependencies are calculated first, but check order
4. Add to dependencies list in `__init__`

---

## Performance Tips

1. **Pre-calculate what you can** - Minimize per-bar computation
2. **Use NumPy operations** - Vectorized is 100x faster
3. **Avoid loops** - Use Pandas rolling, apply, etc.
4. **Cache intermediate results** - Avoid recalculating
5. **Handle errors gracefully** - Return `_error()` for insufficient data

---

## Next Steps

- Study included indicators in `./indicators/` directory
- Create your first custom indicator
- Test it with strategies in `strategy_development_guide.md`
- Combine indicators to create complex analysis
- Share useful indicators with the community!

Good luck! 📊🚀
