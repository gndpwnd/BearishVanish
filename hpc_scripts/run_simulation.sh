#!/bin/bash
# ============================================================================
# BearishVanish - Run Simulation on HPC
# ============================================================================
# This script runs the simulation engine on the HPC login node.
# Since trading simulations are CPU-bound (not GPU), they run on the login node
# which has 192 cores and 1.5TB RAM - more than enough for parallel processing.
#
# Usage (run on HPC):
#   ./run_simulation.sh sp500        # Run S&P 500 simulation
#   ./run_simulation.sh sp500 --offline  # Use cached data only
#   ./run_simulation.sh --download sp500  # Download data first
# ============================================================================

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "${SCRIPT_DIR}")"
SIMULATOR_DIR="${PROJECT_DIR}/simulator"
VENV_DIR="${PROJECT_DIR}/venv"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${BLUE}============================================================${NC}"
echo -e "${BLUE}BearishVanish - HPC Simulation Runner${NC}"
echo -e "${BLUE}============================================================${NC}"
echo ""
echo -e "Project:  ${PROJECT_DIR}"
echo -e "Hostname: $(hostname)"
echo -e "Date:     $(date)"
echo ""

# Check if we're on the HPC
if [[ ! "$(hostname)" =~ (vegaln|gpu) ]]; then
    echo -e "${YELLOW}Warning: Not running on HPC cluster${NC}"
    echo "This script is designed to run on vegaln1.erau.edu"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Load Python module on HPC (has proper ctypes support)
if [[ "$(hostname)" =~ (vegaln|gpu) ]]; then
    echo -e "${CYAN}Loading Python module...${NC}"
    source /etc/profile.d/modules.sh 2>/dev/null || true
    module load python/3.11.7-gcc-8.5.0-wfpoppf 2>/dev/null || true
fi

# Ensure virtual environment exists
if [ ! -d "${VENV_DIR}" ]; then
    echo -e "${YELLOW}Creating Python virtual environment...${NC}"
    python3 -m venv "${VENV_DIR}"
fi

# Activate virtual environment
echo -e "${CYAN}Activating virtual environment...${NC}"
source "${VENV_DIR}/bin/activate"

# Check/install dependencies
if [ ! -f "${VENV_DIR}/.deps_installed" ]; then
    echo -e "${YELLOW}Installing Python dependencies...${NC}"
    pip install --upgrade pip
    pip install -r "${PROJECT_DIR}/requirements.txt"
    touch "${VENV_DIR}/.deps_installed"
    echo -e "${GREEN}Dependencies installed${NC}"
fi

# Parse arguments
UNIVERSE="sp500"
EXTRA_ARGS=""
DOWNLOAD_FIRST=""
SIM_WORKERS=""

for arg in "$@"; do
    case $arg in
        sp500|nasdaq100|dow30|custom)
            UNIVERSE="$arg"
            ;;
        --download)
            DOWNLOAD_FIRST="true"
            ;;
        --offline)
            EXTRA_ARGS+=" --offline"
            ;;
        --force-liquidate)
            EXTRA_ARGS+=" --force-liquidate"
            ;;
        --optimize)
            EXTRA_ARGS+=" --optimize"
            ;;
        --sim-workers=*)
            SIM_WORKERS="${arg#*=}"
            ;;
        --help)
            echo "Usage: $0 [UNIVERSE] [OPTIONS]"
            echo ""
            echo "Universe (default: sp500):"
            echo "  sp500       S&P 500 stocks (~500 symbols)"
            echo "  nasdaq100   NASDAQ 100 stocks (~100 symbols)"
            echo "  dow30       Dow Jones 30 stocks (~30 symbols)"
            echo "  custom      Custom tickers (set via --tickers)"
            echo ""
            echo "Options:"
            echo "  --download          Download data before simulation"
            echo "  --offline           Use cached data only (no API calls)"
            echo "  --force-liquidate   Force liquidate all positions at end"
            echo "  --optimize          Run system optimization first"
            echo "  --sim-workers=N     Number of parallel workers (default: 48 for HPC)"
            echo ""
            exit 0
            ;;
        *)
            EXTRA_ARGS+=" $arg"
            ;;
    esac
done

# Set default sim-workers for HPC (48-96 recommended for 192 cores)
if [ -z "$SIM_WORKERS" ]; then
    # Auto-detect HPC and set appropriate workers
    TOTAL_CORES=$(nproc)
    if [ "$TOTAL_CORES" -gt 64 ]; then
        SIM_WORKERS=48  # HPC with 192 cores - use 48 to balance memory/CPU
    else
        SIM_WORKERS=$((TOTAL_CORES - 2))  # Regular machine
    fi
fi
EXTRA_ARGS+=" --sim-workers ${SIM_WORKERS}"

# Change to simulator directory
cd "${SIMULATOR_DIR}"

# Download data if requested
if [ "$DOWNLOAD_FIRST" == "true" ]; then
    echo -e "${CYAN}============================================================${NC}"
    echo -e "${CYAN}Downloading market data...${NC}"
    echo -e "${CYAN}============================================================${NC}"
    python main.py --download --universe "${UNIVERSE}"
    echo ""
fi

# Show system info
echo -e "${CYAN}============================================================${NC}"
echo -e "${CYAN}System Information${NC}"
echo -e "${CYAN}============================================================${NC}"
echo -e "CPU Cores:    $(nproc)"
echo -e "Sim Workers:  ${SIM_WORKERS}"
echo -e "Memory:       $(free -h | awk '/^Mem:/ {print $2}')"
echo -e "Python:       $(python --version)"
echo -e "Universe:     ${UNIVERSE}"
echo ""

# Run simulation
echo -e "${GREEN}============================================================${NC}"
echo -e "${GREEN}Starting Simulation${NC}"
echo -e "${GREEN}============================================================${NC}"
echo ""

START_TIME=$(date +%s)

python main.py --universe "${UNIVERSE}" ${EXTRA_ARGS}

END_TIME=$(date +%s)
ELAPSED=$((END_TIME - START_TIME))

echo ""
echo -e "${GREEN}============================================================${NC}"
echo -e "${GREEN}Simulation Complete!${NC}"
echo -e "${GREEN}============================================================${NC}"
echo -e "Duration: ${ELAPSED} seconds"
echo ""

# Find the latest simulation database
LATEST_SIM=$(ls -t "${SIMULATOR_DIR}/simulations"/simulation_*.db 2>/dev/null | head -1)

if [ -n "${LATEST_SIM}" ]; then
    echo -e "Results: ${LATEST_SIM}"
    echo ""
    echo "Next steps:"
    echo "  1. Run analysis:  ./hpc_scripts/run_analysis.sh"
    echo "  2. Fetch results: ./hpc_scripts/fetch_results.sh (from local machine)"
fi

# Deactivate venv
deactivate
