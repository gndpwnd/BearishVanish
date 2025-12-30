#!/bin/bash
# ============================================================================
# BearishVanish - Single Command Full Pipeline
# ============================================================================
# Run this ONE script to execute the complete workflow:
#   1. Sync code to HPC
#   2. Run simulation + analysis + reports on HPC
#   3. Fetch reports to local machine (timestamped folder)
#
# Usage:
#   ./run_full_pipeline.sh [workers]
#
# Examples:
#   ./run_full_pipeline.sh         # Default 24 workers
#   ./run_full_pipeline.sh 48      # Use 48 workers
#
# Requirements:
#   - SSH access to HPC configured (key-based auth recommended)
#   - Real market data cached on HPC (run download separately if needed)
# ============================================================================

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${SCRIPT_DIR}"
HPC_USER="nelsg10"
HPC_HOST="vegaln1.erau.edu"
HPC_PROJECT_DIR="/home2/${HPC_USER}/BearishVanish"
WORKERS="${1:-24}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Timestamp for this run
TIMESTAMP=$(date +%Y-%m-%d_%H%M%S)
LOCAL_REPORTS_DIR="${PROJECT_DIR}/docs/reports/run_${TIMESTAMP}"

echo -e "${BLUE}============================================================${NC}"
echo -e "${BLUE}  BearishVanish - Full Pipeline${NC}"
echo -e "${BLUE}============================================================${NC}"
echo ""
echo -e "Timestamp: ${TIMESTAMP}"
echo -e "Workers:   ${WORKERS}"
echo -e "Local:     ${PROJECT_DIR}"
echo -e "Remote:    ${HPC_USER}@${HPC_HOST}:${HPC_PROJECT_DIR}"
echo ""

START_TIME=$(date +%s)

# ============================================================================
# STEP 1: Sync code to HPC
# ============================================================================
echo -e "${CYAN}[1/3] Syncing code to HPC...${NC}"

rsync -avz --delete \
    --exclude='*.db' \
    --exclude='__pycache__' \
    --exclude='.git' \
    --exclude='venv' \
    --exclude='*.pyc' \
    --exclude='.env' \
    --exclude='docs/reports/*' \
    --exclude='simulator/simulations/*' \
    --exclude='analysis/analysis_dbs/*' \
    "${PROJECT_DIR}/" "${HPC_USER}@${HPC_HOST}:${HPC_PROJECT_DIR}/" \
    2>&1 | grep -E "^(sending|sent|total)" || true

echo -e "${GREEN}  Sync complete${NC}"
echo ""

# ============================================================================
# STEP 2: Run simulation + analysis + reports on HPC
# ============================================================================
echo -e "${CYAN}[2/3] Running pipeline on HPC (sim + analysis + reports)...${NC}"

# Create timestamped output folder on HPC and run everything
ssh "${HPC_USER}@${HPC_HOST}" << ENDSSH
set -e

# Load Python
module load python/3.11.7-gcc-8.5.0-wfpoppf 2>/dev/null || true

# Activate venv
cd ${HPC_PROJECT_DIR}
source venv/bin/activate

# Run the unified pipeline (uses real data, not mock)
python run_strategy_test.py --workers ${WORKERS}

# Find the latest test folder
LATEST_TEST=\$(ls -td docs/reports/test_* 2>/dev/null | head -1)
if [ -n "\$LATEST_TEST" ]; then
    echo ""
    echo "LATEST_FOLDER=\$LATEST_TEST"
    echo "Reports generated: \$(ls \$LATEST_TEST/*.md 2>/dev/null | wc -l)"
fi
ENDSSH

echo -e "${GREEN}  HPC pipeline complete${NC}"
echo ""

# ============================================================================
# STEP 3: Fetch reports to local machine
# ============================================================================
echo -e "${CYAN}[3/3] Fetching reports to local machine...${NC}"

# Get the latest test folder name from HPC
LATEST_FOLDER=$(ssh "${HPC_USER}@${HPC_HOST}" "ls -td ${HPC_PROJECT_DIR}/docs/reports/test_* 2>/dev/null | head -1")

if [ -n "${LATEST_FOLDER}" ]; then
    FOLDER_NAME=$(basename "${LATEST_FOLDER}")
    LOCAL_DEST="${PROJECT_DIR}/docs/reports/${FOLDER_NAME}"

    mkdir -p "${LOCAL_DEST}"

    rsync -avz \
        "${HPC_USER}@${HPC_HOST}:${LATEST_FOLDER}/" \
        "${LOCAL_DEST}/" \
        2>&1 | grep -E "^(receiving|received|total)" || true

    echo -e "${GREEN}  Reports saved to: ${LOCAL_DEST}${NC}"
else
    echo -e "${YELLOW}  Warning: No report folder found on HPC${NC}"
fi

echo ""

# ============================================================================
# Summary
# ============================================================================
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

echo -e "${GREEN}============================================================${NC}"
echo -e "${GREEN}  PIPELINE COMPLETE${NC}"
echo -e "${GREEN}============================================================${NC}"
echo ""
echo -e "Duration: ${DURATION} seconds"
echo ""

if [ -n "${LATEST_FOLDER}" ]; then
    echo -e "${CYAN}Reports:${NC}"
    ls -1 "${LOCAL_DEST}"/*.md 2>/dev/null | head -15
    echo ""
    echo -e "${CYAN}Quick View:${NC}"
    echo "  cat ${LOCAL_DEST}/TEST_SUMMARY.md"
    echo ""
fi

echo -e "${CYAN}Next Steps:${NC}"
echo "  1. Review reports in: ${LOCAL_DEST:-docs/reports/}"
echo "  2. Check TEST_SUMMARY.md for strategy performance"
echo "  3. Document findings in docs/Findings/"
echo ""
