# Database Performance Testing Plan

This document outlines how to test the WAL mode database performance improvements.

---

## Quick Tests (No Data Required)

### Test 1: Verify WAL Configuration

Run the simple verification script:

```bash
cd /home/devel/BearishVanish/simulator
python test_wal_simple.py
```

**Expected Output:**
```
======================================================================
WAL MODE VERIFICATION TEST
======================================================================

Test 1: Checking get_utf8_connection utility...
✅ get_utf8_connection imported successfully

Test 2: Creating test database with WAL mode...

Test 3: Verifying PRAGMA settings...
  journal_mode: wal
  synchronous: 1
  cache_size: 10000
  temp_store: 2

Test 4: Testing write operations...

Test 5: Checking for WAL files...
  test_wal_verification.db: True (12288 bytes)
  test_wal_verification.db-wal: True (xxxxx bytes)
  test_wal_verification.db-shm: True (xxxxx bytes)

Test 6: Testing SimulationTelemetry...
  Database created: simulation_YYYYMMDD_HHMMSS_wal_test.db
  journal_mode: wal
✅ SimulationTelemetry uses WAL mode correctly

======================================================================
TEST COMPLETE
======================================================================
```

**Pass Criteria:**
- ✅ journal_mode = `wal`
- ✅ synchronous = `1` (NORMAL)
- ✅ cache_size = `10000`
- ✅ temp_store = `2` (MEMORY)
- ✅ WAL and SHM files created
- ✅ SimulationTelemetry uses WAL mode

---

### Test 2: Performance Benchmark

Run the comprehensive test suite:

```bash
cd /home/devel/BearishVanish/simulator
python test_db_performance.py
```

**Expected Output:**
```
======================================================================
DATABASE PERFORMANCE TEST SUITE
Testing WAL Mode Implementation
======================================================================

======================================================================
TEST 1: WAL Mode Configuration
======================================================================
...
✅ WAL mode is ENABLED

======================================================================
TEST 2: Write Performance Benchmark
======================================================================

1. Testing DELETE journal mode (10,000 inserts)...
   Time: X.XXs
   Rate: X,XXX inserts/sec

2. Testing WAL journal mode (10,000 inserts)...
   WAL file: True (xxxxx bytes)
   SHM file: True
   Time: X.XXs
   Rate: XX,XXX inserts/sec

3. Performance Comparison:
   DELETE mode: X.XXs
   WAL mode: X.XXs
   Speedup: XX.Xx faster with WAL mode
   ✅ Excellent! WAL mode provides XX.Xx speedup

======================================================================
TEST 3: Batch Insert Performance
======================================================================
   Time: X.XXs
   Rate: XX,XXX inserts/sec
   Records inserted: 10,000
   ✅ All records inserted successfully

======================================================================
TEST 4: SimulationTelemetry WAL Mode
======================================================================
   ✅ SimulationTelemetry uses WAL mode

======================================================================
TEST SUMMARY
======================================================================
✅ ALL TESTS PASSED
   Database performance improvements verified!
   Expected speedup in production: XX.Xx - 15x
```

**Pass Criteria:**
- ✅ WAL mode enabled
- ✅ Speedup >= 5x (target: 10-20x)
- ✅ Batch inserts working
- ✅ SimulationTelemetry using WAL

---

## Simulation Tests (Requires Data)

### Test 3: Performance Test Mode

Run a small test simulation:

```bash
cd /home/devel/BearishVanish/simulator
python main.py --test-performance
```

**What it does:**
- Tests with 2 strategies and 5 symbols
- Runs quick simulation
- Measures performance
- Verifies telemetry recording

**Expected Output:**
```
======================================================================
PERFORMANCE TEST MODE
======================================================================
Testing with 2 strategies and 5 symbols
Expected improvement: 5-15x speedup with telemetry
======================================================================

📥 Loading market data...
...
⚡ Pre-computing X indicators...
...
🚀 Running parallel simulations...
...
💾 Recording telemetry data...
  📊 Collected data counts:
    Trade attempts: X,XXX
    Trade entries: XXX
    Trade exits: XXX
    Portfolio snapshots: X,XXX
...
======================================================================
✅ SIMULATION COMPLETE WITH TELEMETRY
======================================================================
📊 Completed: 10 simulations
⏱️  Time: X.Xs (X.XXs per sim)
⚡ Speed: X,XXX calculations/sec
💾 Database: ./simulations/simulation_YYYYMMDD_HHMMSS_*.db

📈 TELEMETRY RECORDED:
   Trade attempts: X,XXX
   Trade entries: XXX
   Trade exits: XXX
   Portfolio snapshots: X,XXX
...
🎯 Estimated speedup: XX.Xx
```

**Verification:**
```bash
# Check database files
ls -la simulations/simulation_*.db*

# Expected output:
simulation_YYYYMMDD_HHMMSS_*.db
simulation_YYYYMMDD_HHMMSS_*.db-wal
simulation_YYYYMMDD_HHMMSS_*.db-shm

# Check journal mode
sqlite3 simulations/simulation_*.db "PRAGMA journal_mode;"
# Expected: wal

# Check record counts
sqlite3 simulations/simulation_*.db "SELECT COUNT(*) FROM trade_history;"
# Should match telemetry output
```

**Pass Criteria:**
- ✅ Simulation completes successfully
- ✅ Database files created (.db, .db-wal, .db-shm)
- ✅ WAL mode active in database
- ✅ Telemetry records match database counts
- ✅ Speedup estimate reasonable (5-15x)

---

### Test 4: Full Simulation (Optional)

Run a full simulation with offline data:

```bash
cd /home/devel/BearishVanish/simulator
python main.py --universe sp500 --offline
```

**Note:** Requires cached SP500 data. Use `--download` first if needed.

**What to measure:**
1. **Database write time** - Look for "Recording telemetry data..." section
2. **Overall simulation time**
3. **Records written** - Compare counts in output
4. **Database size** - Check file sizes

**Expected Performance:**
- Small simulation (10 symbols): 5-10s total, <1s database writes
- Medium simulation (100 symbols): 30-60s total, <5s database writes
- Large simulation (500 symbols): 2-5 minutes total, <30s database writes

---

## Manual Database Inspection

If you want to manually verify a simulation database:

```bash
cd /home/devel/BearishVanish/simulator/simulations

# List all simulation databases
ls -lah simulation_*.db*

# Connect to a database
sqlite3 simulation_YYYYMMDD_HHMMSS_*.db

# Inside sqlite3:
PRAGMA journal_mode;
# Expected: wal

PRAGMA synchronous;
# Expected: 1 (NORMAL)

PRAGMA cache_size;
# Expected: 10000

# Check table counts
SELECT COUNT(*) FROM trade_attempts;
SELECT COUNT(*) FROM trade_history;
SELECT COUNT(*) FROM portfolio_history;
SELECT COUNT(*) FROM strategy_performance;

# Exit
.quit
```

---

## Performance Baselines

For reference, here are expected performance characteristics:

### Write Operations (per 1000 records)

| Mode | Time | Rate | Speedup |
|------|------|------|---------|
| DELETE + FULL sync | 1.0s | 1,000/s | 1x (baseline) |
| DELETE + NORMAL sync | 0.5s | 2,000/s | 2x |
| WAL + NORMAL sync | 0.05s | 20,000/s | 20x |

### Full Simulation (500 symbols, 3 strategies, 180 days)

| Phase | Records | DELETE Mode | WAL Mode | Speedup |
|-------|---------|-------------|----------|---------|
| Data loading | - | 30s | 30s | 1x |
| Indicator calc | - | 60s | 60s | 1x |
| Simulation | - | 180s | 180s | 1x |
| **Database writes** | **500,000** | **500s** | **25s** | **20x** |
| **TOTAL** | - | **770s** | **295s** | **2.6x** |

**Key takeaway:** WAL mode primarily speeds up database writes. Overall simulation speedup depends on the proportion of time spent writing to database.

---

## Troubleshooting

### Issue: WAL mode not enabled

**Symptoms:**
- `PRAGMA journal_mode` returns `delete` instead of `wal`

**Possible causes:**
1. Database created before WAL implementation
2. PRAGMA not applied correctly
3. Permissions issue on filesystem

**Solution:**
```bash
# Manually enable WAL on existing database
sqlite3 your_database.db "PRAGMA journal_mode=WAL;"

# Or delete old database and recreate
rm your_database.db*
# Run simulation again
```

---

### Issue: No speedup observed

**Symptoms:**
- Test shows <2x speedup with WAL mode

**Possible causes:**
1. Very fast SSD (already optimized)
2. Small dataset (overhead dominates)
3. Wrong PRAGMA settings

**Diagnostics:**
```bash
# Check PRAGMA settings
sqlite3 your_database.db << EOF
PRAGMA journal_mode;
PRAGMA synchronous;
PRAGMA cache_size;
PRAGMA temp_store;
EOF
```

**Expected output:**
```
wal
1
10000
2
```

---

### Issue: WAL files very large

**Symptoms:**
- `.db-wal` file larger than `.db` file
- Disk space concerns

**Explanation:**
- Normal during heavy writes
- WAL file checkpointed on close
- Automatically cleaned up

**Manual checkpoint:**
```bash
sqlite3 your_database.db "PRAGMA wal_checkpoint(FULL);"
```

---

## Success Criteria Summary

### Code Implementation ✅
- [x] WAL mode in `get_utf8_connection()`
- [x] WAL mode in `SimulationTelemetry`
- [x] WAL mode in `DataManager`
- [x] Optimized PRAGMA settings
- [x] UTF-8 safety maintained

### Runtime Verification ⏸️
- [ ] Test scripts execute without errors
- [ ] PRAGMA settings verified in databases
- [ ] WAL and SHM files created
- [ ] Performance benchmark shows >= 5x speedup

### Production Validation ⏸️
- [ ] Full simulation completes successfully
- [ ] Database writes faster than baseline
- [ ] All telemetry data recorded correctly
- [ ] No data corruption or loss

---

**Last Updated:** 2024-12-28
**Next Review:** After first test simulation
