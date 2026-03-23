# BearishVanish - Scope

> Last updated: 2026-03-23
> Status: Active

---

## Overview

BearishVanish is a quantitative trading simulation, analysis, and visualization platform. It backtests trading strategies against historical market data, computes 50+ performance metrics, and presents results through an interactive web dashboard. The platform is designed to eventually support live trading execution while maintaining modularity and separation from external AI/ML layers.

## Objectives

- Provide a robust backtesting engine for systematic trading strategies
- Compute comprehensive performance metrics (risk, drawdown, trade quality, monthly analysis)
- Visualize strategy performance through an interactive FastAPI web dashboard
- Support headless, server-based operation for automated simulation runs
- Achieve consistent 1% monthly returns (12%+ annually) with controlled risk
- Eventually support live trading execution via Alpaca API

## Requirements

### Functional Requirements

- [x] Bar-by-bar backtesting with no look-ahead bias
- [x] 12+ built-in trading strategies (momentum, mean reversion, trend following, breakout, etc.)
- [x] 8+ JIT-compiled indicators (VWAP, MFI, ADX, Supertrend, Ichimoku, etc.)
- [x] 50+ performance metrics (Sharpe, Sortino, Calmar, VaR, CVaR, Beta, Alpha, etc.)
- [x] Interactive web dashboard (FastAPI + Chart.js)
- [x] Report generation (markdown, PDF/HTML)
- [x] Offline mode with cached data
- [x] Parallel processing for multi-strategy/multi-symbol simulations
- [ ] Live trading execution via Alpaca API
- [ ] Full FastAPI-only visualization (remove matplotlib dependency)

### Technical Requirements

- [x] Python 3.9+
- [x] Numba JIT compilation for indicator performance (10-100x speedup)
- [x] SQLite with WAL mode for database performance
- [x] Alpaca API for market data and (future) trade execution
- [x] FastAPI for web dashboard and API layer
- [ ] Headless server operation without GUI dependencies
- [ ] Resource-aware execution on shared compute servers

### Resource Requirements

- [x] Alpaca API account (free tier sufficient for data)
- [x] Python environment with dependencies (requirements.txt)
- [ASSUMED] Compute server for simulation runs (skytracker-dev or local)
- [ASSUMED] No GPU required — CPU-based computation is sufficient

## Constraints

| Constraint | Reason | Flexible? |
|------------|--------|-----------|
| Alpaca API only (for now) | Established integration, free tier | Yes — could add other brokers later |
| Python only | Codebase is 25,000+ lines of Python | No |
| No paid cloud services | Budget/preference | No |
| No AI/ML in this repo | Separation of concerns — AI layer lives in external projects | Yes — may add ML strategies later, but modularly |
| Shared server resources | Skytracker server is a shared workstation | No — must be resource-aware |
| [VERIFIED] No HPC cluster access | Not approved for HPC use at this time | Yes — may change |

## Assumptions

- [VERIFIED] Alpaca API provides sufficient historical data for backtesting
- [VERIFIED] SQLite WAL mode handles concurrent simulation writes adequately
- [VERIFIED] Numba JIT provides sufficient performance for indicator computation
- [ASSUMED] Skytracker server (skytracker-dev@155.31.130.52) has adequate CPU for simulations
- [ASSUMED] Data caching on the server will reduce simulation startup time significantly

## Boundaries

### In Scope

- Backtesting engine (simulator)
- Performance analysis engine (50+ metrics)
- Web-based visualization dashboard (FastAPI)
- Report generation (markdown, PDF/HTML)
- Strategy development framework (base classes, indicators)
- Data management (download, cache, offline mode)
- Real-time monitoring system for simulation jobs
- Deployment scripts for remote server execution
- Live trading execution (future — Alpaca API)

### Out of Scope (Exclusions)

- **AI/ML research and inference** — handled by external projects (researchhub, cletus)
- **News monitoring and analysis** — handled by cletus
- **Academic paper discovery** — handled by researchhub
- **Orchestration layer** between BearishVanish and external AI projects — future work, separate concern
- **Broker integrations beyond Alpaca** — not planned currently
- **Mobile or desktop GUI** — web dashboard only
- **Real-time streaming market data** — batch/historical processing for now
- **Cryptocurrency or forex trading** — equities only for now

## Technical Decisions

| Decision | Choice | Rationale | Date |
|----------|--------|-----------|------|
| Backtesting engine | Custom Python + Numba | Full control, JIT performance | 2024-12 |
| Database | SQLite with WAL mode | Lightweight, portable, 15-90x write speedup | 2024-12 |
| Web framework | FastAPI | Async, fast, good API design, serves as both dashboard and API layer | 2024-12 |
| Frontend | Chart.js + vanilla JS | Lightweight, no build step needed | 2024-12 |
| Market data | Alpaca API | Free tier, good coverage, eventual live trading | 2024-12 |
| Indicators | Numba JIT compiled | 10-100x speedup over pure Python | 2024-12 |
| Compute target | Skytracker server (shared workstation) | Available SSH access, Xeon CPU | 2026-03 |

## Integration Points

- **Alpaca API** — market data download, future live trading execution
- **researchhub** (~/researchhub/) — academic research automation platform; potential future integration for strategy research insights
- **cletus** (~/cletus/) — news aggregation and intelligence reporting; potential future integration for news-driven trading signals
- **Skytracker server** (skytracker-dev@155.31.130.52) — remote compute for headless simulation runs

## Open Questions

- [ ] What does the live trading architecture look like? (paper trading first? safety limits?)
- [ ] How will strategy signals from ML models be consumed? (API? file-based? message queue?)
- [ ] What's the data retention policy for historical simulation results?
- [ ] Should the visualizer be accessible remotely on the skytracker server?

## Critical Notes

- **Development philosophy**: Sound statistical reasoning over curve-fitting. Accept lower backtested returns in exchange for higher confidence in future performance.
- **Shared server etiquette**: Skytracker server is shared — simulations must be resource-aware, wait for available resources, and release them promptly.
- **No unauthorized HPC usage**: HPC cluster access has not been approved for this project.

---

## Revision History

| Date | Changes | By |
|------|---------|-----|
| 2026-03-23 | Initial scope document created from project bootstrap | LLM |

---

*This document evolves as the project develops. Requirements, constraints, and boundaries can be added, modified, or removed as understanding improves. Major scope changes should be discussed with the user.*
