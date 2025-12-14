"""
Base class for trading strategies with FIXED signal state management.
All strategies should inherit from this class and implement the on_data method.
"""

class StrategyBase:
    def __init__(self, name="Strategy", color="blue", 
                 initial_capital=100000, 
                 position_size_pct=0.10, 
                 max_positions=10):
        """
        Initialize strategy with customizable parameters.
        
        Args:
            name: Strategy name
            color: Display color for charts
            initial_capital: Starting capital for this strategy
            position_size_pct: Percentage of portfolio allocated per position (0-1)
            max_positions: Maximum number of concurrent positions
        """
        self.name = name
        self.color = color
        self.initial_capital = initial_capital
        self.position_size_pct = position_size_pct
        self.max_positions = max_positions
        self.reset()
    
    def reset(self):
        """Reset strategy state for a new simulation"""
        self.history = {}  # Track history per symbol
        self.last_executed_signal = {}  # Track EXECUTED signals per symbol (not attempted)
        
        # Debug tracking
        self.attempted_signals = {}  # Track all signal attempts
        self.blocked_signals = {}  # Track blocked signals
    
    def get_config(self):
        """Return strategy configuration for telemetry"""
        return {
            'name': self.name,
            'color': self.color,
            'initial_capital': self.initial_capital,
            'position_size_pct': self.position_size_pct,
            'max_positions': self.max_positions
        }
    
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
        """
        Check if we can generate this signal type for this symbol
        
        CRITICAL FIX: Only check EXECUTED signals, not attempted ones
        This prevents "stuck" signals when max positions is reached
        """
        # First signal for this symbol - always allowed
        if symbol not in self.last_executed_signal:
            return True
        
        # Can't generate same signal twice in a row (must alternate BUY/SELL)
        if self.last_executed_signal[symbol] == signal_type:
            # Track that this was blocked
            if symbol not in self.blocked_signals:
                self.blocked_signals[symbol] = []
            self.blocked_signals[symbol].append({
                'signal': signal_type,
                'reason': 'duplicate_signal'
            })
            return False
        
        return True
    
    def emit_signal(self, signal_type, symbol):
        """
        Emit a signal for this symbol
        
        IMPORTANT: This does NOT update last_executed_signal
        That only happens when the trade actually executes (see record_execution)
        """
        if signal_type in ['BUY', 'SELL']:
            # Track attempted signal (for debugging)
            if symbol not in self.attempted_signals:
                self.attempted_signals[symbol] = []
            self.attempted_signals[symbol].append(signal_type)
            
            return signal_type
        return None
    
    def record_execution(self, signal_type, symbol):
        """
        Record that a signal was actually EXECUTED (trade completed)
        
        Call this from simulator after execute_trade succeeds
        """
        if signal_type in ['BUY', 'SELL']:
            self.last_executed_signal[symbol] = signal_type
    
    def get_debug_stats(self):
        """Get debug statistics about signal generation"""
        return {
            'symbols_with_attempts': len(self.attempted_signals),
            'symbols_with_executions': len(self.last_executed_signal),
            'symbols_with_blocks': len(self.blocked_signals),
            'total_attempts': sum(len(v) for v in self.attempted_signals.values()),
            'total_blocks': sum(len(v) for v in self.blocked_signals.values()),
            'config': self.get_config()
        }
    
    def print_debug_stats(self):
        """Print debug statistics"""
        stats = self.get_debug_stats()
        print(f"\n📊 {self.name} Configuration:")
        print(f"   Initial Capital: ${self.initial_capital:,.0f}")
        print(f"   Position Size: {self.position_size_pct*100:.1f}%")
        print(f"   Max Positions: {self.max_positions}")
        print(f"\n   Signal Statistics:")
        print(f"   Symbols with signal attempts: {stats['symbols_with_attempts']}")
        print(f"   Symbols with executions: {stats['symbols_with_executions']}")
        print(f"   Symbols with blocked signals: {stats['symbols_with_blocks']}")
        print(f"   Total signal attempts: {stats['total_attempts']}")
        print(f"   Total blocked signals: {stats['total_blocks']}")
        
        # Show sample of blocked signals
        if self.blocked_signals:
            print(f"\n   Sample blocked signals (first 5):")
            for symbol in list(self.blocked_signals.keys())[:5]:
                blocks = self.blocked_signals[symbol]
                print(f"      {symbol}: {len(blocks)} blocks - {blocks[0]['reason']}")