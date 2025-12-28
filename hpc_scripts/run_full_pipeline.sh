#!/bin/bash
# ============================================================================
# BearishVanish - Full HPC Pipeline
# ============================================================================
# This script runs the complete simulation and analysis pipeline on HPC.
# Designed to be run on the HPC login node.
#
# Usage (run on HPC):
#   ./run_full_pipeline.sh sp500
#   ./run_full_pipeline.sh sp500 --offline
# ============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${BLUE}============================================================${NC}"
echo -e "${BLUE}BearishVanish - Full HPC Pipeline${NC}"
echo -e "${BLUE}============================================================${NC}"
echo ""
echo -e "This will run: Simulation -> Analysis"
echo -e "Hostname: $(hostname)"
echo -e "Date:     $(date)"
echo ""

START_TIME=$(date +%s)

# Step 1: Run Simulation
echo -e "${CYAN}============================================================${NC}"
echo -e "${CYAN}STEP 1: Running Simulation${NC}"
echo -e "${CYAN}============================================================${NC}"
echo ""

"${SCRIPT_DIR}/run_simulation.sh" "$@"

# Step 2: Run Analysis
echo ""
echo -e "${CYAN}============================================================${NC}"
echo -e "${CYAN}STEP 2: Running Analysis${NC}"
echo -e "${CYAN}============================================================${NC}"
echo ""

"${SCRIPT_DIR}/run_analysis.sh" --latest

# Complete
END_TIME=$(date +%s)
TOTAL_ELAPSED=$((END_TIME - START_TIME))

echo ""
echo -e "${GREEN}============================================================${NC}"
echo -e "${GREEN}FULL PIPELINE COMPLETE!${NC}"
echo -e "${GREEN}============================================================${NC}"
echo ""
echo -e "Total Duration: ${TOTAL_ELAPSED} seconds ($(echo "scale=1; ${TOTAL_ELAPSED}/60" | bc) minutes)"
echo ""
echo "Results are ready. From your LOCAL machine, run:"
echo "  cd $(dirname "${SCRIPT_DIR}")"
echo "  ./hpc_scripts/fetch_results.sh"
echo ""
echo "Then start the visualizer:"
echo "  cd visualizer && python main.py"
echo ""
