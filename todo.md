Update Todos

Create unified pipeline script (sync, run, fetch)

Investigate why 8 strategies generate no trades

Remove mock data generator and dependencies

Update roadmap with immediate fixes

Fix Mean Reversion strategy (remove VWAP contradiction)

Fix Conservative Income strategy (SMA50 to SMA20)

Fix 500 Intersection strategy (add cooldown)

Fix SP500 Slope v2 strategy (add cooldown)

Fix Breakout strategy (lower volume threshold)

Fix Trend Following strategy (optional Supertrend)

Fix AMIS strategy (column name fallbacks)

Fix Momentum MFI strategy (relax conditions)

Test pipeline with fixed strategies

Document findings
All tasks are complete. Here's a summary of what was accomplished:
Summary
Completed Tasks
Created unified pipeline script (run_full_pipeline.sh)
Single command to sync code to HPC, run simulation+analysis+reports, and fetch results back
Investigated inactive strategies - Identified root causes for 8 strategies with 0 trades
Removed mock data generator - Deleted generate_mock_data.py and cleaned up dependencies
Implemented 8 strategy fixes:
Mean Reversion: Removed VWAP contradiction
Conservative Income: Changed SMA50 filter to SMA20 rising check
500 Intersection: Added 24-hour cooldown instead of one-signal-per-cross
SP500 Slope v2: Same cooldown fix
Breakout: Lowered volume threshold from 1.5x to 1.2x
Trend Following: Made Supertrend optional with EMA fallback
AMIS: Added .get() fallbacks for indicator column names - FIXED: 266 trades
Momentum MFI: Relaxed conditions, 3-of-4 instead of ALL - FIXED: 2,209 trades
Tested pipeline - Ran local test confirming improvements
Documented findings - Created detailed findings document and updated roadmap
Results
Metric	Before	After
Total trades	~200	~2,700
Strategies with trades	4	6
Improvement	-	13x increase
Remaining Work (Phase 2)
Six strategies still show 0 trades due to conditions being too strict. The roadmap has been updated with proposed Phase 2 fixes to further relax these strategies.