"""
Trailing Stop Manager
Provides trailing stop functionality for all strategies
"""


class TrailingStop:
    """
    Manages trailing stops for a position

    Usage:
        stop = TrailingStop(entry_price=100, initial_stop_pct=0.07, trail_pct=0.05)

        # Update with each new price
        stop.update(current_price=105)

        # Check if stopped out
        if stop.is_stopped(current_price=98):
            # Sell position
    """

    def __init__(self, entry_price: float, initial_stop_pct: float = 0.07, trail_pct: float = 0.05):
        """
        Args:
            entry_price: Price at which position was entered
            initial_stop_pct: Initial stop loss percentage (e.g., 0.07 for 7%)
            trail_pct: Trailing distance as percentage (e.g., 0.05 for 5%)
        """
        self.entry_price = entry_price
        self.initial_stop_pct = initial_stop_pct
        self.trail_pct = trail_pct

        # Initial stop level
        self.stop_price = entry_price * (1 - initial_stop_pct)
        self.highest_price = entry_price
        self.trailing_active = False

    def update(self, current_price: float) -> float:
        """
        Update trailing stop with new price

        Args:
            current_price: Current market price

        Returns:
            Current stop price
        """
        if current_price > self.highest_price:
            self.highest_price = current_price

            # Activate trailing once price rises above entry + trail_pct
            if current_price > self.entry_price * (1 + self.trail_pct):
                self.trailing_active = True

            # Update stop if trailing is active
            if self.trailing_active:
                new_stop = current_price * (1 - self.trail_pct)
                if new_stop > self.stop_price:
                    self.stop_price = new_stop

        return self.stop_price

    def is_stopped(self, current_price: float) -> bool:
        """Check if position should be stopped out"""
        return current_price <= self.stop_price

    def get_profit_pct(self, current_price: float) -> float:
        """Get current profit percentage"""
        return (current_price - self.entry_price) / self.entry_price * 100

    def get_stop_distance_pct(self, current_price: float) -> float:
        """Get distance to stop as percentage"""
        return (current_price - self.stop_price) / current_price * 100
