#!/usr/bin/env python3
"""
Quick diagnostic to see what's missing
"""

import sys
import os
from pathlib import Path

print("📋 System Status Check")
print("="*60)

# Check critical files
files_to_check = [
    'simulation_telemetry.py',
    'risk_analysis.py', 
    'portfolio_risk_analyzer.py',
    'strategy_tracker.py',
    'simulator.py',
    'strategy_analysis.py'
]

print("\n📂 File Status:")
for file in files_to_check:
    if os.path.exists(file):
        size = os.path.getsize(file) / 1024
        print(f"  ✅ {file}: {size:.1f} KB")
    else:
        print(f"  ❌ {file}: MISSING")

# Check telemetry directory
telemetry_dir = Path('./telemetry')
if telemetry_dir.exists():
    db_path = telemetry_dir / 'simulations.db'
    if db_path.exists():
        size = db_path.stat().st_size / 1024
        print(f"\n📊 Telemetry Database: {size:.1f} KB")
    else:
        print(f"\n📊 Telemetry Database: Not created yet")
else:
    print(f"\n📊 Telemetry Directory: Not created yet")

# Check simulator for telemetry integration
print("\n🔍 Checking simulator.py integration:")
try:
    with open('simulator.py', 'r') as f:
        content = f.read()
        
    checks = {
        'import telemetry': 'from simulation_telemetry' in content or 'import telemetry' in content,
        'telemetry.start_simulation': 'telemetry.start_simulation' in content,
        'telemetry.record_trade': 'telemetry.record_trade' in content,
        'telemetry.finalize': 'telemetry.finalize' in content,
    }
    
    for check_name, passed in checks.items():
        status = "✅" if passed else "❌"
        print(f"  {status} {check_name}")
        
except Exception as e:
    print(f"  ❌ Error checking simulator.py: {e}")

print("\n" + "="*60)
print("Recommendation: Run the integration script below!")
