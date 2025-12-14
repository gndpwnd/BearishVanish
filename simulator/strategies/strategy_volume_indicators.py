"""
Example strategy using the modular indicator system
"""

from strategy_base import StrategyBase

class Strategy(StrategyBase):
    def __init__(self, color="green", initial_capital=100000, 
                 position_size_pct=0.10, max_positions=10):
        super().__init__(
            name="Volume Indicator Strategy",
            color=color,
            initial_capital=initial_capital,
            position_size_pct=position_size_pct,
            max_positions=max_positions
        )
        
    def on_data(self, stock_data, spy_data, current_date, symbol):
        """
        Advanced strategy using multiple indicators
        """
        # Skip if we don't have enough data
        if len(stock_data) < 21:  # Need 20 days for many indicators
            return None
        
        try:
            # Get volume metrics using built-in helper
            volume_metrics = self.get_all_volume_metrics(stock_data)
            
            # Get current price
            current_price = stock_data['close'].iloc[-1]
            
            # Use indicators from the library if available
            if hasattr(self, 'indicator_library') and self.indicator_library:
                # Example 1: Check for volume spike
                volume_spike = self.indicator_library.get('volume_spike', stock_data, threshold=2.0)
                
                # Example 2: Get RSI
                rsi_value = self.indicator_library.get('rsi', stock_data, period=14)
                
                # Example 3: Get custom indicator if it exists
                try:
                    # This will automatically load from ./indicators/
                    custom_signal = self.indicator_library.get('high_volume_up_trend', stock_data)
                except ValueError:
                    custom_signal = None
                
                # Strategy logic
                if volume_spike and rsi_value < 35:
                    # Volume spike + oversold RSI = buy
                    if self.can_generate_signal('BUY', symbol):
                        return self.emit_signal('BUY', symbol)
                        
                elif rsi_value > 70 and volume_metrics['relative_volume'] > 1.5:
                    # Overbought RSI + high volume = sell
                    if self.can_generate_signal('SELL', symbol):
                        return self.emit_signal('SELL', symbol)
                        
                elif custom_signal:  # If custom indicator says buy
                    if self.can_generate_signal('BUY', symbol):
                        return self.emit_signal('BUY', symbol)
            
            # Fallback: Simple volume-based logic
            elif volume_metrics['relative_volume'] > 2.0:
                if self.can_generate_signal('BUY', symbol):
                    return self.emit_signal('BUY', symbol)
            
        except Exception as e:
            print(f"⚠️  Error in {self.name} for {symbol}: {e}")
            
        return None