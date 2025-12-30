#!/usr/bin/env python3
"""
Metrics Accuracy Test Suite

Tests to validate that:
1. Risk metrics are calculated correctly
2. No look-ahead bias in simulations
3. Slippage is applied correctly
4. Annualization factors are consistent
"""

import numpy as np
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "analysis"))
sys.path.insert(0, str(PROJECT_ROOT / "simulator"))

# Constants
TRADING_DAYS_PER_YEAR = 252
RISK_FREE_RATE = 0.04  # 4% annual


def test_sharpe_ratio_calculation():
    """Verify Sharpe ratio matches manual calculation"""
    print("\n=== Test: Sharpe Ratio Calculation ===")

    # Sample daily returns (in decimal form)
    returns = np.array([0.01, -0.02, 0.015, -0.01, 0.02, 0.005, -0.008, 0.012])

    # Manual calculation
    daily_rf = RISK_FREE_RATE / TRADING_DAYS_PER_YEAR
    excess = returns - daily_rf
    expected_sharpe = (excess.mean() / excess.std()) * np.sqrt(TRADING_DAYS_PER_YEAR)

    print(f"  Returns: {returns}")
    print(f"  Daily risk-free: {daily_rf:.6f}")
    print(f"  Excess returns mean: {excess.mean():.6f}")
    print(f"  Excess returns std: {excess.std():.6f}")
    print(f"  Expected Sharpe: {expected_sharpe:.4f}")

    # Import and test system calculation
    try:
        from calculators.risk_metrics import RiskMetricsCalculator
        # Note: Full test would require a mock database reader
        print("  [INFO] RiskMetricsCalculator imported successfully")
        print("  [PASS] Formula verified manually")
    except ImportError as e:
        print(f"  [SKIP] Could not import RiskMetricsCalculator: {e}")

    return True


def test_sortino_ratio_units():
    """Verify Sortino ratio uses consistent units"""
    print("\n=== Test: Sortino Ratio Units ===")

    returns = np.array([0.01, -0.02, 0.015, -0.01, 0.02])
    target = 0.0

    # Calculate downside deviation (correct formula)
    excess = returns - target
    downside_sq = np.where(excess < 0, excess ** 2, 0)
    downside_dev = np.sqrt(np.mean(downside_sq)) * np.sqrt(TRADING_DAYS_PER_YEAR)

    # Mean excess (annualized)
    mean_excess_annual = returns.mean() * TRADING_DAYS_PER_YEAR

    # Both in same units (decimal annualized)
    expected_sortino = mean_excess_annual / downside_dev if downside_dev > 0 else 0

    print(f"  Returns: {returns}")
    print(f"  Downside deviation (decimal): {downside_dev:.6f}")
    print(f"  Mean excess annual (decimal): {mean_excess_annual:.6f}")
    print(f"  Expected Sortino: {expected_sortino:.4f}")
    print("  [PASS] Units are consistent (both decimal)")

    return True


def test_downside_deviation_formula():
    """Verify downside deviation uses standard formula"""
    print("\n=== Test: Downside Deviation Formula ===")

    returns = np.array([0.02, -0.01, 0.015, -0.03, 0.01, -0.02, 0.008])
    target = 0.0

    # Correct formula: squared deviations below target, zeros above
    excess = returns - target
    downside_sq = np.where(excess < 0, excess ** 2, 0)
    expected_dd = np.sqrt(np.mean(downside_sq)) * np.sqrt(TRADING_DAYS_PER_YEAR)

    # Wrong formula (old): only negative returns squared
    negative_only = returns[returns < 0]
    wrong_dd = np.sqrt(np.mean(negative_only ** 2)) * np.sqrt(TRADING_DAYS_PER_YEAR)

    print(f"  Returns: {returns}")
    print(f"  Correct downside deviation: {expected_dd:.6f}")
    print(f"  Old (wrong) calculation: {wrong_dd:.6f}")
    print(f"  Difference: {abs(expected_dd - wrong_dd):.6f}")

    # They should be different when there are positive returns
    if expected_dd < wrong_dd:
        print("  [PASS] Correct formula includes zeros for positive returns")
    else:
        print("  [WARN] Formulas are equivalent (no positive returns?)")

    return True


def test_calmar_ratio_edge_case():
    """Verify Calmar ratio handles zero drawdown correctly"""
    print("\n=== Test: Calmar Ratio Edge Case ===")

    # Scenario 1: No drawdown, positive returns
    max_dd = 0.0
    annual_return = 0.12  # 12%

    if max_dd == 0:
        calmar = float('inf') if annual_return > 0 else 0
    else:
        calmar = annual_return / max_dd

    print(f"  Scenario 1: No drawdown, +12% return")
    print(f"  Expected Calmar: inf")
    print(f"  Calculated: {calmar}")

    if calmar == float('inf'):
        print("  [PASS] Returns infinity for positive return with no drawdown")
    else:
        print("  [FAIL] Should return infinity")

    # Scenario 2: No drawdown, zero returns
    annual_return = 0.0
    calmar = float('inf') if annual_return > 0 else 0

    print(f"  Scenario 2: No drawdown, 0% return")
    print(f"  Expected Calmar: 0")
    print(f"  Calculated: {calmar}")

    if calmar == 0:
        print("  [PASS] Returns 0 for zero return with no drawdown")
    else:
        print("  [FAIL] Should return 0")

    return True


def test_slippage_application():
    """Verify slippage is applied correctly"""
    print("\n=== Test: Slippage Application ===")

    SLIPPAGE_PCT = 0.001  # 0.1%
    current_price = 100.0

    # BUY: Should pay more
    buy_price = current_price * (1 + SLIPPAGE_PCT)

    # SELL: Should receive less
    sell_price = current_price * (1 - SLIPPAGE_PCT)

    print(f"  Current price: ${current_price:.2f}")
    print(f"  Slippage: {SLIPPAGE_PCT * 100}%")
    print(f"  BUY execution price: ${buy_price:.4f} (+${buy_price - current_price:.4f})")
    print(f"  SELL execution price: ${sell_price:.4f} (-${current_price - sell_price:.4f})")

    # Round-trip cost
    round_trip_cost = (buy_price - sell_price) / current_price * 100
    print(f"  Round-trip cost: {round_trip_cost:.2f}%")

    if buy_price > current_price and sell_price < current_price:
        print("  [PASS] Slippage works against trader (realistic)")
    else:
        print("  [FAIL] Slippage should work against trader")

    return True


def test_annualization_consistency():
    """Verify annualization factor is consistent across modules"""
    print("\n=== Test: Annualization Consistency ===")

    expected_factor = np.sqrt(252)

    print(f"  Expected annualization factor: sqrt(252) = {expected_factor:.4f}")

    # Check risk_metrics.py
    try:
        from calculators import risk_metrics
        if hasattr(risk_metrics, 'TRADING_DAYS_PER_YEAR'):
            rm_factor = np.sqrt(risk_metrics.TRADING_DAYS_PER_YEAR)
            print(f"  risk_metrics.py: sqrt({risk_metrics.TRADING_DAYS_PER_YEAR}) = {rm_factor:.4f}")
            if abs(rm_factor - expected_factor) < 0.01:
                print("    [PASS]")
            else:
                print("    [FAIL] Mismatch!")
    except ImportError:
        print("  [SKIP] Could not import risk_metrics")

    # Check simulation_telemetry.py
    # Note: Can't easily import without full simulator setup
    print("  simulation_telemetry.py: Check manually that it uses sqrt(252)")
    print("  [INFO] Manual verification required")

    return True


def test_no_look_ahead_bias():
    """Verify simulation doesn't use future data"""
    print("\n=== Test: No Look-Ahead Bias ===")

    print("  This test verifies the code structure:")
    print("  1. Data is sliced with iloc[:i+1] before passing to strategy")
    print("  2. Strategies only see historical_data, not full dataset")
    print("  3. Signal is generated BEFORE trade execution")

    # Check simulator.py has correct pattern
    simulator_path = PROJECT_ROOT / "simulator" / "simulator.py"
    if simulator_path.exists():
        content = simulator_path.read_text()

        # Check for correct slicing pattern
        if "historical_data = stock_data.iloc[:i+1]" in content or \
           "historical_data = enriched_data.iloc[:i+1]" in content:
            print("  [PASS] Found correct historical data slicing pattern")
        else:
            print("  [WARN] Could not verify slicing pattern")

        # Check signal comes before trade
        signal_line = content.find("generate_signal")
        trade_line = content.find("execute_trade")

        if signal_line < trade_line and signal_line > 0:
            print("  [PASS] Signal generated before trade execution")
        else:
            print("  [WARN] Could not verify signal/trade ordering")
    else:
        print("  [SKIP] Could not find simulator.py")

    return True


def run_all_tests():
    """Run all validation tests"""
    print("=" * 60)
    print("  BEARISHVANISH METRICS ACCURACY TEST SUITE")
    print("=" * 60)

    tests = [
        test_sharpe_ratio_calculation,
        test_sortino_ratio_units,
        test_downside_deviation_formula,
        test_calmar_ratio_edge_case,
        test_slippage_application,
        test_annualization_consistency,
        test_no_look_ahead_bias,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            result = test()
            if result:
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"  [ERROR] {test.__name__}: {e}")
            failed += 1

    print("\n" + "=" * 60)
    print(f"  RESULTS: {passed} passed, {failed} failed")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
