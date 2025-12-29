#!/usr/bin/env python3
"""
Simple WAL Mode Verification Script
Run this to verify WAL mode is properly configured
"""

import sqlite3
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

print("="*70)
print("WAL MODE VERIFICATION TEST")
print("="*70)

# Test 1: Check get_utf8_connection function
print("\nTest 1: Checking get_utf8_connection utility...")
try:
    from utilities.utf8_helpers import get_utf8_connection
    print("✅ get_utf8_connection imported successfully")
except ImportError as e:
    print(f"❌ Failed to import get_utf8_connection: {e}")
    sys.exit(1)

# Test 2: Create test database with WAL mode
print("\nTest 2: Creating test database with WAL mode...")
test_db = Path('./test_wal_verification.db')
test_db.unlink(missing_ok=True)

conn = get_utf8_connection(
    test_db,
    journal_mode='WAL',
    synchronous='NORMAL',
    cache_size=10000,
    temp_store='MEMORY'
)

# Test 3: Verify PRAGMA settings
print("\nTest 3: Verifying PRAGMA settings...")
cursor = conn.cursor()

cursor.execute("PRAGMA journal_mode;")
journal_mode = cursor.fetchone()[0]
print(f"  journal_mode: {journal_mode}")

cursor.execute("PRAGMA synchronous;")
synchronous = cursor.fetchone()[0]
print(f"  synchronous: {synchronous}")

cursor.execute("PRAGMA cache_size;")
cache_size = cursor.fetchone()[0]
print(f"  cache_size: {cache_size}")

cursor.execute("PRAGMA temp_store;")
temp_store = cursor.fetchone()[0]
print(f"  temp_store: {temp_store}")

# Test 4: Create table and insert data
print("\nTest 4: Testing write operations...")
cursor.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, value TEXT)")
cursor.execute("INSERT INTO test VALUES (1, 'test')")
conn.commit()

# Test 5: Check for WAL files
print("\nTest 5: Checking for WAL files...")
wal_file = Path(str(test_db) + '-wal')
shm_file = Path(str(test_db) + '-shm')

print(f"  {test_db.name}: {test_db.exists()} ({test_db.stat().st_size if test_db.exists() else 0} bytes)")
print(f"  {wal_file.name}: {wal_file.exists()}" +
      (f" ({wal_file.stat().st_size} bytes)" if wal_file.exists() else ""))
print(f"  {shm_file.name}: {shm_file.exists()}" +
      (f" ({shm_file.stat().st_size} bytes)" if shm_file.exists() else ""))

conn.close()

# Test 6: Test SimulationTelemetry
print("\nTest 6: Testing SimulationTelemetry...")
try:
    from simulation_telemetry import SimulationTelemetry

    telemetry = SimulationTelemetry(simulation_name="wal_test")
    print(f"  Database created: {telemetry.db_path.name}")

    # Check journal mode
    conn = sqlite3.connect(telemetry.db_path)
    cursor = conn.cursor()
    cursor.execute("PRAGMA journal_mode;")
    journal_mode = cursor.fetchone()[0]
    conn.close()

    print(f"  journal_mode: {journal_mode}")

    # Cleanup
    telemetry.db_path.unlink(missing_ok=True)
    Path(str(telemetry.db_path) + '-wal').unlink(missing_ok=True)
    Path(str(telemetry.db_path) + '-shm').unlink(missing_ok=True)

    if journal_mode.upper() == 'WAL':
        print("✅ SimulationTelemetry uses WAL mode correctly")
    else:
        print(f"❌ SimulationTelemetry NOT using WAL (current: {journal_mode})")

except Exception as e:
    print(f"❌ Error testing SimulationTelemetry: {e}")
    import traceback
    traceback.print_exc()

# Cleanup
test_db.unlink(missing_ok=True)
wal_file.unlink(missing_ok=True)
shm_file.unlink(missing_ok=True)

print("\n" + "="*70)
print("TEST COMPLETE")
print("="*70)
print("\nIf all tests show WAL mode enabled, the implementation is correct.")
print("To test performance, run a full simulation with:")
print("  python main.py --universe sp500 --offline")
print("="*70 + "\n")
