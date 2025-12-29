# Quick Test Guide - Database Performance

**Status:** Ready to Test | Scripts Created | Implementation Complete

---

## 30-Second Quick Test

```bash
cd /home/devel/BearishVanish/simulator
python test_wal_simple.py
```

**What it checks:** WAL mode enabled, PRAGMA settings, file creation

**Expected:** All tests pass with "✅" marks

---

## 1-Minute Performance Test

```bash
cd /home/devel/BearishVanish/simulator
python test_db_performance.py
```

**What it measures:** DELETE vs WAL speedup (expected: 5-20x)

**Expected:** Speedup >= 5x, all tests pass

---

## 2-Minute Simulation Test

```bash
cd /home/devel/BearishVanish/simulator
python main.py --test-performance
```

**What it does:** Mini simulation with real strategies

**Expected:** Completes successfully, creates WAL database files

**Verify after:**
```bash
ls -la simulations/simulation_*.db*
sqlite3 simulations/simulation_*.db "PRAGMA journal_mode;"
# Should output: wal
```

---

## What to Look For

### ✅ Success Indicators

- `journal_mode: wal` in all databases
- `.db-wal` and `.db-shm` files created
- Speedup >= 5x in performance tests
- All telemetry data recorded
- No errors in test output

### ❌ Failure Indicators

- `journal_mode: delete` instead of `wal`
- No WAL files created
- Speedup < 2x
- Database errors or corruption
- Missing telemetry data

---

## Troubleshooting

### If Tests Fail

1. Check Python version: `python --version` (need 3.8+)
2. Check dependencies: `pip install -r requirements.txt`
3. Check permissions: `ls -la simulations/`
4. Review error messages in output

### If No Speedup

- May indicate very fast SSD (already optimized)
- Check PRAGMA settings manually
- Try larger dataset (use full simulation)

---

## Full Documentation

- **Summary:** `/home/devel/BearishVanish/DATABASE_PERFORMANCE_SUMMARY.md`
- **Test Plan:** `/home/devel/BearishVanish/simulator/TEST_PLAN.md`
- **Detailed Findings:** `/home/devel/BearishVanish/0_docs/Findings/2024-12-28_database_performance_test_results.md`

---

**Quick Answer: Is it working?**

Run: `python test_wal_simple.py`

If you see "✅ WAL mode is ENABLED" → Yes, it's working!
