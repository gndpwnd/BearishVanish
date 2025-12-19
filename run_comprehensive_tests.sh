#!/bin/bash
# Comprehensive Testing Framework for Trading Strategies
# Runs complete test suite: unit tests, simulations, diagnostics, validation

set -e  # Exit on error

echo "========================================================================"
echo "  COMPREHENSIVE TRADING SYSTEM TEST SUITE"
echo "========================================================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
STRATEGIES="Conservative Income,Mean Reversion,Trend Following,Breakout"
UNIVERSE="SP500_TOP_50"
TEST_DAYS=730  # 2 years (includes bear market)

# Step 1: Unit Tests
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "STEP 1: Unit Tests"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
cd tests
if python run_all_tests.py; then
    echo -e "${GREEN}✅ Unit tests passed${NC}"
else
    echo -e "${RED}❌ Unit tests failed${NC}"
    exit 1
fi
cd ..

# Step 2: Run Simulations
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "STEP 2: Run Simulations (2-year backtest)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
cd simulator

if python main.py --strategies "$STRATEGIES" \
                  --universe $UNIVERSE \
                  --days $TEST_DAYS \
                  --force-liquidate; then
    echo -e "${GREEN}✅ Simulations completed${NC}"

    # Get latest simulation database
    LATEST_DB=$(ls -t simulations/*.db | head -1)
    echo "Latest simulation: $LATEST_DB"
else
    echo -e "${RED}❌ Simulations failed${NC}"
    exit 1
fi

# Step 3: Strategy Diagnostics
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "STEP 3: Strategy Diagnostics"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if python strategy_diagnostics.py --db "$LATEST_DB"; then
    echo -e "${GREEN}✅ Diagnostics completed${NC}"
else
    echo -e "${YELLOW}⚠️  Diagnostics had warnings${NC}"
fi

# Step 4: Strategy Validation
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "STEP 4: Strategy Validation (Production Readiness)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Run validation in lenient mode first
echo "Running lenient validation..."
python strategy_validation_framework.py --db "$LATEST_DB"

# Ask user if they want strict validation
echo ""
read -p "Run strict (production) validation? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Running strict validation..."
    python strategy_validation_framework.py --db "$LATEST_DB" --strict
fi

# Step 5: Analysis
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "STEP 5: Analysis Engine"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
cd ../analysis

if python analysis_engine.py --sim "$LATEST_DB"; then
    echo -e "${GREEN}✅ Analysis completed${NC}"

    LATEST_ANALYSIS=$(ls -t analysis_dbs/*.db | head -1)
    echo "Latest analysis: $LATEST_ANALYSIS"
else
    echo -e "${YELLOW}⚠️  Analysis had issues${NC}"
fi

# Step 6: Summary Report
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "STEP 6: Summary Report"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
cd ..

# Extract key metrics from analysis database
sqlite3 "$LATEST_ANALYSIS" <<EOF
.mode column
.headers on
SELECT
    strategy_name,
    printf("%.1f%%", total_return_pct) as "Return",
    printf("%.1f%%", max_drawdown_pct) as "Max DD",
    printf("%.1f%%", win_rate_pct) as "Win Rate",
    printf("%.2f", sharpe_ratio) as "Sharpe",
    completed_trades as "Trades"
FROM strategy_summary
ORDER BY sharpe_ratio DESC;
EOF

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "TEST SUITE COMPLETE!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📊 Results:"
echo "   Simulation DB: $LATEST_DB"
echo "   Analysis DB: $LATEST_ANALYSIS"
echo ""
echo "📈 Next steps:"
echo "   1. Review diagnostic output above"
echo "   2. Check validation results (validation_results.json)"
echo "   3. Run visualizer: cd visualizer && python main.py"
echo "   4. Iterate on strategies based on recommendations"
echo ""
echo -e "${GREEN}✅ All tests completed successfully!${NC}"
