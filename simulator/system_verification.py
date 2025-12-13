"""
System Verification Script
Checks what features are actually integrated and working
Run this to see what's missing!
"""

import sys
from pathlib import Path
import importlib.util

def check_file_exists(filepath, description):
    """Check if a file exists and report"""
    path = Path(filepath)
    if path.exists():
        print(f"✅ {description}")
        print(f"   → {path.absolute()}")
        return True
    else:
        print(f"❌ {description}")
        print(f"   → MISSING: {filepath}")
        return False

def check_module_has_function(module_path, function_name):
    """Check if a module has a specific function"""
    try:
        spec = importlib.util.spec_from_file_location("temp_module", module_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        if hasattr(module, function_name):
            print(f"   ✅ Has {function_name}()")
            return True
        else:
            print(f"   ❌ Missing {function_name}()")
            return False
    except Exception as e:
        print(f"   ❌ Error checking: {e}")
        return False

def check_class_has_method(module_path, class_name, method_name):
    """Check if a class has a specific method"""
    try:
        spec = importlib.util.spec_from_file_location("temp_module", module_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        if hasattr(module, class_name):
            cls = getattr(module, class_name)
            if hasattr(cls, method_name):
                print(f"   ✅ {class_name}.{method_name}() exists")
                return True
            else:
                print(f"   ❌ {class_name} missing {method_name}()")
                return False
        else:
            print(f"   ❌ Class {class_name} not found")
            return False
    except Exception as e:
        print(f"   ❌ Error checking: {e}")
        return False

def main():
    print("\n" + "="*70)
    print("SYSTEM VERIFICATION - Checking Integration Status")
    print("="*70 + "\n")
    
    issues = []
    
    # ============================================================
    # 1. Check Core Files
    # ============================================================
    print("📋 CHECKING CORE FILES:\n")
    
    core_files = {
        'strategy_tracker.py': 'Strategy Tracker (should have new methods)',
        'simulator.py': 'Simulator (should integrate telemetry)',
        'strategy_analysis.py': 'Strategy Analysis (should show risk)',
    }
    
    for file, desc in core_files.items():
        if not check_file_exists(file, desc):
            issues.append(f"Missing file: {file}")
    
    # ============================================================
    # 2. Check New Feature Files
    # ============================================================
    print("\n📦 CHECKING NEW FEATURE FILES:\n")
    
    feature_files = {
        'simulation_telemetry.py': 'Telemetry System',
        'risk_analysis.py': 'Risk Analysis Module',
        'portfolio_risk_analyzer.py': 'Portfolio Risk Analyzer',
        'analysis_components.py': 'Analysis Components',
        'trade_history_viewer.py': 'Trade History Viewer',
        'stock_detail_viewer.py': 'Stock Detail Viewer',
    }
    
    for file, desc in feature_files.items():
        if not check_file_exists(file, desc):
            issues.append(f"Missing feature file: {file}")
    
    # ============================================================
    # 3. Check StrategyTracker Methods
    # ============================================================
    print("\n🔧 CHECKING STRATEGY TRACKER METHODS:\n")
    
    tracker_path = Path('strategy_tracker.py')
    if tracker_path.exists():
        required_methods = [
            ('get_portfolio_beta', 'Calculate portfolio beta'),
            ('get_information_ratio', 'Calculate information ratio'),
            ('get_alpha', 'Calculate alpha'),
            ('get_trade_history_dataframe', 'Get trade history as DataFrame'),
            ('get_stock_performance_summary', 'Get per-stock performance'),
        ]
        
        print("Checking strategy_tracker.py for new methods:")
        for method, desc in required_methods:
            if not check_class_has_method(tracker_path, 'StrategyTracker', method):
                issues.append(f"StrategyTracker missing {method}()")
    
    # ============================================================
    # 4. Check Telemetry Database
    # ============================================================
    print("\n🗄️ CHECKING TELEMETRY DATABASE:\n")
    
    telemetry_dir = Path('./telemetry')
    telemetry_db = telemetry_dir / 'simulations.db'
    
    if telemetry_dir.exists():
        print(f"✅ Telemetry directory exists: {telemetry_dir.absolute()}")
        
        if telemetry_db.exists():
            size_kb = telemetry_db.stat().st_size / 1024
            print(f"✅ Database exists: {telemetry_db.name} ({size_kb:.1f} KB)")
            
            # Check if database has tables
            try:
                import sqlite3
                conn = sqlite3.connect(telemetry_db)
                cursor = conn.cursor()
                
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [row[0] for row in cursor.fetchall()]
                
                expected_tables = ['simulations', 'strategy_performance', 'trades', 
                                 'daily_snapshots', 'stock_performance']
                
                print(f"\n   Tables found: {len(tables)}")
                for table in expected_tables:
                    if table in tables:
                        cursor.execute(f"SELECT COUNT(*) FROM {table}")
                        count = cursor.fetchone()[0]
                        print(f"   ✅ {table}: {count} rows")
                    else:
                        print(f"   ❌ Missing table: {table}")
                        issues.append(f"Telemetry database missing {table} table")
                
                conn.close()
                
            except Exception as e:
                print(f"   ⚠️  Error reading database: {e}")
                issues.append("Could not read telemetry database")
        else:
            print(f"❌ Database not found: {telemetry_db}")
            print("   Telemetry is NOT being collected!")
            issues.append("Telemetry database doesn't exist")
    else:
        print(f"❌ Telemetry directory not found: {telemetry_dir}")
        issues.append("Telemetry system not set up")
    
    # ============================================================
    # 5. Check Simulator Integration
    # ============================================================
    print("\n🔗 CHECKING SIMULATOR INTEGRATION:\n")
    
    simulator_path = Path('simulator.py')
    if simulator_path.exists():
        with open(simulator_path, 'r') as f:
            content = f.read()
        
        checks = [
            ('from simulation_telemetry import telemetry', 'Telemetry import'),
            ('telemetry.start_simulation', 'Start simulation telemetry'),
            ('telemetry.record_trade_entry', 'Record trade entries'),
            ('telemetry.record_trade_exit', 'Record trade exits'),
            ('telemetry.finalize_strategy', 'Finalize strategy metrics'),
        ]
        
        print("Checking simulator.py for telemetry integration:")
        for check_str, desc in checks:
            if check_str in content:
                print(f"   ✅ {desc}")
            else:
                print(f"   ❌ Missing: {desc}")
                issues.append(f"Simulator missing: {desc}")
    
    # ============================================================
    # 6. Check Analysis Integration
    # ============================================================
    print("\n📊 CHECKING ANALYSIS INTEGRATION:\n")
    
    analysis_path = Path('strategy_analysis.py')
    if analysis_path.exists():
        with open(analysis_path, 'r') as f:
            content = f.read()
        
        checks = [
            ('risk_analysis', 'Risk analysis import'),
            ('RiskAnalyzer', 'Risk analyzer usage'),
            ('show_stock_detail_window', 'Stock detail viewer'),
            ('show_trade_history_window', 'Trade history viewer'),
        ]
        
        print("Checking strategy_analysis.py for new features:")
        for check_str, desc in checks:
            if check_str in content:
                print(f"   ✅ {desc}")
            else:
                print(f"   ❌ Missing: {desc}")
                issues.append(f"Analysis missing: {desc}")
    
    # ============================================================
    # 7. Summary
    # ============================================================
    print("\n" + "="*70)
    print("VERIFICATION SUMMARY")
    print("="*70 + "\n")
    
    if not issues:
        print("✅ ALL CHECKS PASSED!")
        print("\nYour system appears to be fully integrated.")
        print("If you're still seeing issues:")
        print("  1. Make sure you're running the latest code")
        print("  2. Check that simulation_id is being passed to analysis functions")
        print("  3. Verify telemetry is being written (check database file size)")
    else:
        print(f"❌ FOUND {len(issues)} ISSUES:\n")
        for i, issue in enumerate(issues, 1):
            print(f"  {i}. {issue}")
        
        print("\n" + "="*70)
        print("RECOMMENDED ACTIONS:")
        print("="*70 + "\n")
        
        if any('telemetry' in issue.lower() for issue in issues):
            print("🔧 TELEMETRY NOT INTEGRATED:")
            print("   → Follow TELEMETRY_INTEGRATION_GUIDE.md")
            print("   → Create simulation_telemetry.py")
            print("   → Update simulator.py with telemetry calls")
        
        if any('tracker' in issue.lower() for issue in issues):
            print("\n🔧 TRACKER METHODS MISSING:")
            print("   → Add new methods to strategy_tracker.py")
            print("   → Copy from strategy_tracker_additions.py artifact")
        
        if any('analysis' in issue.lower() for issue in issues):
            print("\n🔧 ANALYSIS NOT UPDATED:")
            print("   → Create risk_analysis.py")
            print("   → Update strategy_analysis.py")
            print("   → Add risk analysis button")
        
        if any('database' in issue.lower() for issue in issues):
            print("\n🔧 TELEMETRY DATABASE ISSUES:")
            print("   → Run a simulation to create database")
            print("   → Check ./telemetry/ directory")
            print("   → Verify telemetry.start_simulation() is called")
    
    print("\n" + "="*70 + "\n")

if __name__ == '__main__':
    main()