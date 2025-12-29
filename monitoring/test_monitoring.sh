#!/bin/bash
# Quick test script for monitoring system

echo "=========================================="
echo "BearishVanish Monitoring System Test"
echo "=========================================="
echo

# Check if API server is running
echo "1. Checking if API server is running..."
if curl -s http://localhost:8765/ > /dev/null 2>&1; then
    echo "   ✅ API server is running"
else
    echo "   ❌ API server is NOT running"
    echo "   Start it with: python3 monitoring/api_server.py &"
    exit 1
fi

echo

# Test API endpoints
echo "2. Testing API endpoints..."

echo "   Testing /status endpoint..."
curl -s http://localhost:8765/status | python3 -m json.tool | head -10

echo

echo "   Testing /processes endpoint..."
curl -s http://localhost:8765/processes | python3 -m json.tool | head -15

echo

# Test CLI monitor
echo "3. Testing CLI monitor (one-time status)..."
python3 monitoring/monitor_cli.py

echo

echo "=========================================="
echo "Test Complete!"
echo "=========================================="
echo
echo "Next steps:"
echo "  - Run 'python3 monitoring/monitor_cli.py --watch' for live monitoring"
echo "  - Run a simulation to see real-time progress tracking"
echo "  - Test with: cd simulator && python3 main.py --offline --tickers AAPL,MSFT"
echo
