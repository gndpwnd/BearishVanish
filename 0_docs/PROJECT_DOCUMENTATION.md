# BearishVanish - Comprehensive Project Documentation

A production-grade quantitative trading simulation, analysis, and visualization platform.

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Component 1: Simulation Engine](#component-1-simulation-engine)
4. [Component 2: Analysis Engine](#component-2-analysis-engine)
5. [Component 3: Visualizer App](#component-3-visualizer-app)
6. [Data Flow](#data-flow)
7. [Quick Start Guide](#quick-start-guide)
8. [Configuration](#configuration)
9. [Performance Optimizations](#performance-optimizations)
10. [HPC Deployment](#hpc-deployment)
11. [API Reference](#api-reference)
12. [Strategy Development Guide](#strategy-development-guide)

---

## Overview

**BearishVanish** is a comprehensive stock trading strategy backtesting and analysis platform consisting of three main components:

| Component | Purpose | Technology |
|-----------|---------|------------|
| **Simulation Engine** | Backtests trading strategies on historical data | Python, Numba JIT, SQLite |
| **Analysis Engine** | Computes 50+ performance metrics | Python, NumPy, Pandas |
| **Visualizer App** | Interactive web dashboard | FastAPI, React, Chart.js |

### Key Features

- **High Performance**: Numba JIT compilation for 10-100x faster indicator calculations
- **Parallel Processing**: Multi-core simulation using ProcessPoolExecutor
- **Modular Strategies**: Plugin architecture for easy strategy development
- **Comprehensive Metrics**: 50+ performance indicators (Sharpe, Sortino, Calmar, etc.)
- **Interactive Dashboard**: Real-time visualization with equity curves, drawdowns, monthly returns
- **HPC Ready**: Scripts for deploying to high-performance computing clusters

### Codebase Statistics

- **Total Lines**: ~20,880 lines of Python
- **Strategies**: 10+ built-in trading strategies
- **Metrics**: 50+ calculated performance indicators
- **Universes**: S&P 500, NASDAQ 100, Dow 30, custom

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    SIMULATOR                             │
│  main.py -> simulator.py -> strategies -> indicators     │
│  Data: Alpaca API / CSV cache                            │
│  Output: simulation_TIMESTAMP_ID.db                      │
└──────────────────┬──────────────────────────────────────┘
                   │
                   ▼ (raw trade data)
┌─────────────────────────────────────────────────────────┐
│                  ANALYSIS ENGINE                         │
│  analysis_engine.py -> Calculators -> Pre-computed       │
│  Reads: simulation_*.db                                  │
│  Output: analysis_TIMESTAMP_ID.db                        │
└──────────────────┬──────────────────────────────────────┘
                   │
                   ▼ (pre-computed metrics)
┌─────────────────────────────────────────────────────────┐
│                  VISUALIZER (FastAPI)                    │
│  main.py -> Routers -> AnalysisReader                    │
│  Reads: analysis_*.db                                    │
│  Frontend: React + Chart.js (http://localhost:8000)      │
└─────────────────────────────────────────────────────────┘
```

### Directory Structure

```
BearishVanish/
├── simulator/                    # Backtesting engine
│   ├── main.py                   # Entry point
│   ├── simulator.py              # Core simulation loop
│   ├── strategy_base.py          # Strategy base class
│   ├── data_manager.py           # Data fetching/caching
│   ├── stock_universe.py         # Universe management
│   ├── indicator_base.py         # JIT-compiled indicators
│   ├── simulation_telemetry.py   # Database recording
│   ├── strategies/               # Trading strategies
│   ├── indicators/               # Custom indicators
│   ├── optimization/             # Performance tools
│   ├── tests/                    # Unit tests
│   └── simulations/              # Output databases
│
├── analysis/                     # Metric calculation engine
│   ├── analysis_engine.py        # Orchestrator
│   ├── db_reader.py              # Simulation DB reader
│   ├── analysis_db_schema.py     # Database schema
│   ├── calculators/              # Metric calculators
│   │   ├── trade_metrics.py
│   │   ├── risk_metrics.py
│   │   ├── drawdown_metrics.py
│   │   ├── streak_metrics.py
│   │   ├── monthly_metrics.py
│   │   └── volume_metrics.py
│   ├── processors/               # Data processors
│   ├── analysis_dbs/             # Output databases
│   └── utilities/                # UTF-8 helpers
│
├── visualizer/                   # Web dashboard
│   ├── main.py                   # FastAPI app
│   ├── config.py                 # Configuration
│   ├── routers/                  # API endpoints
│   │   ├── strategies.py
│   │   ├── trades.py
│   │   ├── charts.py
│   │   ├── analyses.py
│   │   ├── comparison.py
│   │   └── reports.py
│   ├── database/                 # DB readers
│   ├── models/                   # Pydantic models
│   ├── static/                   # Frontend assets
│   └── templates/                # HTML templates
│
├── hpc_scripts/                  # HPC deployment scripts
│   ├── sync_to_hpc.sh
│   ├── run_simulation.sh
│   ├── run_analysis.sh
│   ├── run_full_pipeline.sh
│   ├── fetch_results.sh
│   └── README.md
│
├── 0_docs/                       # Documentation
│   └── HPC/                      # HPC guides
│
├── requirements.txt              # Python dependencies
└── .env.txt                      # API credentials
```

---

## Component 1: Simulation Engine

### Location
`/simulator/`

### Purpose
Backtest trading strategies on historical market data using bar-by-bar simulation with no look-ahead bias.

### Key Files

| File | Description |
|------|-------------|
| `main.py` | CLI entry point, argument parsing |
| `simulator.py` | Core simulation loop, parallel processing |
| `strategy_base.py` | Abstract base class for strategies |
| `data_manager.py` | Alpaca API integration, caching |
| `stock_universe.py` | Universe management (S&P 500, etc.) |
| `indicator_base.py` | Numba JIT-compiled indicators |
| `simulation_telemetry.py` | Database recording |

### Command Line Interface

```bash
cd simulator

# Run simulation on S&P 500
python main.py --universe sp500

# Download data first
python main.py --download --universe sp500

# Offline mode (use cached data only)
python main.py --universe sp500 --offline

# Force liquidate at end
python main.py --universe sp500 --force-liquidate

# Run system optimization
python main.py --optimize

# Check cache status
python main.py --cache-status

# Update universe
python main.py --update-universe sp500
```

### Simulation Database Schema

```sql
-- Simulation metadata
CREATE TABLE simulation_info (
    simulation_id TEXT,
    start_date TEXT,
    end_date TEXT,
    universe TEXT,
    num_symbols INTEGER
);

-- Per-strategy performance
CREATE TABLE strategy_performance (
    strategy_name TEXT PRIMARY KEY,
    initial_capital REAL,
    final_value REAL,
    total_return_pct REAL,
    total_trades INTEGER,
    winning_trades INTEGER,
    losing_trades INTEGER
);

-- All trades with full details
CREATE TABLE trade_history (
    id INTEGER PRIMARY KEY,
    strategy_name TEXT,
    symbol TEXT,
    entry_date TEXT,
    entry_price REAL,
    exit_date TEXT,
    exit_price REAL,
    shares INTEGER,
    profit_loss REAL,
    profit_loss_pct REAL,
    hold_days INTEGER,
    entry_relative_volume REAL,
    exit_relative_volume REAL
);

-- Daily portfolio values
CREATE TABLE portfolio_history (
    strategy_name TEXT,
    date TEXT,
    portfolio_value REAL,
    cash REAL,
    positions_value REAL
);
```

### Built-in Strategies

| Strategy | File | Description |
|----------|------|-------------|
| S&P 500 Intersection | `strategy_500_intersection.py` | Crossover detection |
| WAM | `strategy_WAM.py` | Weekly threshold strategy |
| Momentum MFI | `strategy_momentum_mfi.py` | Money Flow Index based |
| Momentum Example | `strategy_momentum_example.py` | Basic momentum |
| Mean Reversion | `strategy_mean_reversion.py` | RSI oversold/overbought |
| Breakout | `strategy_breakout.py` | Price breakout signals |
| Trend Following | `strategy_trend_following.py` | Trend-based entries |
| Conservative Income | `strategy_conservative_income.py` | Low-risk approach |
| AMIS | `strategy_AMIS.py` | Advanced momentum |
| S&P 500 Slope V2 | `strategy_sp500_slope_v2.py` | Slope analysis |
| Rolling Windows | `strategy_rolling_windows.py` | Window-based signals |
| Monthly Rolling | `strategy_monthly_rolling.py` | Monthly rebalancing |

---

## Component 2: Analysis Engine

### Location
`/analysis/`

### Purpose
Compute comprehensive performance metrics from simulation results and pre-process data for visualization.

### Key Files

| File | Description |
|------|-------------|
| `analysis_engine.py` | Main orchestrator |
| `db_reader.py` | Reads simulation database |
| `analysis_db_schema.py` | Creates analysis tables |

### Calculators

Located in `analysis/calculators/`:

| Calculator | Metrics Computed |
|------------|------------------|
| `trade_metrics.py` | Win rate, profit factor, expectancy, hold time |
| `risk_metrics.py` | Sharpe, Sortino, Calmar, VaR, CVaR, Beta, Alpha |
| `drawdown_metrics.py` | Max drawdown, recovery time, drawdown periods |
| `streak_metrics.py` | Win/loss streaks, current streak |
| `monthly_metrics.py` | Monthly returns, seasonal patterns |
| `volume_metrics.py` | Entry/exit volume analysis |

### Command Line Interface

```bash
cd analysis

# Analyze latest simulation
python analysis_engine.py --latest

# Analyze specific simulation
python analysis_engine.py --sim ../simulator/simulations/simulation_20241220.db
```

### Analysis Database Schema

```sql
-- Comprehensive strategy metrics (50+ columns)
CREATE TABLE strategy_summary (
    strategy_name TEXT PRIMARY KEY,

    -- Performance
    total_return_pct REAL,
    total_profit_dollars REAL,
    unrealized_pnl REAL,
    annualized_return_pct REAL,

    -- Trade Statistics
    total_trades INTEGER,
    completed_trades INTEGER,
    open_positions INTEGER,
    winning_trades INTEGER,
    losing_trades INTEGER,
    win_rate_pct REAL,

    -- Profit Metrics
    gross_profit REAL,
    gross_loss REAL,
    profit_factor REAL,
    avg_win_dollars REAL,
    avg_loss_dollars REAL,
    risk_reward_ratio REAL,
    expectancy_dollars REAL,

    -- Risk Metrics
    sharpe_ratio REAL,
    sortino_ratio REAL,
    calmar_ratio REAL,
    omega_ratio REAL,
    max_drawdown_pct REAL,
    max_drawdown_dollars REAL,
    avg_drawdown_pct REAL,
    volatility_annual_pct REAL,
    downside_deviation_pct REAL,

    -- Value at Risk
    var_95_pct REAL,
    cvar_95_pct REAL,

    -- Market Exposure
    beta REAL,
    alpha_pct REAL,
    correlation REAL,
    information_ratio REAL,
    treynor_ratio REAL,

    -- Holding Period
    avg_hold_days REAL,
    max_hold_days INTEGER,
    min_hold_days INTEGER,

    -- Streaks
    max_win_streak INTEGER,
    max_loss_streak INTEGER,
    current_streak INTEGER
);

-- Monthly returns for heatmaps
CREATE TABLE monthly_returns (
    strategy_name TEXT,
    year_month TEXT,
    return_pct REAL,
    num_trades INTEGER,
    win_rate_pct REAL
);

-- Drawdown periods
CREATE TABLE drawdown_periods (
    strategy_name TEXT,
    peak_date TEXT,
    trough_date TEXT,
    recovery_date TEXT,
    drawdown_pct REAL,
    drawdown_dollars REAL,
    recovery_days INTEGER,
    duration_days INTEGER
);

-- Pre-computed chart data
CREATE TABLE chart_cache (
    chart_id TEXT PRIMARY KEY,
    strategy_name TEXT,
    chart_type TEXT,
    chart_data TEXT,  -- JSON
    computed_timestamp INTEGER
);
```

---

## Component 3: Visualizer App

### Location
`/visualizer/`

### Purpose
Interactive web dashboard for exploring simulation results and comparing strategies.

### Technology Stack

- **Backend**: FastAPI, Uvicorn
- **Frontend**: React (CDN), Chart.js
- **Database**: SQLite (reads analysis database)

### Starting the Dashboard

```bash
cd visualizer

# Development mode with auto-reload
python main.py

# Or using uvicorn directly
uvicorn main:app --reload --port 8000

# Open browser
# http://localhost:8000
```

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/strategies` | GET | List all strategies with summary metrics |
| `/api/strategies/{name}` | GET | Detailed metrics for one strategy |
| `/api/trades` | GET | Trade history with filtering |
| `/api/trades/{strategy}` | GET | Trades for specific strategy |
| `/api/charts/{strategy}/{type}` | GET | Chart data (equity, drawdown, etc.) |
| `/api/analyses` | GET | List available analysis databases |
| `/api/analyses/{id}/switch` | POST | Switch to different analysis |
| `/api/comparison` | GET | Side-by-side strategy comparison |
| `/api/reports/{strategy}` | GET | Generate PDF report |

### Frontend Components

| Component | File | Purpose |
|-----------|------|---------|
| App | `static/js/app.js` | Main dashboard shell |
| Core | `static/js/core.js` | API client, utilities |
| Dashboard | `static/js/dashboard.js` | Overview view |
| Charts | `static/js/charts.js` | Equity curves, drawdowns |
| Trades | `static/js/trades.js` | Trade list, details |
| Comparison | `static/js/comparison.js` | Strategy comparison |
| Components | `static/js/components.js` | Reusable UI elements |

---

## Data Flow

### Complete Pipeline

```
1. DATA ACQUISITION
   Alpaca API -> DataManager -> stock_data.db (cache)

2. SIMULATION
   Strategies + Indicators -> Bar-by-bar processing
   Output: simulation_YYYYMMDD_HHMMSS_ID.db

3. ANALYSIS
   SimulationReader -> Calculators -> Metrics
   Output: analysis_YYYYMMDD_HHMMSS_ID.db

4. VISUALIZATION
   AnalysisReader -> FastAPI -> React Dashboard
   Browser: http://localhost:8000
```

### Database Files

```
simulator/
└── simulations/
    └── simulation_20241220_143022_sp500.db

analysis/
└── analysis_dbs/
    └── analysis_20241220_143122_sp500.db
```

---

## Quick Start Guide

### Prerequisites

```bash
# Python 3.9+
python --version

# Install dependencies
pip install -r requirements.txt
```

### 1. Configure API Credentials

Edit `.env.txt`:
```
ALPACA_API_KEY=your_api_key
ALPACA_SECRET_KEY=your_secret_key
```

### 2. Run Simulation

```bash
cd simulator

# First time: download data and update universe
python main.py --update-universe sp500
python main.py --download --universe sp500

# Run simulation
python main.py --universe sp500
```

### 3. Run Analysis

```bash
cd ../analysis

# Analyze latest simulation
python analysis_engine.py --latest
```

### 4. View Dashboard

```bash
cd ../visualizer

# Start server
python main.py

# Open http://localhost:8000 in browser
```

---

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ALPACA_API_KEY` | Alpaca API key | Required |
| `ALPACA_SECRET_KEY` | Alpaca secret key | Required |

### Strategy Configuration

Each strategy can be configured in its constructor:

```python
config = StrategyConfig(
    name="My Strategy",
    color="#FF6B6B",
    initial_capital=100000,
    position_size_pct=0.10,  # 10% per position
    max_positions=10,
    verbose=False
)
```

---

## Performance Optimizations

### Numba JIT Compilation

Indicators are compiled with Numba for 10-100x speedup:

```python
from indicator_base import calculate_sma, calculate_rsi

# These are Numba-accelerated
sma = calculate_sma(df, period=20, use_numba=True)
rsi = calculate_rsi(df, period=14, use_numba=True)
```

### Pre-computation

Indicators are calculated once per symbol, then reused:

```python
# Computed once for AAPL
indicators = {
    'sma_20': [...],
    'rsi_14': [...],
    'macd': [...],
}

# Reused across all strategies
for strategy in strategies:
    strategy.set_indicators(indicators)
```

### Parallel Processing

Simulations run in parallel across CPU cores:

```python
from concurrent.futures import ProcessPoolExecutor

with ProcessPoolExecutor(max_workers=cpu_count()) as executor:
    futures = [executor.submit(simulate, strategy, symbol)
               for strategy, symbol in combinations]
```

### Batch Database Operations

Trades are buffered and committed in batches:

```python
# Buffer trades
telemetry.buffer_trade(trade_data)

# Commit every 1000 trades
if len(buffer) >= 1000:
    telemetry.flush()
```

---

## HPC Deployment

See [hpc_scripts/README.md](../hpc_scripts/README.md) for detailed HPC deployment instructions.

### Quick HPC Workflow

```bash
# 1. Sync to HPC (from local machine)
./hpc_scripts/sync_to_hpc.sh

# 2. Run simulation (on HPC)
ssh nelsg10@vegaln1.erau.edu
cd /home2/nelsg10/BearishVanish
./hpc_scripts/run_full_pipeline.sh sp500

# 3. Fetch results (from local machine)
./hpc_scripts/fetch_results.sh

# 4. View results locally
cd visualizer && python main.py
```

---

## API Reference

### Strategies Endpoint

**GET /api/strategies**

Returns all strategies with summary metrics:

```json
{
  "strategies": [
    {
      "name": "Momentum Mfi",
      "total_return_pct": 15.3,
      "sharpe_ratio": 1.2,
      "max_drawdown_pct": -8.5,
      "win_rate_pct": 55.0,
      "total_trades": 150
    }
  ]
}
```

### Trades Endpoint

**GET /api/trades/{strategy}**

Returns trade history:

```json
{
  "trades": [
    {
      "id": 1,
      "symbol": "AAPL",
      "entry_date": "2024-01-15",
      "entry_price": 185.50,
      "exit_date": "2024-01-22",
      "exit_price": 192.30,
      "profit_loss_pct": 3.67,
      "hold_days": 7
    }
  ]
}
```

### Charts Endpoint

**GET /api/charts/{strategy}/equity_curve**

Returns equity curve data:

```json
{
  "labels": ["2024-01-01", "2024-01-02", ...],
  "datasets": [
    {
      "label": "Portfolio Value",
      "data": [100000, 100500, ...]
    }
  ]
}
```

---

## Strategy Development Guide

### Creating a New Strategy

1. Create file in `simulator/strategies/strategy_my_strategy.py`:

```python
from strategy_base import StrategyBase, StrategyConfig

class Strategy(StrategyBase):
    """My custom trading strategy"""

    def __init__(self, config=None):
        super().__init__(config)
        # Custom initialization

    def next_bar(self, date, row, portfolio):
        """
        Called for each bar in the simulation.

        Args:
            date: Current date
            row: DataFrame row with OHLCV + indicators
            portfolio: Current portfolio state

        Returns:
            Signal: 'BUY', 'SELL', or None
        """
        # Access pre-computed indicators
        sma_20 = row.get('sma_20')
        rsi = row.get('rsi_14')

        # Entry logic
        if rsi < 30 and row['close'] > sma_20:
            return 'BUY'

        # Exit logic
        if rsi > 70:
            return 'SELL'

        return None
```

2. The strategy is automatically discovered and loaded.

### Available Indicators

Pre-computed indicators available in `row`:

| Indicator | Key | Description |
|-----------|-----|-------------|
| SMA | `sma_{period}` | Simple Moving Average |
| EMA | `ema_{period}` | Exponential Moving Average |
| RSI | `rsi_{period}` | Relative Strength Index |
| MACD | `macd`, `macd_signal`, `macd_hist` | MACD Indicator |
| Bollinger | `bb_upper`, `bb_lower`, `bb_middle` | Bollinger Bands |
| ATR | `atr_{period}` | Average True Range |
| Volume | `volume_sma`, `relative_volume` | Volume indicators |

### Strategy Best Practices

1. **No Look-Ahead Bias**: Only use data up to current bar
2. **Position Sizing**: Use `config.position_size_pct` for risk management
3. **Max Positions**: Respect `config.max_positions` limit
4. **Logging**: Use `self.log()` for debugging (disabled in parallel mode)
5. **Error Handling**: Handle missing indicator data gracefully

---

## License

MIT License - See LICENSE file for details.

## Contributing

1. Fork the repository
2. Create feature branch
3. Add tests for new functionality
4. Submit pull request

## Support

For issues and questions, open a GitHub issue or contact the maintainers.
