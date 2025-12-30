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

### 3. Download Market Data (One-Time)

**Best Practice**: Download all required data FIRST, then run simulations in offline mode.

```bash
cd simulator

# Update universe (get list of symbols)
python main.py --update-universe sp500

# Download 1 year of historical data (requires API keys)
python main.py --download --universe sp500

# Verify data completeness
python main.py --cache-status
```

### 4. Run Simulation (Offline Mode Recommended)

```bash
cd simulator

# Run with cached data (fast, no API calls)
python main.py --offline --universe sp500

# Or run with live API (slower, fills gaps)
python main.py --universe sp500
```

**Why Offline Mode?**
- Faster simulation startup (no network calls)
- Reproducible results with same data
- HPC cluster doesn't need API keys
- API calls happen once during download, not every simulation

### 5. Analyze Results

```bash
cd ../analysis
python analysis_engine.py --latest
```

### 6. View Dashboard

```bash
cd ../visualizer
python main.py
# Open http://localhost:8000
```

---

## Documentation

Comprehensive documentation is available in the `docs/` directory:

| Document | Description |
|----------|-------------|
| [PROJECT_ROADMAP.md](docs/PROJECT_ROADMAP.md) | Current status and future plans |
| [PROJECT_DOCUMENTATION.md](docs/PROJECT_DOCUMENTATION.md) | Full architecture and API reference |
| [STRATEGY_DEVELOPMENT.md](docs/STRATEGY_DEVELOPMENT.md) | Guide to creating custom strategies |
| [ANALYSIS_METRICS.md](docs/ANALYSIS_METRICS.md) | All 50+ metrics explained |
| [HPC/README](hpc_scripts/README.md) | HPC cluster deployment guide |
| [Findings/](docs/Findings/) | Implementation summaries and analysis |

---

## Features

- **High Performance**: Numba JIT compilation for 10-100x faster indicators
- **Parallel Processing**: Multi-core simulation across strategies and symbols
- **12 Built-in Strategies**: Momentum, mean reversion, breakout, and more
- **50+ Metrics**: Sharpe, Sortino, Calmar, VaR, CVaR, Alpha, Beta, etc.
- **Interactive Dashboard**: Equity curves, drawdowns, monthly heatmaps
- **HPC Ready**: Scripts for deploying to compute clusters

---

## Strategy Development Philosophy

**IMPORTANT**: This project prioritizes **sound statistical reasoning** over curve-fitting to historical data.

### Principles

1. **Generalization over Optimization**: Strategies should work on future unseen data, not just historical backtests. We avoid overfitting to specific time periods.

2. **Statistical Foundations**: All strategies are based on well-documented market phenomena:
   - Mean reversion (price returns to average)
   - Momentum (trends tend to persist)
   - Volume confirmation (institutions move prices)
   - Relative strength (outperformers continue outperforming)

3. **Robust Indicators**: We use indicators with theoretical backing:
   - RSI: Measures overbought/oversold conditions
   - Bollinger Bands: Measures price deviation from mean
   - VWAP: Institutional price benchmark
   - ADX: Trend strength measurement

4. **Simple Rules over Complex Models**: Simple strategies with few conditions are more likely to generalize. Complex strategies with many conditions tend to overfit.

5. **Walk-Forward Validation**: Test on data the strategy has never seen. Past performance does not guarantee future results.

### What We Don't Do

- ❌ Optimize parameters to maximize historical returns
- ❌ Add conditions just because they improved backtests
- ❌ Cherry-pick time periods that look good
- ❌ Use machine learning without proper validation

### What We Do

- ✅ Use established financial theory
- ✅ Keep strategies simple and interpretable
- ✅ Test on multiple time periods and market conditions
- ✅ Document the statistical reasoning behind each rule

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
# Step 1: Download data locally first (requires API keys)
cd simulator
python main.py --download --universe sp500
python main.py --cache-status  # Verify completeness

# Step 2: Sync to HPC (includes data in offline_data/)
./hpc_scripts/sync_to_hpc.sh

# Step 3: Run on HPC (uses offline mode - no API needed)
ssh user@hpc
cd /path/to/BearishVanish
./hpc_scripts/run_complete_pipeline.sh sp500 --offline

# Step 4: Fetch results (from local)
./hpc_scripts/fetch_results.sh
```

**Key Point**: The HPC cluster runs in `--offline` mode using the data you synced.
API keys are only needed on your local machine for the initial download.

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
