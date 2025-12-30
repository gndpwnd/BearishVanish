#!/bin/bash
# ============================================================================
# BearishVanish - Sync to HPC Cluster
# ============================================================================
# This script syncs the project to the HPC login node (vegaln1.erau.edu)
# The shared filesystem makes it accessible from GPU nodes as well.
#
# Usage:
#   ./sync_to_hpc.sh           # Full sync (code + offline data)
#   ./sync_to_hpc.sh --dry-run # Preview changes
#   ./sync_to_hpc.sh --code    # Sync only code (no data/results)
#   ./sync_to_hpc.sh --data    # Sync only offline data (for updates)
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
DATA_ONLY=""

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
        --data)
            DATA_ONLY="true"
            echo -e "${YELLOW}DATA ONLY MODE - Syncing offline_data directory only${NC}"
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --dry-run    Show what would be synced without making changes"
            echo "  --code       Sync only code files (no data, caches, or results)"
            echo "  --data       Sync only offline data (for updating market data)"
            echo "  --help       Show this help message"
            echo ""
            echo "Examples:"
            echo "  ./sync_to_hpc.sh                  # Full sync (recommended first time)"
            echo "  ./sync_to_hpc.sh --data           # Update offline data after download"
            echo "  ./sync_to_hpc.sh --code           # Quick code update"
            echo "  ./sync_to_hpc.sh --dry-run --data # Preview data sync"
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

# Handle DATA_ONLY mode
if [ "$DATA_ONLY" == "true" ]; then
    echo -e "${BLUE}Syncing offline data to HPC...${NC}"
    echo ""

    # Create remote directory if it doesn't exist
    ssh "${HPC_USER}@${HPC_HOST}" "mkdir -p ${HPC_PROJECT_DIR}/simulator/offline_data" 2>/dev/null || true

    # Sync only the offline_data directory
    rsync -avz --progress \
        ${DRY_RUN} \
        "${LOCAL_PROJECT_DIR}/simulator/offline_data/" \
        "${HPC_USER}@${HPC_HOST}:${HPC_PROJECT_DIR}/simulator/offline_data/"
else
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
fi

echo ""
if [ -z "$DRY_RUN" ]; then
    echo -e "${GREEN}============================================================${NC}"
    echo -e "${GREEN}Sync complete!${NC}"
    echo -e "${GREEN}============================================================${NC}"
    echo ""
    if [ "$DATA_ONLY" == "true" ]; then
        echo "Offline data synced to: ${HPC_PROJECT_DIR}/simulator/offline_data/"
        echo ""
        echo "The HPC now has updated market data for offline simulations."
        echo "Run simulations with: cd ${HPC_PROJECT_DIR}/simulator && python3 main.py --offline"
    else
        echo "Project synced to: ${HPC_PROJECT_DIR}"
        echo ""
        echo "Next steps:"
        echo "  1. SSH to HPC:     ssh ${HPC_USER}@${HPC_HOST}"
        echo "  2. Go to project:  cd ${HPC_PROJECT_DIR}"
        echo "  3. Setup Python:   python3 -m venv venv && source venv/bin/activate"
        echo "  4. Install deps:   pip install -r requirements.txt"
        echo "  5. Run simulation: cd simulator && python3 main.py --offline"
        echo ""
        echo "Offline data workflow:"
        echo "  1. Download data locally: python3 main.py --download --days 365"
        echo "  2. Sync data to HPC:      ./hpc_scripts/sync_to_hpc.sh --data"
        echo "  3. Run on HPC:            python3 main.py --offline"
    fi
else
    echo -e "${YELLOW}============================================================${NC}"
    echo -e "${YELLOW}Dry run complete - no changes made${NC}"
    echo -e "${YELLOW}============================================================${NC}"
fi
