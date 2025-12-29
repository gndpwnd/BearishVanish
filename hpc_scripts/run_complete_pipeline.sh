#!/bin/bash
# ============================================================================
# BearishVanish - Complete HPC Pipeline with Report Generation
# ============================================================================
# This script runs the complete workflow:
#   1. Sync code to HPC
#   2. Run simulation on HPC
#   3. Run analysis on HPC
#   4. Generate markdown reports on HPC
#   5. Fetch all results (databases + reports) to local machine
#
# Usage (run on LOCAL machine):
#   ./run_complete_pipeline.sh sp500 [--offline] [--download]
#
# Examples:
#   ./run_complete_pipeline.sh sp500 --offline  # Use cached data
#   ./run_complete_pipeline.sh sp500 --download # Download fresh data first
# ============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "${SCRIPT_DIR}")"

# Configuration
HPC_USER="nelsg10"
HPC_HOST="vegaln1.erau.edu"
HPC_PROJECT_DIR="/home2/${HPC_USER}/BearishVanish"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'

echo -e "${BLUE}============================================================================${NC}"
echo -e "${BLUE}BearishVanish - Complete HPC Pipeline${NC}"
echo -e "${BLUE}============================================================================${NC}"
echo ""
echo -e "This will execute the full workflow:"
echo -e "  1. ${CYAN}Sync code to HPC${NC}"
echo -e "  2. ${CYAN}Run simulation on HPC${NC}"
echo -e "  3. ${CYAN}Run analysis on HPC${NC}"
echo -e "  4. ${CYAN}Generate reports on HPC${NC}"
echo -e "  5. ${CYAN}Fetch results to local machine${NC}"
echo ""
echo -e "Local:  ${PROJECT_DIR}"
echo -e "Remote: ${HPC_USER}@${HPC_HOST}:${HPC_PROJECT_DIR}"
echo ""

START_TIME=$(date +%s)

# ============================================================================
# STEP 1: Sync Code to HPC
# ============================================================================

echo -e "${MAGENTA}============================================================================${NC}"
echo -e "${MAGENTA}STEP 1/5: Syncing Code to HPC${NC}"
echo -e "${MAGENTA}============================================================================${NC}"
echo ""

"${SCRIPT_DIR}/sync_to_hpc.sh" --code

echo ""

# ============================================================================
# STEP 2: Run Simulation on HPC
# ============================================================================

echo -e "${MAGENTA}============================================================================${NC}"
echo -e "${MAGENTA}STEP 2/5: Running Simulation on HPC${NC}"
echo -e "${MAGENTA}============================================================================${NC}"
echo ""

ssh "${HPC_USER}@${HPC_HOST}" "cd ${HPC_PROJECT_DIR} && ./hpc_scripts/run_simulation.sh $@"

echo ""

# ============================================================================
# STEP 3: Run Analysis on HPC
# ============================================================================

echo -e "${MAGENTA}============================================================================${NC}"
echo -e "${MAGENTA}STEP 3/5: Running Analysis on HPC${NC}"
echo -e "${MAGENTA}============================================================================${NC}"
echo ""

ssh "${HPC_USER}@${HPC_HOST}" "cd ${HPC_PROJECT_DIR} && ./hpc_scripts/run_analysis.sh --latest"

echo ""

# ============================================================================
# STEP 4: Generate Reports on HPC
# ============================================================================

echo -e "${MAGENTA}============================================================================${NC}"
echo -e "${MAGENTA}STEP 4/5: Generating Markdown Reports on HPC${NC}"
echo -e "${MAGENTA}============================================================================${NC}"
echo ""

# Create reports directory on HPC
ssh "${HPC_USER}@${HPC_HOST}" "mkdir -p ${HPC_PROJECT_DIR}/docs/reports"

# Generate reports using the headless CLI
ssh "${HPC_USER}@${HPC_HOST}" << 'ENDSSH'
set -e

# Load Python module
module load python/3.11.7-gcc-8.5.0-wfpoppf

# Activate virtual environment
cd /home2/nelsg10/BearishVanish
source venv/bin/activate

# Run report generator
cd visualizer
python generate_report_cli.py --output ../docs/reports --type full

echo ""
echo "Reports generated successfully!"
ls -lh ../docs/reports/*.md | tail -10
ENDSSH

echo ""

# ============================================================================
# STEP 5: Fetch Results to Local Machine
# ============================================================================

echo -e "${MAGENTA}============================================================================${NC}"
echo -e "${MAGENTA}STEP 5/5: Fetching Results to Local Machine${NC}"
echo -e "${MAGENTA}============================================================================${NC}"
echo ""

# Fetch databases
"${SCRIPT_DIR}/fetch_results.sh"

echo ""

# Fetch reports
echo -e "${CYAN}Fetching markdown reports...${NC}"
mkdir -p "${PROJECT_DIR}/docs/reports"

rsync -avz --progress \
    "${HPC_USER}@${HPC_HOST}:${HPC_PROJECT_DIR}/docs/reports/" \
    "${PROJECT_DIR}/docs/reports/"

echo ""

# ============================================================================
# Complete
# ============================================================================

END_TIME=$(date +%s)
TOTAL_ELAPSED=$((END_TIME - START_TIME))
MINUTES=$(echo "scale=1; ${TOTAL_ELAPSED}/60" | bc)

echo -e "${GREEN}============================================================================${NC}"
echo -e "${GREEN}COMPLETE PIPELINE FINISHED SUCCESSFULLY!${NC}"
echo -e "${GREEN}============================================================================${NC}"
echo ""
echo -e "Total Duration: ${TOTAL_ELAPSED} seconds (${MINUTES} minutes)"
echo ""
echo -e "${CYAN}Results Summary:${NC}"
echo ""

# Show fetched files
echo "Simulation databases:"
ls -lh "${PROJECT_DIR}/simulator/simulations/"*.db 2>/dev/null | tail -3 || echo "  (none)"
echo ""

echo "Analysis databases:"
ls -lh "${PROJECT_DIR}/analysis/analysis_dbs/"*.db 2>/dev/null | tail -3 || echo "  (none)"
echo ""

echo "Generated reports:"
ls -lh "${PROJECT_DIR}/docs/reports/"*.md 2>/dev/null | tail -10 || echo "  (none)"
echo ""

echo -e "${GREEN}Next Steps:${NC}"
echo ""
echo "1. Review reports in: ${PROJECT_DIR}/docs/reports/"
echo ""
echo "2. Send reports to Claude/GPT-4 for analysis and improvement suggestions"
echo ""
echo "3. Start visualizer to explore results interactively:"
echo "   cd ${PROJECT_DIR}/visualizer"
echo "   python main.py"
echo "   # Then open http://localhost:8000"
echo ""
echo "4. Document findings in: ${PROJECT_DIR}/docs/Findings/"
echo ""
echo "5. Update strategies based on insights and re-run pipeline"
echo ""
