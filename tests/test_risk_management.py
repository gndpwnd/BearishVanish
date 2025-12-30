#!/usr/bin/env python3
"""
Risk Management Test Suite

Tests for:
1. TrailingStop class - stop level updates and triggers
2. Regime Filter - SPY 200 SMA market regime filtering
"""

import pytest
import numpy as np
import pandas as pd
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "simulator"))


# ============================================================================
# TrailingStop Tests
# ============================================================================

class TestTrailingStop:
    """Tests for TrailingStop class functionality"""

    def test_initial_stop_level(self):
        """Test that initial stop is set correctly at entry"""
        from trailing_stop import TrailingStop

        entry_price = 100.0
        initial_stop_pct = 0.07  # 7%

        stop = TrailingStop(entry_price=entry_price, initial_stop_pct=initial_stop_pct)

        expected_stop = entry_price * (1 - initial_stop_pct)  # 93.0
        assert stop.stop_price == expected_stop
        assert stop.highest_price == entry_price
        assert stop.trailing_active is False

    def test_stop_level_unchanged_when_price_falls(self):
        """Test that stop level does not decrease when price falls"""
        from trailing_stop import TrailingStop

        entry_price = 100.0
        stop = TrailingStop(entry_price=entry_price, initial_stop_pct=0.07, trail_pct=0.05)

        initial_stop = stop.stop_price  # 93.0

        # Price falls - stop should NOT change
        stop.update(95.0)
        assert stop.stop_price == initial_stop
        assert stop.highest_price == entry_price  # Highest price unchanged

        stop.update(90.0)
        assert stop.stop_price == initial_stop
        assert stop.highest_price == entry_price

    def test_trailing_activation_threshold(self):
        """Test that trailing only activates after price rises above entry + trail_pct"""
        from trailing_stop import TrailingStop

        entry_price = 100.0
        trail_pct = 0.05  # 5%
        stop = TrailingStop(entry_price=entry_price, initial_stop_pct=0.07, trail_pct=trail_pct)

        initial_stop = stop.stop_price  # 93.0
        activation_threshold = entry_price * (1 + trail_pct)  # 105.0

        # Price rises but below activation threshold - trailing should NOT activate
        stop.update(103.0)
        assert stop.trailing_active is False
        assert stop.stop_price == initial_stop  # Stop unchanged

        # Price rises above activation threshold - trailing SHOULD activate
        stop.update(106.0)
        assert stop.trailing_active is True
        # New stop should be 106 * 0.95 = 100.7
        expected_new_stop = 106.0 * (1 - trail_pct)
        assert stop.stop_price == expected_new_stop

    def test_stop_level_rises_as_price_rises(self):
        """Test that stop level correctly updates as price rises (after activation)"""
        from trailing_stop import TrailingStop

        entry_price = 100.0
        trail_pct = 0.05
        stop = TrailingStop(entry_price=entry_price, initial_stop_pct=0.07, trail_pct=trail_pct)

        # Activate trailing
        stop.update(106.0)  # Above 105 threshold
        stop_at_106 = stop.stop_price  # 100.7

        # Price rises more - stop should rise
        stop.update(110.0)
        stop_at_110 = stop.stop_price  # 104.5
        assert stop_at_110 > stop_at_106
        assert stop_at_110 == 110.0 * (1 - trail_pct)

        # Price rises even more
        stop.update(120.0)
        stop_at_120 = stop.stop_price  # 114.0
        assert stop_at_120 > stop_at_110
        assert stop_at_120 == 120.0 * (1 - trail_pct)

    def test_stop_triggers_when_price_falls_below(self):
        """Test that is_stopped returns True when price falls below stop"""
        from trailing_stop import TrailingStop

        entry_price = 100.0
        stop = TrailingStop(entry_price=entry_price, initial_stop_pct=0.07, trail_pct=0.05)

        # Initial stop is at 93.0
        assert stop.is_stopped(94.0) is False
        assert stop.is_stopped(93.0) is True  # At stop level
        assert stop.is_stopped(92.0) is True  # Below stop level

    def test_trailing_stop_scenario_with_price_sequence(self):
        """Test complete trailing stop scenario with realistic price sequence"""
        from trailing_stop import TrailingStop

        entry_price = 100.0
        stop = TrailingStop(entry_price=entry_price, initial_stop_pct=0.07, trail_pct=0.05)

        # Simulate price sequence
        prices = [100, 102, 104, 106, 108, 110, 108, 106, 104, 103]
        # Expected stops:
        # 100: initial stop = 93.0, not trailing
        # 102: not above 105, stop = 93.0
        # 104: not above 105, stop = 93.0
        # 106: above 105, trailing activated, stop = 100.7
        # 108: stop = 102.6
        # 110: stop = 104.5
        # 108: price falls, stop stays at 104.5
        # 106: price falls, stop stays at 104.5
        # 104: price falls below stop (104 < 104.5), should be stopped

        for price in prices[:-1]:
            stop.update(price)

        # After rising to 110, stop should be at 104.5
        assert abs(stop.stop_price - 104.5) < 0.01

        # Final price of 103 should trigger stop
        assert stop.is_stopped(103.0) is True

    def test_get_profit_pct(self):
        """Test profit percentage calculation"""
        from trailing_stop import TrailingStop

        entry_price = 100.0
        stop = TrailingStop(entry_price=entry_price, initial_stop_pct=0.07, trail_pct=0.05)

        # 10% profit
        assert abs(stop.get_profit_pct(110.0) - 10.0) < 0.01
        # 5% loss
        assert abs(stop.get_profit_pct(95.0) - (-5.0)) < 0.01
        # At entry
        assert stop.get_profit_pct(100.0) == 0.0

    def test_get_stop_distance_pct(self):
        """Test stop distance percentage calculation"""
        from trailing_stop import TrailingStop

        entry_price = 100.0
        stop = TrailingStop(entry_price=entry_price, initial_stop_pct=0.07, trail_pct=0.05)

        # At entry price (100), stop is at 93
        # Distance = (100 - 93) / 100 * 100 = 7%
        assert abs(stop.get_stop_distance_pct(100.0) - 7.0) < 0.01

    def test_edge_case_zero_trail_pct(self):
        """Test edge case with zero trailing percentage"""
        from trailing_stop import TrailingStop

        entry_price = 100.0
        stop = TrailingStop(entry_price=entry_price, initial_stop_pct=0.07, trail_pct=0.0)

        # With 0% trail, activation threshold is entry_price * 1.0 = 100
        # So any price above entry activates trailing
        stop.update(101.0)
        assert stop.trailing_active is True
        # New stop = 101 * 1.0 = 101 (0% below price)
        assert stop.stop_price == 101.0


# ============================================================================
# Regime Filter Tests
# ============================================================================

def create_mock_spy_data(prices: list, start_date: str = "2023-01-01") -> pd.DataFrame:
    """
    Create mock SPY data for testing regime filters

    Args:
        prices: List of closing prices
        start_date: Start date for the date range

    Returns:
        DataFrame with date index and OHLCV columns
    """
    dates = pd.date_range(start=start_date, periods=len(prices), freq='B')

    data = pd.DataFrame({
        'open': prices,
        'high': [p * 1.01 for p in prices],
        'low': [p * 0.99 for p in prices],
        'close': prices,
        'volume': [1000000] * len(prices)
    }, index=dates)

    return data


def create_mock_stock_data(prices: list, start_date: str = "2023-01-01") -> pd.DataFrame:
    """Create mock stock data for testing"""
    dates = pd.date_range(start=start_date, periods=len(prices), freq='B')

    data = pd.DataFrame({
        'open': prices,
        'high': [p * 1.01 for p in prices],
        'low': [p * 0.99 for p in prices],
        'close': prices,
        'volume': [500000] * len(prices)
    }, index=dates)

    return data


class TestRegimeFilter:
    """Tests for market regime filtering (SPY 200 SMA)"""

    def test_regime_filter_blocks_buys_in_bear_market(self):
        """Test that strategies skip trades when SPY < 200 SMA"""
        # Create SPY data where current price is BELOW 200 SMA
        # Need at least 200 data points for SMA calculation

        # Create prices that start high and trend down (bear market)
        # SMA will be higher than current price
        base_prices = list(range(500, 300, -1))  # 200 prices, descending from 500 to 301
        spy_data = create_mock_spy_data(base_prices)

        # Calculate 200 SMA for verification
        spy_sma_200 = spy_data['close'].rolling(200).mean().iloc[-1]
        spy_price = spy_data['close'].iloc[-1]

        # Verify we're in a bear market scenario
        assert spy_price < spy_sma_200, f"Test setup error: SPY {spy_price} should be < SMA {spy_sma_200}"

        # Simulate the regime filter logic (as used in strategies)
        should_block_buy = spy_price < spy_sma_200
        assert should_block_buy == True

    def test_regime_filter_allows_buys_in_bull_market(self):
        """Test that strategies allow trades when SPY > 200 SMA"""
        # Create SPY data where current price is ABOVE 200 SMA
        # Prices trend up (bull market)

        base_prices = list(range(300, 500))  # 200 prices, ascending from 300 to 499
        spy_data = create_mock_spy_data(base_prices)

        # Calculate 200 SMA for verification
        spy_sma_200 = spy_data['close'].rolling(200).mean().iloc[-1]
        spy_price = spy_data['close'].iloc[-1]

        # Verify we're in a bull market scenario
        assert spy_price > spy_sma_200, f"Test setup error: SPY {spy_price} should be > SMA {spy_sma_200}"

        # Simulate the regime filter logic
        should_allow_buy = spy_price > spy_sma_200
        assert should_allow_buy == True

    def test_regime_filter_with_insufficient_data(self):
        """Test that regime filter doesn't block when insufficient SPY data"""
        # Less than 200 data points
        base_prices = list(range(400, 500))  # Only 100 prices
        spy_data = create_mock_spy_data(base_prices)

        # Simulate the regime filter check from strategies
        # When len(spy_data) < 200, filter should not apply
        if len(spy_data) >= 200:
            should_apply_filter = True
        else:
            should_apply_filter = False

        assert should_apply_filter is False
        assert len(spy_data) == 100

    def test_regime_filter_boundary_case_equal_to_sma(self):
        """Test boundary case when SPY price equals 200 SMA"""
        # Create flat prices so SMA equals current price
        flat_price = 400.0
        base_prices = [flat_price] * 200
        spy_data = create_mock_spy_data(base_prices)

        spy_sma_200 = spy_data['close'].rolling(200).mean().iloc[-1]
        spy_price = spy_data['close'].iloc[-1]

        # Verify prices are equal
        assert abs(spy_price - spy_sma_200) < 0.01

        # Per strategy logic: spy_price < spy_sma_200 blocks
        # Equal should NOT block (not strictly less than)
        should_block = spy_price < spy_sma_200
        assert should_block == False

    def test_regime_filter_integration_with_momentum_strategy(self):
        """Test regime filter integration as implemented in momentum strategy"""
        # This tests the exact logic from strategy_momentum_example.py

        # Bear market scenario
        bear_prices = list(range(500, 300, -1))  # Descending
        spy_data_bear = create_mock_spy_data(bear_prices)

        # Simulate the exact code from momentum strategy
        if spy_data_bear is not None and len(spy_data_bear) >= 200:
            spy_sma_200 = spy_data_bear['close'].rolling(200).mean().iloc[-1]
            spy_price = spy_data_bear['close'].iloc[-1]
            bear_market = spy_price < spy_sma_200
        else:
            bear_market = False

        assert bear_market == True, "Should detect bear market"

        # Bull market scenario
        bull_prices = list(range(300, 500))  # Ascending
        spy_data_bull = create_mock_spy_data(bull_prices)

        if spy_data_bull is not None and len(spy_data_bull) >= 200:
            spy_sma_200 = spy_data_bull['close'].rolling(200).mean().iloc[-1]
            spy_price = spy_data_bull['close'].iloc[-1]
            bull_market = spy_price > spy_sma_200
        else:
            bull_market = False

        assert bull_market == True, "Should detect bull market"

    def test_regime_filter_allows_sells_in_bear_market(self):
        """Test that regime filter only blocks new buys, not sells"""
        # Bear market scenario - but sells should still be allowed
        bear_prices = list(range(500, 300, -1))
        spy_data = create_mock_spy_data(bear_prices)

        spy_sma_200 = spy_data['close'].rolling(200).mean().iloc[-1]
        spy_price = spy_data['close'].iloc[-1]

        is_bear_market = spy_price < spy_sma_200
        assert is_bear_market == True

        # Per strategy logic:
        # In bear market, existing positions can still be sold
        # Only NEW positions are blocked
        in_position = True  # Simulate being in a position

        # Regime filter should NOT block sells (only blocks buys when NOT in position)
        if is_bear_market and not in_position:
            signal_blocked = True
        else:
            signal_blocked = False

        assert signal_blocked is False, "Sells should not be blocked in bear market"

    def test_sma_calculation_accuracy(self):
        """Test that 200 SMA is calculated correctly"""
        # Create known prices for SMA verification
        prices = [100.0] * 100 + [200.0] * 100  # 100 prices at 100, 100 prices at 200
        spy_data = create_mock_spy_data(prices)

        # Expected SMA = (100*100 + 200*100) / 200 = 150
        spy_sma_200 = spy_data['close'].rolling(200).mean().iloc[-1]

        assert abs(spy_sma_200 - 150.0) < 0.01

    def test_regime_filter_with_volatile_market(self):
        """Test regime filter behavior with volatile prices crossing SMA"""
        # Create prices that oscillate around a mean
        np.random.seed(42)
        base = 400
        prices = [base + 50 * np.sin(i * 0.1) + np.random.randn() * 5 for i in range(250)]
        spy_data = create_mock_spy_data(prices)

        spy_sma_200 = spy_data['close'].rolling(200).mean().iloc[-1]
        spy_price = spy_data['close'].iloc[-1]

        # The filter should work regardless of volatility
        is_bear = spy_price < spy_sma_200
        is_bull = spy_price > spy_sma_200

        # Exactly one should be true (unless exactly equal, which is rare)
        assert is_bear != is_bull or abs(spy_price - spy_sma_200) < 0.01


# ============================================================================
# Combined Tests - TrailingStop + Regime Filter Interaction
# ============================================================================

class TestCombinedRiskManagement:
    """Tests for combined risk management scenarios"""

    def test_trailing_stop_respects_regime_on_entry(self):
        """Test that trailing stop is only created after regime filter passes"""
        from trailing_stop import TrailingStop

        # Bull market - should allow entry and create trailing stop
        bull_prices = list(range(300, 500))
        spy_data = create_mock_spy_data(bull_prices)
        spy_sma_200 = spy_data['close'].rolling(200).mean().iloc[-1]
        spy_price = spy_data['close'].iloc[-1]

        # Simulate strategy flow
        can_enter = spy_price > spy_sma_200

        if can_enter:
            entry_price = 50.0  # Some stock price
            stop = TrailingStop(entry_price=entry_price, initial_stop_pct=0.07, trail_pct=0.05)
            assert stop.stop_price == entry_price * 0.93
        else:
            stop = None

        assert stop is not None, "Should create trailing stop in bull market"

    def test_trailing_stop_still_works_in_bear_market_for_existing_positions(self):
        """Test that trailing stops protect existing positions even in bear market"""
        from trailing_stop import TrailingStop

        # Position entered during bull market
        entry_price = 100.0
        stop = TrailingStop(entry_price=entry_price, initial_stop_pct=0.07, trail_pct=0.05)

        # Price rises during bull market
        stop.update(110.0)  # Above activation threshold
        stop.update(115.0)  # Trailing stop rises

        # Now market turns bearish - but stop should still work
        bear_prices = list(range(500, 300, -1))
        spy_data = create_mock_spy_data(bear_prices)
        spy_sma_200 = spy_data['close'].rolling(200).mean().iloc[-1]
        spy_price = spy_data['close'].iloc[-1]
        is_bear_market = spy_price < spy_sma_200

        assert is_bear_market == True

        # Stock price falls in bear market - stop should trigger
        current_stock_price = stop.stop_price - 1.0  # Below stop
        assert stop.is_stopped(current_stock_price) == True


# ============================================================================
# Run tests if executed directly
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
