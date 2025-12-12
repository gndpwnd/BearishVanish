"""
Base class for trading strategies.
All strategies should inherit from this class and implement the on_data method.
"""

class StrategyBase:
    def __init__(self, name="Strategy", color="blue"):
        self.name = name
        self.color = color
        self.reset()
    
    def reset(self):
        """Reset strategy state for a new simulation"""
        self.history = {}  # Track history per symbol
        self.last_signal = {}  # Track last signal per symbol
        
    def on_data(self, stock_data, spy_data, current_date, symbol):
        """
        Called on each new data point during simulation.
        
        Args:
            stock_data: DataFrame with stock data up to current point
            spy_data: DataFrame with SPY data up to current point  
            current_date: Current date being simulated
            symbol: Stock symbol being processed
            
        Returns:
            'BUY', 'SELL', or None
        """
        raise NotImplementedError("Strategies must implement on_data method")
    
    def can_generate_signal(self, signal_type, symbol):
        """Ensure signals alternate per symbol (no consecutive BUY or SELL)"""
        if symbol not in self.last_signal:
            return True
        if self.last_signal[symbol] == signal_type:
            return False
        return True
    
    def emit_signal(self, signal_type, symbol):
        """Emit a signal and update last_signal for the symbol"""
        if signal_type in ['BUY', 'SELL']:
            self.last_signal[symbol] = signal_type
            return signal_type
        return None