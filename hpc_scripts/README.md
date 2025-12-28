# HPC Scripts for BearishVanish

This directory contains scripts for running BearishVanish simulations and analysis on the HPC cluster.

## HPC Architecture

```
Local Machine
     |
     | SSH
     v
+------------------+
| vegaln1.erau.edu |  <-- Login Node (192 cores, 1.5TB RAM, Internet)
+------------------+
     |
     | Shared Filesystem (/home2/)
     v
+------------------+
| gpu01 / gpu02    |  <-- GPU Nodes (4x H100 80GB each, NO Internet)
+------------------+
```

**Note:** Trading simulations are CPU-bound and run on the login node. The GPU nodes are for deep learning workloads.

## Quick Start

### 1. Sync Project to HPC (from local machine)

```bash
# First time or after code changes
./hpc_scripts/sync_to_hpc.sh

# Preview what would be synced
./hpc_scripts/sync_to_hpc.sh --dry-run

# Sync only code (skip data/results)
./hpc_scripts/sync_to_hpc.sh --code
```

### 2. Run Simulation (on HPC)

```bash
# SSH to HPC
ssh nelsg10@vegaln1.erau.edu

# Navigate to project
cd /home2/nelsg10/BearishVanish

# Run S&P 500 simulation
./hpc_scripts/run_simulation.sh sp500

# Download data first, then simulate
./hpc_scripts/run_simulation.sh --download sp500

# Use only cached data (offline mode)
./hpc_scripts/run_simulation.sh sp500 --offline
```

### 3. Run Analysis (on HPC)

```bash
# Analyze the latest simulation
./hpc_scripts/run_analysis.sh

# Analyze a specific simulation
./hpc_scripts/run_analysis.sh --sim ../simulator/simulations/simulation_20241220.db
```

### 4. Run Full Pipeline (on HPC)

```bash
# Run simulation + analysis in one command
./hpc_scripts/run_full_pipeline.sh sp500
```

### 5. Fetch Results (from local machine)

```bash
# Fetch latest results
./hpc_scripts/fetch_results.sh

# Fetch all results
./hpc_scripts/fetch_results.sh --all

# Preview what would be fetched
./hpc_scripts/fetch_results.sh --dry-run
```

### 6. View Results (local machine)

```bash
cd visualizer
python main.py
# Open http://localhost:8000
```

## Script Reference

| Script | Run From | Description |
|--------|----------|-------------|
| `sync_to_hpc.sh` | Local | Sync project code to HPC |
| `run_simulation.sh` | HPC | Run trading simulation |
| `run_analysis.sh` | HPC | Analyze simulation results |
| `run_full_pipeline.sh` | HPC | Run simulation + analysis |
| `fetch_results.sh` | Local | Download results from HPC |

## One-Liner Workflows

### Complete workflow from local machine:

```bash
# Sync, run everything on HPC, and fetch results
./hpc_scripts/sync_to_hpc.sh && \
ssh nelsg10@vegaln1.erau.edu "cd /home2/nelsg10/BearishVanish && ./hpc_scripts/run_full_pipeline.sh sp500" && \
./hpc_scripts/fetch_results.sh
```

### Background HPC job:

```bash
# Start on HPC and disconnect (job continues running)
ssh nelsg10@vegaln1.erau.edu \
  "cd /home2/nelsg10/BearishVanish && nohup ./hpc_scripts/run_full_pipeline.sh sp500 > hpc_output.log 2>&1 &"

# Check status later
ssh nelsg10@vegaln1.erau.edu "tail -f /home2/nelsg10/BearishVanish/hpc_output.log"
```

## Universes

| Universe | Symbols | Description |
|----------|---------|-------------|
| `sp500` | ~500 | S&P 500 stocks |
| `nasdaq100` | ~100 | NASDAQ 100 stocks |
| `dow30` | ~30 | Dow Jones 30 stocks |
| `custom` | varies | Custom ticker list |

## Troubleshooting

### SSH Connection Issues

```bash
# Test connection
ssh nelsg10@vegaln1.erau.edu "echo 'Connected!'"

# If using SSH key, ensure it's loaded
ssh-add ~/.ssh/id_rsa
```

### Dependencies Not Installing

```bash
# On HPC, manually set up environment
cd /home2/nelsg10/BearishVanish
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### Simulation Failing

```bash
# Check if data is cached
ls -la simulator/cache/

# Download fresh data
./hpc_scripts/run_simulation.sh --download sp500

# Run in offline mode with existing cache
./hpc_scripts/run_simulation.sh sp500 --offline
```

## Performance Tips

1. **Use offline mode** when data is already cached to avoid API rate limits
2. **The login node has 192 cores** - simulations parallelize across all cores
3. **Shared filesystem** means no need to copy data between nodes
4. **Run long jobs with nohup** so they continue after SSH disconnect
