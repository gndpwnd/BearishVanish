#!/bin/bash
# HPC Strategy Testing Script
# Runs complete simulation -> analysis -> report pipeline on HPC
#
# Usage:
#   ./hpc_scripts/run_strategy_test_hpc.sh [universe] [workers]
#   ./hpc_scripts/run_strategy_test_hpc.sh sp500 48
#   ./hpc_scripts/run_strategy_test_hpc.sh test 96

set -e  # Exit on error

# Configuration
UNIVERSE=${1:-test}
WORKERS=${2:-48}
PROJECT_DIR="$HOME/BearishVanish"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$PROJECT_DIR/logs/test_${TIMESTAMP}.log"

# Create logs directory
mkdir -p "$PROJECT_DIR/logs"

echo "=============================================="
echo "BearishVanish HPC Strategy Test"
echo "=============================================="
echo "Universe: $UNIVERSE"
echo "Workers: $WORKERS"
echo "Timestamp: $TIMESTAMP"
echo "Log: $LOG_FILE"
echo ""

# Change to project directory
cd "$PROJECT_DIR"

# Start monitoring server in background (optional)
echo "Starting monitoring server..."
python3 monitoring/api_server.py > /dev/null 2>&1 &
MONITOR_PID=$!
sleep 2

# Run the strategy test pipeline
echo "Running strategy test pipeline..."
python3 run_strategy_test.py \
    --universe "$UNIVERSE" \
    --workers "$WORKERS" \
    --report-type full \
    2>&1 | tee "$LOG_FILE"

# Capture exit code
RESULT=$?

# Stop monitoring server
kill $MONITOR_PID 2>/dev/null || true

# Summary
echo ""
echo "=============================================="
if [ $RESULT -eq 0 ]; then
    echo "SUCCESS - Test completed"
else
    echo "FAILED - Check log: $LOG_FILE"
fi
echo "=============================================="

# Find and display the output directory
LATEST_TEST=$(ls -td "$PROJECT_DIR/docs/reports/test_"* 2>/dev/null | head -1)
if [ -n "$LATEST_TEST" ]; then
    echo "Output: $LATEST_TEST"
    echo ""
    echo "Reports generated:"
    ls -la "$LATEST_TEST"/*.md 2>/dev/null | head -15
fi

exit $RESULT
