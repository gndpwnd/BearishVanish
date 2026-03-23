# BearishVanish - Todo

> Last updated: 2026-03-23

## 🔴 In Progress

_Tasks actively being worked on_

- [ ] Project bootstrap — standardize documentation structure and create scope/roadmap/todo

## 🟡 Blocked

_Tasks waiting on something (include reason)_

_(none currently)_

## 🟢 Up Next

_Priority queue for immediate work_

- [ ] Audit matplotlib usage — identify all matplotlib imports and determine removal path
- [ ] Validate headless operation — confirm the project runs without any GUI dependencies
- [ ] Volume confirmation — implement volume >= 1.2x average filter for entry signals
- [ ] Data download monitoring — add progress tracking during market data downloads

## 📋 Backlog

_Lower priority, do when time permits_

- [ ] Walk-forward validation framework
- [ ] Volatility-scaled position sizing
- [ ] Strategy correlation matrix
- [ ] Paper trading mode via Alpaca API
- [ ] Fix known issue #2 (holding days inefficient iteration)
- [ ] Fix known issue #16 (hardcoded database paths in visualizer)

## ✅ Recently Completed

_For context; clear periodically_

- [x] Project bootstrap (scope.md, roadmap v4, todo.md, archive old roadmap) — 2026-03-23
- [x] Full pipeline test with real Alpaca data (6,758 trades, 64/64 tests) — 2025-12-29
- [x] Phase 3 bug fixes (all 12 strategies generating trades) — 2025-12-29
- [x] Metrics accuracy audit (Sharpe/Sortino fix, slippage, look-ahead bias) — 2025-12-29
- [x] Monitoring system (FastAPI + Rich CLI + WebSocket) — 2025-12-28

---

## Notes

_Context or decisions affecting current tasks_

- Compute target is the skytracker server (skytracker-dev@155.31.130.52), not HPC
- Development may happen directly on the skytracker server — hold off on building orchestration/deployment scripts for now
- Previous work log archived at [docs/archive/worklog_2025-12-29.md](./archive/worklog_2025-12-29.md)

---

*Update every session: start by reading, end by updating.*
