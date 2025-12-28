# BearishVanish

A production-grade quantitative trading simulation, analysis, and visualization platform.

## Overview

BearishVanish consists of three main components:

| Component | Description | Entry Point |
|-----------|-------------|-------------|
| **Simulator** | Backtests trading strategies on historical data | `simulator/main.py` |
| **Analysis** | Computes 50+ performance metrics | `analysis/analysis_engine.py` |
| **Visualizer** | Interactive web dashboard | `visualizer/main.py` |

## Quick Start

### 1. Setup Environment

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 2. Configure API Credentials

Create `.env` file:
```bash
ALPACA_API_KEY=your_api_key_here
ALPACA_SECRET_KEY=your_secret_key_here
```

### 3. Run Simulation

```bash
cd simulator

# Update universe and download data
python main.py --update-universe sp500
python main.py --download --universe sp500

# Run simulation
python main.py --universe sp500
```

### 4. Analyze Results

```bash
cd ../analysis
python analysis_engine.py --latest
```

### 5. View Dashboard

```bash
cd ../visualizer
python main.py
# Open http://localhost:8000
```

---

## Documentation

Comprehensive documentation is available in the `0_docs/` directory:

| Document | Description |
|----------|-------------|
| [PROJECT_DOCUMENTATION.md](0_docs/PROJECT_DOCUMENTATION.md) | Full architecture and API reference |
| [STRATEGY_DEVELOPMENT.md](0_docs/STRATEGY_DEVELOPMENT.md) | Guide to creating custom strategies |
| [ANALYSIS_METRICS.md](0_docs/ANALYSIS_METRICS.md) | All 50+ metrics explained |
| [HPC/README](hpc_scripts/README.md) | HPC cluster deployment guide |

---

## Features

- **High Performance**: Numba JIT compilation for 10-100x faster indicators
- **Parallel Processing**: Multi-core simulation across strategies and symbols
- **12 Built-in Strategies**: Momentum, mean reversion, breakout, and more
- **50+ Metrics**: Sharpe, Sortino, Calmar, VaR, CVaR, Alpha, Beta, etc.
- **Interactive Dashboard**: Equity curves, drawdowns, monthly heatmaps
- **HPC Ready**: Scripts for deploying to compute clusters

---

## Directory Structure

```
BearishVanish/
├── simulator/          # Backtesting engine
│   ├── strategies/     # Trading strategies
│   └── simulations/    # Output databases
├── analysis/           # Metrics calculation
│   └── analysis_dbs/   # Output databases
├── visualizer/         # Web dashboard
├── hpc_scripts/        # HPC deployment
└── 0_docs/             # Documentation
```

---

## HPC Deployment

For running simulations on HPC clusters:

```bash
# Sync to HPC (from local)
./hpc_scripts/sync_to_hpc.sh

# Run on HPC
ssh user@hpc
cd /path/to/BearishVanish
./hpc_scripts/run_full_pipeline.sh sp500

# Fetch results (from local)
./hpc_scripts/fetch_results.sh
```

See [hpc_scripts/README.md](hpc_scripts/README.md) for full instructions.

---

## Command Reference

### Simulator

```bash
python main.py --universe sp500      # Run simulation
python main.py --download --universe sp500  # Download data
python main.py --offline             # Use cached data only
python main.py --optimize            # Optimize system settings
python main.py --cache-status        # Show cache status
python main.py --update-universe sp500  # Update universe
```

### Analysis

```bash
python analysis_engine.py --latest   # Analyze latest simulation
python analysis_engine.py --sim <path>  # Analyze specific simulation
```

### Visualizer

```bash
python main.py                       # Start dashboard (port 8000)
uvicorn main:app --reload --port 8000  # Development mode
```

---

## Requirements

- Python 3.9+
- Alpaca API account (free paper trading)
- Dependencies in `requirements.txt`

For interactive plotting:
```bash
sudo apt-get update
sudo apt-get install python3-tk
```

---

## License

MIT License

---

## Original Notes

### Alpaca API Reference
> [Alpaca API Python Reference](https://pypi.org/project/alpaca-py/)

### Environment Cleanup

```bash
deactivate  # Exit venv

# View what would be deleted (except venv/)
git clean -xdn -e venv/

# Delete (except venv/)
git clean -xdf -e venv/
```

### Potential Errors

#### Wash Trade Detection
> "Order failed: potential wash trade detected. use complex orders alpaca"

[Reference](https://forum.alpaca.markets/t/apierror-potential-wash-trade-detected-use-complex-orders/13441/6)

The order is being rejected because it could result in a 'wash trade'. A wash trade is when one trades with oneself (buy order fills against one's sell order). The SEC looks very unfavorably on this.

Alpaca rejects any order where there is an existing open order on the opposite side. Your algo should be either increasing or decreasing a position, not doing both simultaneously.
