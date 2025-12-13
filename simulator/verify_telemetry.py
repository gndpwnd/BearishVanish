"""
Telemetry System Verification Script
Run this to test your installation and see examples
"""

import sys
from pathlib import Path

def check_installation():
    """Check if all required files are in place"""
    print("\n" + "="*70)
    print("TELEMETRY SYSTEM INSTALLATION CHECK")
    print("="*70)
    
    required_files = {
        'simulation_telemetry.py': 'Telemetry database system',
        'trade_history_viewer.py': 'Fixed trade history viewer',
        'analysis_components.py': 'Fixed analysis components'
    }
    
    all_good = True
    for file, desc in required_files.items():
        if Path(file).exists():
            print(f"✅ {file:<30} - {desc}")
        else:
            print(f"❌ {file:<30} - MISSING")
            all_good = False
    
    if not all_good:
        print("\n⚠️  Some files are missing! Please create them from the artifacts.")
        return False
    
    print("\n✅ All required files found!")
    return True


def test_telemetry():
    """Test telemetry system functionality"""
    print("\n" + "="*70)
    print("TESTING TELEMETRY SYSTEM")
    print("="*70)
    
    try:
        from simulation_telemetry import telemetry
        print("✅ Telemetry module imported successfully")
        
        # Check database
        if telemetry.db_path.exists():
            size_kb = telemetry.db_path.stat().st_size / 1024
            print(f"✅ Database exists: {telemetry.db_path} ({size_kb:.1f} KB)")
        else:
            print(f"📁 Database will be created at: {telemetry.db_path}")
        
        # Test creating a simulation ID
        from datetime import datetime
        test_id = telemetry.create_simulation_id(
            'test_universe', 
            ['AAPL', 'GOOGL'], 
            datetime.now()
        )
        print(f"✅ Can generate simulation IDs: {test_id}")
        
        # Get history
        history = telemetry.get_simulation_history(limit=5)
        print(f"📊 Found {len(history)} previous simulations")
        
        if len(history) > 0:
            print("\n📋 Recent simulations:")
            print(history[['simulation_id', 'universe_name', 'universe_size', 'start_date']].to_string(index=False))
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing telemetry: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_accurate_win_rate():
    """Test the accurate win rate calculation"""
    print("\n" + "="*70)
    print("TESTING WIN RATE CALCULATION")
    print("="*70)
    
    try:
        from analysis_components import calculate_accurate_win_rate
        
        # Create mock tracker
        class MockTracker:
            def __init__(self):
                self.trades = [
                    {'symbol': 'AAPL', 'action': 'BUY', 'price': 100, 'shares': 10},
                    {'symbol': 'AAPL', 'action': 'SELL', 'price': 110, 'shares': 10},  # Win
                    {'symbol': 'GOOGL', 'action': 'BUY', 'price': 200, 'shares': 5},
                    {'symbol': 'GOOGL', 'action': 'SELL', 'price': 195, 'shares': 5},  # Loss
                    {'symbol': 'MSFT', 'action': 'BUY', 'price': 300, 'shares': 3},     # Open position
                ]
        
        tracker = MockTracker()
        win_rate = calculate_accurate_win_rate(tracker)
        
        print(f"\nTest case:")
        print(f"  Total executions: {len(tracker.trades)}")
        print(f"  Completed trades: 2 (AAPL win, GOOGL loss)")
        print(f"  Open positions: 1 (MSFT)")
        print(f"  Expected win rate: 50.0%")
        print(f"  Calculated win rate: {win_rate:.1f}%")
        
        if abs(win_rate - 50.0) < 0.1:
            print("✅ Win rate calculation is CORRECT!")
            return True
        else:
            print("❌ Win rate calculation is WRONG!")
            return False
            
    except Exception as e:
        print(f"❌ Error testing win rate: {e}")
        import traceback
        traceback.print_exc()
        return False


def show_integration_example():
    """Show example of how to integrate telemetry"""
    print("\n" + "="*70)
    print("INTEGRATION EXAMPLE")
    print("="*70)
    
    example = '''
# In simulator.py, at start of run_simulation():

from simulation_telemetry import telemetry

sim_id = telemetry.start_simulation(
    universe_name=args.universe or 'custom',
    symbols=symbols,
    start_date=spy_data.index[0],
    end_date=spy_data.index[-1],
    initial_capital=INITIAL_CASH,
    config={'force_liquidate': args.force_liquidate}
)

# In the simulation loop, when trades execute:

if signal == 'BUY' and success:
    telemetry.record_trade_entry(
        sim_id, strategy.name, symbol, 
        current_date, current_prices[symbol], 
        tracker.positions[symbol]
    )

if signal == 'SELL' and success:
    telemetry.record_trade_exit(
        sim_id, strategy.name, symbol,
        current_date, current_prices[symbol]
    )

# At end of simulation:

for strategy in strategies:
    telemetry.finalize_strategy(
        sim_id, strategy.name, 
        strategy_trackers[strategy.name],
        spy_returns
    )

telemetry.print_simulation_summary(sim_id)
'''
    
    print(example)


def main():
    """Run all verification checks"""
    print("\n" + "╔" + "═"*68 + "╗")
    print("║" + " "*15 + "TELEMETRY SYSTEM VERIFICATION" + " "*24 + "║")
    print("╚" + "═"*68 + "╝")
    
    # Check installation
    if not check_installation():
        print("\n❌ Installation check failed!")
        print("Please create the missing files from the artifacts.")
        return False
    
    # Test telemetry
    if not test_telemetry():
        print("\n❌ Telemetry test failed!")
        return False
    
    # Test win rate calculation
    if not test_accurate_win_rate():
        print("\n❌ Win rate test failed!")
        return False
    
    # Show integration example
    show_integration_example()
    
    # Final summary
    print("\n" + "="*70)
    print("✅ ALL CHECKS PASSED!")
    print("="*70)
    print("\n🎯 Next Steps:")
    print("1. Follow the integration guide to update simulator.py")
    print("2. Run a test simulation: python main.py --universe sp500")
    print("3. Check telemetry: telemetry.get_simulation_history()")
    print("4. Verify metrics are accurate in the analysis dashboard")
    print("\n📚 Full integration guide: TELEMETRY_INTEGRATION_GUIDE.md")
    print("="*70 + "\n")
    
    return True


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)