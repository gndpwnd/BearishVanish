#!/bin/bash
# ============================================================================
# BearishVanish - Sync to HPC Cluster
# ============================================================================
# This script syncs the project to the HPC login node (vegaln1.erau.edu)
# The shared filesystem makes it accessible from GPU nodes as well.
#
# Usage:
#   ./sync_to_hpc.sh           # Full sync
#   ./sync_to_hpc.sh --dry-run # Preview changes
#   ./sync_to_hpc.sh --code    # Sync only code (no data/results)
# ============================================================================

set -e

# Configuration
HPC_USER="nelsg10"
HPC_HOST="vegaln1.erau.edu"
HPC_PROJECT_DIR="/home2/${HPC_USER}/BearishVanish"
LOCAL_PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}============================================================${NC}"
echo -e "${BLUE}BearishVanish - Sync to HPC${NC}"
echo -e "${BLUE}============================================================${NC}"
echo ""
echo -e "Local:  ${LOCAL_PROJECT_DIR}"
echo -e "Remote: ${HPC_USER}@${HPC_HOST}:${HPC_PROJECT_DIR}"
echo ""

# Parse arguments
DRY_RUN=""
CODE_ONLY=""

for arg in "$@"; do
    case $arg in
        --dry-run)
            DRY_RUN="--dry-run"
            echo -e "${YELLOW}DRY RUN MODE - No changes will be made${NC}"
            ;;
        --code)
            CODE_ONLY="true"
            echo -e "${YELLOW}CODE ONLY MODE - Skipping data and results${NC}"
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --dry-run    Show what would be synced without making changes"
            echo "  --code       Sync only code files (no data, caches, or results)"
            echo "  --help       Show this help message"
            exit 0
            ;;
    esac
done

# Build exclude list
EXCLUDES=(
    # Git
    ".git"

    # Python caches
    "__pycache__"
    "*.pyc"
    "*.pyo"
    ".pytest_cache"

    # Virtual environments
    "venv"
    ".venv"
    "env"

    # IDE files
    ".vscode"
    ".idea"
    "*.swp"
    "*.swo"

    # OS files
    ".DS_Store"
    "Thumbs.db"

    # Logs
    "*.log"
    "simulation_errors.log"

    # Temporary files
    "tmp_*.txt"
    "*.tmp"
)

# Additional excludes for code-only mode
if [ "$CODE_ONLY" == "true" ]; then
    EXCLUDES+=(
        # Data directories
        "simulator/cache"
        "simulator/simulations"
        "simulator/data"

        # Analysis results
        "analysis/analysis_dbs"

        # Visualizer static/cached data
        "visualizer/static/cache"

        # Documentation archives
        "0_docs/chats"
    )
fi

# Build rsync exclude arguments
EXCLUDE_ARGS=""
for pattern in "${EXCLUDES[@]}"; do
    EXCLUDE_ARGS+="--exclude='${pattern}' "
done

echo -e "${BLUE}Syncing project to HPC...${NC}"
echo ""

# Create remote directory if it doesn't exist
ssh "${HPC_USER}@${HPC_HOST}" "mkdir -p ${HPC_PROJECT_DIR}" 2>/dev/null || true

# Run rsync
eval rsync -avz --progress \
    ${DRY_RUN} \
    ${EXCLUDE_ARGS} \
    --delete \
    "${LOCAL_PROJECT_DIR}/" \
    "${HPC_USER}@${HPC_HOST}:${HPC_PROJECT_DIR}/"

echo ""
if [ -z "$DRY_RUN" ]; then
    echo -e "${GREEN}============================================================${NC}"
    echo -e "${GREEN}Sync complete!${NC}"
    echo -e "${GREEN}============================================================${NC}"
    echo ""
    echo "Project synced to: ${HPC_PROJECT_DIR}"
    echo ""
    echo "Next steps:"
    echo "  1. SSH to HPC:     ssh ${HPC_USER}@${HPC_HOST}"
    echo "  2. Go to project:  cd ${HPC_PROJECT_DIR}"
    echo "  3. Setup Python:   python3 -m venv venv && source venv/bin/activate"
    echo "  4. Install deps:   pip install -r requirements.txt"
    echo "  5. Run simulation: ./hpc_scripts/run_simulation.sh sp500"
else
    echo -e "${YELLOW}============================================================${NC}"
    echo -e "${YELLOW}Dry run complete - no changes made${NC}"
    echo -e "${YELLOW}============================================================${NC}"
fi
