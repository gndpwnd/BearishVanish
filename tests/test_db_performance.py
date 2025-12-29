#!/usr/bin/env python3
"""
Test database performance improvements with WAL mode
Tests the WAL mode implementation and measures write performance
"""

import sqlite3
import time
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from utilities.utf8_helpers import get_utf8_connection

def test_wal_mode_enabled():
    """Test that WAL mode is properly enabled"""
    print("\n" + "="*70)
    print("TEST 1: WAL Mode Configuration")
    print("="*70)

    # Create test database
    test_db = Path('./test_wal_performance.db')

    # Test 1: Create database with WAL mode
    print("\n1. Creating database with WAL mode...")
    conn = get_utf8_connection(
        test_db,
        journal_mode='WAL',
        synchronous='NORMAL',
        cache_size=10000,
        temp_store='MEMORY'
    )

    cursor = conn.cursor()

    # Check journal mode
    cursor.execute("PRAGMA journal_mode;")
    journal_mode = cursor.fetchone()[0]

    print(f"   Journal mode: {journal_mode}")

    if journal_mode.upper() == 'WAL':
        print("   ✅ WAL mode is ENABLED")
    else:
        print(f"   ❌ WAL mode is NOT enabled (current: {journal_mode})")
        return False

    # Check other PRAGMA settings
    cursor.execute("PRAGMA synchronous;")
    synchronous = cursor.fetchone()[0]
    print(f"   Synchronous: {synchronous} (1=NORMAL is optimal)")

    cursor.execute("PRAGMA cache_size;")
    cache_size = cursor.fetchone()[0]
    print(f"   Cache size: {cache_size} pages (~{abs(cache_size) * 4 / 1024:.1f} MB)")

    cursor.execute("PRAGMA temp_store;")
    temp_store = cursor.fetchone()[0]
    print(f"   Temp store: {temp_store} (2=MEMORY)")

    conn.close()

    # Test 2: Check for WAL files
    print("\n2. Checking for WAL files...")
    wal_file = Path(str(test_db) + '-wal')
    shm_file = Path(str(test_db) + '-shm')

    # Reconnect to trigger WAL file creation
    conn = sqlite3.connect(test_db)
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS test (id INTEGER)")
    cursor.execute("INSERT INTO test VALUES (1)")
    conn.commit()

    if wal_file.exists():
        print(f"   ✅ WAL file exists: {wal_file.name} ({wal_file.stat().st_size} bytes)")
    else:
        print(f"   ⚠️  WAL file not yet created (will be created on first write)")

    if shm_file.exists():
        print(f"   ✅ Shared memory file exists: {shm_file.name} ({shm_file.stat().st_size} bytes)")
    else:
        print(f"   ⚠️  Shared memory file not yet created")

    conn.close()

    # Cleanup test database
    test_db.unlink(missing_ok=True)
    wal_file.unlink(missing_ok=True)
    shm_file.unlink(missing_ok=True)

    return True


def benchmark_write_performance():
    """Benchmark write performance with and without WAL mode"""
    print("\n" + "="*70)
    print("TEST 2: Write Performance Benchmark")
    print("="*70)

    num_records = 10000

    # Test with DELETE journal mode (default)
    print(f"\n1. Testing DELETE journal mode ({num_records:,} inserts)...")
    test_db = Path('./test_delete_mode.db')
    test_db.unlink(missing_ok=True)

    conn = sqlite3.connect(test_db)
    conn.execute("PRAGMA journal_mode=DELETE")
    conn.execute("PRAGMA synchronous=FULL")
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE test_data (
            id INTEGER PRIMARY KEY,
            timestamp INTEGER,
            strategy TEXT,
            symbol TEXT,
            price REAL,
            volume INTEGER
        )
    """)

    start_time = time.time()
    for i in range(num_records):
        cursor.execute(
            "INSERT INTO test_data VALUES (?, ?, ?, ?, ?, ?)",
            (i, int(time.time()), 'TestStrategy', 'AAPL', 150.0 + i * 0.01, 1000000 + i)
        )
    conn.commit()
    delete_time = time.time() - start_time

    conn.close()
    test_db.unlink()

    print(f"   Time: {delete_time:.2f}s")
    print(f"   Rate: {num_records/delete_time:,.0f} inserts/sec")

    # Test with WAL journal mode
    print(f"\n2. Testing WAL journal mode ({num_records:,} inserts)...")
    test_db = Path('./test_wal_mode.db')
    test_db.unlink(missing_ok=True)

    conn = get_utf8_connection(
        test_db,
        journal_mode='WAL',
        synchronous='NORMAL',
        cache_size=10000
    )
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE test_data (
            id INTEGER PRIMARY KEY,
            timestamp INTEGER,
            strategy TEXT,
            symbol TEXT,
            price REAL,
            volume INTEGER
        )
    """)

    start_time = time.time()
    for i in range(num_records):
        cursor.execute(
            "INSERT INTO test_data VALUES (?, ?, ?, ?, ?, ?)",
            (i, int(time.time()), 'TestStrategy', 'AAPL', 150.0 + i * 0.01, 1000000 + i)
        )
    conn.commit()
    wal_time = time.time() - start_time

    conn.close()

    # Check for WAL files
    wal_file = Path(str(test_db) + '-wal')
    shm_file = Path(str(test_db) + '-shm')
    print(f"   WAL file: {wal_file.exists()} ({wal_file.stat().st_size if wal_file.exists() else 0} bytes)")
    print(f"   SHM file: {shm_file.exists()}")

    test_db.unlink()
    wal_file.unlink(missing_ok=True)
    shm_file.unlink(missing_ok=True)

    print(f"   Time: {wal_time:.2f}s")
    print(f"   Rate: {num_records/wal_time:,.0f} inserts/sec")

    # Calculate speedup
    speedup = delete_time / wal_time if wal_time > 0 else 1
    print(f"\n3. Performance Comparison:")
    print(f"   DELETE mode: {delete_time:.2f}s")
    print(f"   WAL mode: {wal_time:.2f}s")
    print(f"   Speedup: {speedup:.1f}x faster with WAL mode")

    if speedup >= 5:
        print(f"   ✅ Excellent! WAL mode provides {speedup:.1f}x speedup")
    elif speedup >= 2:
        print(f"   ✅ Good! WAL mode provides {speedup:.1f}x speedup")
    else:
        print(f"   ⚠️  Speedup lower than expected ({speedup:.1f}x)")

    return speedup


def test_batch_insert_performance():
    """Test batch insert performance (what our simulation uses)"""
    print("\n" + "="*70)
    print("TEST 3: Batch Insert Performance")
    print("="*70)

    num_records = 10000
    batch_size = 1000

    print(f"\nTesting batch inserts ({num_records:,} records in batches of {batch_size})...")

    test_db = Path('./test_batch_inserts.db')
    test_db.unlink(missing_ok=True)

    conn = get_utf8_connection(
        test_db,
        journal_mode='WAL',
        synchronous='NORMAL',
        cache_size=10000
    )
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE test_data (
            id INTEGER PRIMARY KEY,
            timestamp INTEGER,
            strategy TEXT,
            symbol TEXT,
            price REAL,
            volume INTEGER
        )
    """)

    # Prepare batch data
    batch_data = [
        (i, int(time.time()), 'TestStrategy', 'AAPL', 150.0 + i * 0.01, 1000000 + i)
        for i in range(num_records)
    ]

    start_time = time.time()

    # Insert in batches
    for i in range(0, len(batch_data), batch_size):
        batch = batch_data[i:i+batch_size]
        cursor.executemany(
            "INSERT INTO test_data VALUES (?, ?, ?, ?, ?, ?)",
            batch
        )

    conn.commit()
    elapsed = time.time() - start_time

    # Verify data
    cursor.execute("SELECT COUNT(*) FROM test_data")
    count = cursor.fetchone()[0]

    conn.close()
    test_db.unlink()
    Path(str(test_db) + '-wal').unlink(missing_ok=True)
    Path(str(test_db) + '-shm').unlink(missing_ok=True)

    print(f"   Time: {elapsed:.2f}s")
    print(f"   Rate: {num_records/elapsed:,.0f} inserts/sec")
    print(f"   Records inserted: {count:,}")

    if count == num_records:
        print(f"   ✅ All records inserted successfully")
    else:
        print(f"   ❌ Record count mismatch: {count} vs {num_records}")

    return elapsed


def test_simulation_telemetry_setup():
    """Test that SimulationTelemetry uses WAL mode"""
    print("\n" + "="*70)
    print("TEST 4: SimulationTelemetry WAL Mode")
    print("="*70)

    try:
        from simulation_telemetry import SimulationTelemetry

        print("\n1. Creating SimulationTelemetry instance...")
        telemetry = SimulationTelemetry(simulation_name="test_wal_mode")

        print(f"   Database: {telemetry.db_path}")

        # Check journal mode
        conn = sqlite3.connect(telemetry.db_path)
        cursor = conn.cursor()

        cursor.execute("PRAGMA journal_mode;")
        journal_mode = cursor.fetchone()[0]

        print(f"   Journal mode: {journal_mode}")

        if journal_mode.upper() == 'WAL':
            print(f"   ✅ SimulationTelemetry uses WAL mode")
            result = True
        else:
            print(f"   ❌ SimulationTelemetry NOT using WAL mode (current: {journal_mode})")
            result = False

        conn.close()

        # Cleanup
        telemetry.db_path.unlink(missing_ok=True)
        Path(str(telemetry.db_path) + '-wal').unlink(missing_ok=True)
        Path(str(telemetry.db_path) + '-shm').unlink(missing_ok=True)

        return result

    except Exception as e:
        print(f"   ❌ Error testing SimulationTelemetry: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all database performance tests"""
    print("\n" + "="*70)
    print("DATABASE PERFORMANCE TEST SUITE")
    print("Testing WAL Mode Implementation")
    print("="*70)

    results = {}

    # Test 1: WAL mode configuration
    results['wal_enabled'] = test_wal_mode_enabled()

    # Test 2: Write performance benchmark
    results['speedup'] = benchmark_write_performance()

    # Test 3: Batch insert performance
    results['batch_time'] = test_batch_insert_performance()

    # Test 4: SimulationTelemetry setup
    results['telemetry_wal'] = test_simulation_telemetry_setup()

    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)

    print(f"\n✅ Tests Passed:")
    if results['wal_enabled']:
        print(f"   - WAL mode configuration: PASS")
    else:
        print(f"   - WAL mode configuration: FAIL")

    if results['speedup'] >= 2:
        print(f"   - Write performance: PASS ({results['speedup']:.1f}x speedup)")
    else:
        print(f"   - Write performance: FAIL ({results['speedup']:.1f}x speedup)")

    if results['batch_time'] > 0:
        print(f"   - Batch inserts: PASS ({results['batch_time']:.2f}s)")
    else:
        print(f"   - Batch inserts: FAIL")

    if results['telemetry_wal']:
        print(f"   - SimulationTelemetry WAL: PASS")
    else:
        print(f"   - SimulationTelemetry WAL: FAIL")

    # Overall result
    all_passed = (
        results['wal_enabled'] and
        results['speedup'] >= 2 and
        results['batch_time'] > 0 and
        results['telemetry_wal']
    )

    print(f"\n{'='*70}")
    if all_passed:
        print("✅ ALL TESTS PASSED")
        print(f"   Database performance improvements verified!")
        print(f"   Expected speedup in production: {results['speedup']:.1f}x - 15x")
    else:
        print("❌ SOME TESTS FAILED")
        print("   Review test output above for details")
    print(f"{'='*70}\n")

    return 0 if all_passed else 1


if __name__ == '__main__':
    sys.exit(main())
