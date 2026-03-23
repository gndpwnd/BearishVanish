# BearishVanish - Roadmap v4

> Last updated: 2026-03-23
> Previous roadmap: [roadmap_v3_2025-12-29](./archive/roadmap_v3_2025-12-29.md)
> For context on completed features, see the archived roadmap.

## Overview

This roadmap tracks project-level features and milestones. For immediate tasks, see [todo.md](./todo.md).

**Note**: No time estimates. Focus on WHAT needs to be done, not WHEN.

---

## Core Features

### Visualization & API Layer

- [ ] Remove matplotlib dependency — full FastAPI-only visualization
  - Description: Eliminate matplotlib/backend GUI deps; all charts rendered client-side via Chart.js
  - Dependencies: Verify all report generation paths use FastAPI endpoints, not matplotlib
  - Related findings: Visualizer already has Chart.js dashboard; need to audit remaining matplotlib usage

- [ ] Remote-accessible dashboard
  - Description: Run the FastAPI visualizer on a server and access it remotely
  - Dependencies: CORS configuration, authentication considerations

### Strategy Development

- [ ] Volume confirmation for entry signals
  - Description: Require volume >= 1.2-1.5x 20-day average for trade entries
  - Status: Documented in v3 roadmap, implementation pending

- [ ] Walk-forward validation framework
  - Description: Out-of-sample testing to detect overfitting
  - Dependencies: None
  - Related findings: See [v3 roadmap](./archive/roadmap_v3_2025-12-29.md#phase-5-analysis-improvements)

- [ ] Dynamic parameters (volatility-adaptive)
  - Description: Auto-adjust strategy parameters based on realized volatility
  - Dependencies: Regime detection

### Risk Management

- [ ] Volatility-scaled position sizing
  - Description: `volatility_scaled_position(target_vol, realized_vol, base_size)`
  - See [v3 roadmap](./archive/roadmap_v3_2025-12-29.md#phase-2-risk-management-next-priority) for full spec

- [ ] Portfolio heat control
  - Description: `calculate_portfolio_heat(positions, stops)` — aggregate risk exposure tracking

- [ ] Enhanced regime detection
  - Description: Classify market into BULL_LOW_VOL, BULL_HIGH_VOL, BEAR, TRANSITION
  - Dependencies: SPY data availability

### New Indicators (carry-forward)

- [ ] Rate of Change (ROC)
- [ ] Relative Strength vs SPY
- [ ] Market Breadth (% stocks > 50-day MA)
- [ ] Trend Strength Index (composite: ADX + MA slope + momentum)
- [ ] Volume-Confirmed Momentum (RSI + Volume)

### Analysis Improvements (carry-forward)

- [ ] Strategy correlation matrix
- [ ] Regime-specific performance breakdown
- [ ] Entry/exit quality scoring
- [ ] Trade attribution (decompose P&L into factors)
- [ ] Sector exposure analysis

### Live Trading (Future)

- [ ] Paper trading mode via Alpaca API
  - Description: Execute simulated trades through Alpaca's paper trading endpoint
  - Dependencies: Strategy signal generation in real-time, position management

- [ ] Live trading execution
  - Description: Real money execution with safety limits, position sizing, and kill switches
  - Dependencies: Paper trading validation, risk management framework

- [ ] Real-time position monitoring
  - Description: Track open positions, P&L, exposure in real-time

---

## Infrastructure / Setup

- [x] Core simulation engine (Numba JIT, parallel processing, WAL mode) ✓
- [x] Analysis engine (50+ metrics, all calculator modules) ✓
- [x] FastAPI web dashboard with Chart.js ✓
- [x] Monitoring system (FastAPI server, Rich CLI, WebSocket) ✓
- [x] Automated testing pipeline (run_strategy_test.py) ✓
- [x] 64 pytest tests passing ✓
- [ ] Data download monitoring (progress tracking during market data downloads)
- [ ] Headless server operation validation (confirm no GUI deps remain)

---

## Known Issues (carry-forward)

> See [v3 roadmap](./archive/roadmap_v3_2025-12-29.md#known-issues) for full details.

| ID | Severity | Description | Component |
|----|----------|-------------|-----------|
| #2 | MEDIUM | Holding days inefficient iteration | simulator.py |
| #3 | MEDIUM | Missing FIFO cost basis tracking | strategy_tracker.py |
| #6 | MEDIUM | Volume metrics not initialized for short data | simulator.py |
| #7 | MEDIUM | Parallel processing pickle risk | simulator.py |
| #11 | MEDIUM | Drawdown edge cases (no recovery) | drawdown_metrics.py |
| #14 | MEDIUM | Volatility annualization error | risk_metrics.py |
| #16 | MEDIUM | Hardcoded database paths | routers/trades.py |
| #21 | LOW | CORS too permissive | visualizer/main.py |

---

## Nice to Have (Lower Priority)

- [ ] Chart caching (pre-computed chart_cache table)
- [ ] Response caching for expensive API queries
- [ ] Trade pagination in dashboard
- [ ] UTF-8 CSV export for international tickers
- [ ] Process management via monitoring API (pause/resume/kill)
- [ ] Alert notifications (email/Slack on completion/failure)
- [ ] Monitoring web dashboard (HTML/JS alternative to Rich CLI)
- [ ] Monitoring authentication and rate limiting
- [ ] Report comparison across test runs (regression detection)

---

## Completed

> For full history of completed features, see [archived roadmap v3](./archive/roadmap_v3_2025-12-29.md#completed-features).

### Highlights
- [x] 12 trading strategies — all generating trades, all profitable in 1-year backtest
- [x] 8+ Numba JIT-compiled indicators
- [x] 50+ performance metrics with accuracy audit
- [x] FastAPI web dashboard with Chart.js visualizations
- [x] Real-time monitoring system (FastAPI + Rich CLI + WebSocket)
- [x] HPC deployment scripts and complete pipeline automation
- [x] 64 pytest tests (100% pass rate)
- [x] Strategy improvements: stop-losses, trailing stops, regime filters, ATR/ADX
- [x] Metrics accuracy audit: Sharpe/Sortino annualization, slippage, look-ahead bias verification
- [x] 1-year real data backtest: 6,758 trades, all 12 strategies profitable

---

## Notes

- **Development philosophy**: Sound statistical reasoning over curve-fitting. See [scope.md](./scope.md) for full boundaries.
- **Compute target**: Transitioning from HPC to skytracker server (shared workstation). Orchestration scripts may be updated accordingly.
- **External integrations**: researchhub (research) and cletus (news) are separate projects that may integrate via a future orchestration layer — not part of this roadmap.

---

*Update as features complete. Check boxes when done. Add new features as they're identified.*
