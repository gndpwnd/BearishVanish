#!/bin/bash
# ============================================================================
# BearishVanish - Fetch Results from HPC
# ============================================================================
# This script fetches simulation and analysis results from the HPC cluster
# back to your local machine.
#
# Usage (run on LOCAL machine):
#   ./fetch_results.sh           # Fetch latest results
#   ./fetch_results.sh --all     # Fetch all results
#   ./fetch_results.sh --dry-run # Preview what would be fetched
# ============================================================================

set -e

# Configuration
HPC_USER="nelsg10"
HPC_HOST="vegaln1.erau.edu"
HPC_PROJECT_DIR="/home2/${HPC_USER}/BearishVanish"
LOCAL_PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${BLUE}============================================================${NC}"
echo -e "${BLUE}BearishVanish - Fetch Results from HPC${NC}"
echo -e "${BLUE}============================================================${NC}"
echo ""
echo -e "Remote: ${HPC_USER}@${HPC_HOST}:${HPC_PROJECT_DIR}"
echo -e "Local:  ${LOCAL_PROJECT_DIR}"
echo ""

# Parse arguments
DRY_RUN=""
FETCH_ALL=""
LATEST_ONLY="true"

for arg in "$@"; do
    case $arg in
        --dry-run)
            DRY_RUN="--dry-run"
            echo -e "${YELLOW}DRY RUN MODE - No files will be transferred${NC}"
            ;;
        --all)
            FETCH_ALL="true"
            LATEST_ONLY=""
            echo -e "${CYAN}Fetching ALL results${NC}"
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --dry-run    Show what would be fetched without transferring"
            echo "  --all        Fetch all simulation and analysis databases"
            echo "  --help       Show this help message"
            echo ""
            echo "By default, only the latest simulation and analysis are fetched."
            exit 0
            ;;
    esac
done

echo ""

# Create local directories if they don't exist
mkdir -p "${LOCAL_PROJECT_DIR}/simulator/simulations"
mkdir -p "${LOCAL_PROJECT_DIR}/analysis/analysis_dbs"

if [ "$LATEST_ONLY" == "true" ]; then
    # Fetch only latest simulation
    echo -e "${CYAN}Finding latest simulation on HPC...${NC}"

    LATEST_SIM=$(ssh "${HPC_USER}@${HPC_HOST}" "ls -t ${HPC_PROJECT_DIR}/simulator/simulations/simulation_*.db 2>/dev/null | head -1" 2>/dev/null || echo "")

    if [ -n "${LATEST_SIM}" ]; then
        echo -e "Found: $(basename ${LATEST_SIM})"
        echo -e "${CYAN}Fetching simulation database...${NC}"

        rsync -avz --progress ${DRY_RUN} \
            "${HPC_USER}@${HPC_HOST}:${LATEST_SIM}" \
            "${LOCAL_PROJECT_DIR}/simulator/simulations/"
    else
        echo -e "${YELLOW}No simulation databases found on HPC${NC}"
    fi

    echo ""

    # Fetch only latest analysis
    echo -e "${CYAN}Finding latest analysis on HPC...${NC}"

    LATEST_ANALYSIS=$(ssh "${HPC_USER}@${HPC_HOST}" "ls -t ${HPC_PROJECT_DIR}/analysis/analysis_dbs/analysis_*.db 2>/dev/null | head -1" 2>/dev/null || echo "")

    if [ -n "${LATEST_ANALYSIS}" ]; then
        echo -e "Found: $(basename ${LATEST_ANALYSIS})"
        echo -e "${CYAN}Fetching analysis database...${NC}"

        rsync -avz --progress ${DRY_RUN} \
            "${HPC_USER}@${HPC_HOST}:${LATEST_ANALYSIS}" \
            "${LOCAL_PROJECT_DIR}/analysis/analysis_dbs/"
    else
        echo -e "${YELLOW}No analysis databases found on HPC${NC}"
    fi

else
    # Fetch all results
    echo -e "${CYAN}Fetching all simulation databases...${NC}"
    rsync -avz --progress ${DRY_RUN} \
        "${HPC_USER}@${HPC_HOST}:${HPC_PROJECT_DIR}/simulator/simulations/" \
        "${LOCAL_PROJECT_DIR}/simulator/simulations/"

    echo ""
    echo -e "${CYAN}Fetching all analysis databases...${NC}"
    rsync -avz --progress ${DRY_RUN} \
        "${HPC_USER}@${HPC_HOST}:${HPC_PROJECT_DIR}/analysis/analysis_dbs/" \
        "${LOCAL_PROJECT_DIR}/analysis/analysis_dbs/"
fi

echo ""

if [ -z "$DRY_RUN" ]; then
    echo -e "${GREEN}============================================================${NC}"
    echo -e "${GREEN}Results fetched successfully!${NC}"
    echo -e "${GREEN}============================================================${NC}"
    echo ""

    # Show what was fetched
    echo "Simulation databases:"
    ls -lh "${LOCAL_PROJECT_DIR}/simulator/simulations/"*.db 2>/dev/null | tail -5 || echo "  (none)"
    echo ""

    echo "Analysis databases:"
    ls -lh "${LOCAL_PROJECT_DIR}/analysis/analysis_dbs/"*.db 2>/dev/null | tail -5 || echo "  (none)"
    echo ""

    echo "Next steps:"
    echo "  1. Start visualizer: cd visualizer && python main.py"
    echo "  2. Open browser:     http://localhost:8000"
else
    echo -e "${YELLOW}============================================================${NC}"
    echo -e "${YELLOW}Dry run complete - no files transferred${NC}"
    echo -e "${YELLOW}============================================================${NC}"
fi
