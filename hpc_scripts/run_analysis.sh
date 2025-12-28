#!/bin/bash
# ============================================================================
# BearishVanish - Run Analysis Engine on HPC
# ============================================================================
# This script runs the analysis engine on simulation results.
# The analysis engine computes metrics, risk calculations, and pre-processes
# chart data for the visualizer.
#
# Usage (run on HPC):
#   ./run_analysis.sh           # Analyze latest simulation
#   ./run_analysis.sh --sim <path>  # Analyze specific simulation
# ============================================================================

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "${SCRIPT_DIR}")"
ANALYSIS_DIR="${PROJECT_DIR}/analysis"
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
echo -e "${BLUE}BearishVanish - HPC Analysis Engine${NC}"
echo -e "${BLUE}============================================================${NC}"
echo ""
echo -e "Project:  ${PROJECT_DIR}"
echo -e "Hostname: $(hostname)"
echo -e "Date:     $(date)"
echo ""

# Load Python module on HPC (has proper ctypes support)
if [[ "$(hostname)" =~ (vegaln|gpu) ]]; then
    echo -e "${CYAN}Loading Python module...${NC}"
    source /etc/profile.d/modules.sh 2>/dev/null || true
    module load python/3.11.7-gcc-8.5.0-wfpoppf 2>/dev/null || true
fi

# Ensure virtual environment exists and is activated
if [ ! -d "${VENV_DIR}" ]; then
    echo -e "${RED}Error: Virtual environment not found${NC}"
    echo "Run ./run_simulation.sh first to set up the environment"
    exit 1
fi

echo -e "${CYAN}Activating virtual environment...${NC}"
source "${VENV_DIR}/bin/activate"

# Parse arguments
SIM_PATH=""
USE_LATEST="true"

for arg in "$@"; do
    case $arg in
        --sim)
            USE_LATEST="false"
            ;;
        --latest)
            USE_LATEST="true"
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --latest          Analyze the latest simulation (default)"
            echo "  --sim <path>      Analyze a specific simulation database"
            echo ""
            echo "Examples:"
            echo "  $0                                    # Analyze latest"
            echo "  $0 --sim ../simulator/simulations/simulation_20241220.db"
            echo ""
            exit 0
            ;;
        *)
            if [ "$USE_LATEST" == "false" ] && [ -z "$SIM_PATH" ]; then
                SIM_PATH="$arg"
            fi
            ;;
    esac
done

# Find simulation database
if [ "$USE_LATEST" == "true" ]; then
    echo -e "${CYAN}Finding latest simulation...${NC}"
    SIM_PATH=$(ls -t "${SIMULATOR_DIR}/simulations"/simulation_*.db 2>/dev/null | head -1)

    if [ -z "${SIM_PATH}" ]; then
        echo -e "${RED}Error: No simulation databases found${NC}"
        echo "Run ./run_simulation.sh first"
        exit 1
    fi
fi

# Verify simulation exists
if [ ! -f "${SIM_PATH}" ]; then
    echo -e "${RED}Error: Simulation database not found: ${SIM_PATH}${NC}"
    exit 1
fi

echo -e "Simulation: ${SIM_PATH}"
echo ""

# Change to analysis directory
cd "${ANALYSIS_DIR}"

# Show simulation info
echo -e "${CYAN}============================================================${NC}"
echo -e "${CYAN}Simulation Details${NC}"
echo -e "${CYAN}============================================================${NC}"

# Get basic info from simulation DB
sqlite3 "${SIM_PATH}" <<EOF 2>/dev/null || true
.mode column
.headers on
SELECT
    COUNT(DISTINCT strategy_name) as strategies,
    COUNT(DISTINCT symbol) as symbols,
    COUNT(*) as total_trades
FROM trade_history;
EOF

echo ""

# Run analysis
echo -e "${GREEN}============================================================${NC}"
echo -e "${GREEN}Starting Analysis Engine${NC}"
echo -e "${GREEN}============================================================${NC}"
echo ""

START_TIME=$(date +%s)

python analysis_engine.py --sim "${SIM_PATH}"

END_TIME=$(date +%s)
ELAPSED=$((END_TIME - START_TIME))

echo ""
echo -e "${GREEN}============================================================${NC}"
echo -e "${GREEN}Analysis Complete!${NC}"
echo -e "${GREEN}============================================================${NC}"
echo -e "Duration: ${ELAPSED} seconds"
echo ""

# Find the latest analysis database
LATEST_ANALYSIS=$(ls -t "${ANALYSIS_DIR}/analysis_dbs"/analysis_*.db 2>/dev/null | head -1)

if [ -n "${LATEST_ANALYSIS}" ]; then
    echo -e "Analysis DB: ${LATEST_ANALYSIS}"
    echo -e "Size:        $(du -h "${LATEST_ANALYSIS}" | cut -f1)"
    echo ""
    echo "Next steps:"
    echo "  1. Fetch results: ./hpc_scripts/fetch_results.sh (from local machine)"
    echo "  2. Start visualizer locally: cd visualizer && python main.py"
fi

# Deactivate venv
deactivate
