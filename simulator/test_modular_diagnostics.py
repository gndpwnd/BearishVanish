"""
Test Script for Modular Universe System
Verifies that diagnostics and reporting modules work correctly
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load API credentials
load_dotenv()
api_key = os.getenv('ALPACA_API_KEY')
secret_key = os.getenv('ALPACA_SECRET_KEY')

# Import the modular universe manager
from stock_universe import UniverseManager

def test_basic_functionality():
    """Test core universe operations"""
    print("\n" + "="*70)
    print("TEST 1: BASIC FUNCTIONALITY")
    print("="*70)
    
    manager = UniverseManager(api_key, secret_key)
    
    # Test getting approved tickers
    print("\n✓ Testing get_approved_tickers()...")
    sp500_tickers = manager.get_approved_tickers('sp500')
    print(f"  Found {len(sp500_tickers)} S&P 500 stocks")
    
    nasdaq_tickers = manager.get_approved_tickers('nasdaq100')
    print(f"  Found {len(nasdaq_tickers)} NASDAQ 100 stocks")
    
    russell_tickers = manager.get_approved_tickers('russell3000')
    print(f"  Found {len(russell_tickers)} Russell 3000 stocks")
    
    print("\n✅ Basic functionality: PASSED")

def test_diagnostics_module():
    """Test diagnostics features"""
    print("\n" + "="*70)
    print("TEST 2: DIAGNOSTICS MODULE")
    print("="*70)
    
    manager = UniverseManager(api_key, secret_key)
    
    # Test mismatch diagnosis
    print("\n✓ Testing diagnose_mismatch()...")
    manager.diagnose_mismatch('russell3000')
    
    # Test data quality check
    print("\n✓ Testing check_data_quality()...")
    manager.diagnostics.check_data_quality('sp500')
    
    # Test duplicate finding
    print("\n✓ Testing find_duplicate_issues()...")
    manager.diagnostics.find_duplicate_issues('russell3000')
    
    # Test universe comparison
    print("\n✓ Testing compare_universes()...")
    manager.diagnostics.compare_universes('sp500', 'nasdaq100')
    
    print("\n✅ Diagnostics module: PASSED")

def test_reporting_module():
    """Test reporting features"""
    print("\n" + "="*70)
    print("TEST 3: REPORTING MODULE")
    print("="*70)
    
    manager = UniverseManager(api_key, secret_key)
    
    # Test status display
    print("\n✓ Testing print_status()...")
    manager.print_status()
    
    # Test ticker info
    print("\n✓ Testing print_ticker_info()...")
    manager.print_ticker_info('AAPL')
    
    # Test recent changes
    print("\n✓ Testing print_recent_changes()...")
    manager.reporter.print_recent_changes('sp500', days=30)
    
    # Test summary
    print("\n✓ Testing print_summary()...")
    manager.reporter.print_summary('nasdaq100')
    
    print("\n✅ Reporting module: PASSED")

def test_lazy_loading():
    """Test that modules are loaded only when needed"""
    print("\n" + "="*70)
    print("TEST 4: LAZY LOADING")
    print("="*70)
    
    manager = UniverseManager(api_key, secret_key)
    
    # Check that modules aren't loaded initially
    print("\n✓ Checking initial state...")
    assert manager._diagnostics is None, "Diagnostics should not be loaded initially"
    assert manager._reporter is None, "Reporter should not be loaded initially"
    print("  Modules not loaded initially: ✅")
    
    # Access diagnostics - should trigger loading
    print("\n✓ Accessing diagnostics module...")
    _ = manager.diagnostics
    assert manager._diagnostics is not None, "Diagnostics should be loaded after access"
    print("  Diagnostics loaded on first access: ✅")
    
    # Access reporter - should trigger loading
    print("\n✓ Accessing reporter module...")
    _ = manager.reporter
    assert manager._reporter is not None, "Reporter should be loaded after access"
    print("  Reporter loaded on first access: ✅")
    
    print("\n✅ Lazy loading: PASSED")

def test_modular_independence():
    """Test that modules can be used independently"""
    print("\n" + "="*70)
    print("TEST 5: MODULAR INDEPENDENCE")
    print("="*70)
    
    manager = UniverseManager(api_key, secret_key)
    
    # Test using diagnostics directly
    print("\n✓ Testing direct diagnostics access...")
    from universe_diagnostics import UniverseDiagnostics
    diagnostics = UniverseDiagnostics(manager)
    
    tickers = manager.get_approved_tickers('sp500')
    format_analysis = diagnostics.analyze_ticker_format(tickers)
    print(f"  Analyzed {format_analysis['total']} tickers")
    print(f"  Found {len(format_analysis['with_dots'])} tickers with dots")
    
    # Test using reporter directly
    print("\n✓ Testing direct reporter access...")
    from universe_reporting import UniverseReporter
    reporter = UniverseReporter(manager)
    
    info = manager.get_universe_info('nasdaq100')
    print(f"  NASDAQ 100: {info['current_count']} stocks")
    
    print("\n✅ Modular independence: PASSED")

def run_all_tests():
    """Run all tests"""
    print("\n" + "="*70)
    print("MODULAR UNIVERSE SYSTEM - TEST SUITE")
    print("="*70)
    print("\nTesting the new modular architecture...")
    
    try:
        test_basic_functionality()
        test_diagnostics_module()
        test_reporting_module()
        test_lazy_loading()
        test_modular_independence()
        
        print("\n" + "="*70)
        print("✅ ALL TESTS PASSED!")
        print("="*70)
        print("\nYour modular universe system is working correctly!")
        print("\nYou can now use:")
        print("  • python simulator.py --diagnose russell3000")
        print("  • python simulator.py --check-quality sp500")
        print("  • python simulator.py --find-duplicates russell3000")
        print("  • python simulator.py --compare sp500 nasdaq100")
        print("\n" + "="*70 + "\n")
        
        return True
        
    except Exception as e:
        print("\n" + "="*70)
        print("❌ TEST FAILED!")
        print("="*70)
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        
        print("\nPlease ensure:")
        print("  1. All three files are in the same directory:")
        print("     - stock_universe.py (updated)")
        print("     - universe_diagnostics.py (new)")
        print("     - universe_reporting.py (new)")
        print("  2. You've run --update-universe at least once")
        print("  3. The database exists in ./universes/stock_universe.db")
        
        return False

if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)