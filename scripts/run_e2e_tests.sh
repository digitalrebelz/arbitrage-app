#!/bin/bash
# Run E2E tests with proper setup

set -e

echo "=== Running E2E Tests ==="

# Ensure screenshot directory exists
mkdir -p tests/screenshots/e2e

# Clean old screenshots
rm -f tests/screenshots/e2e/*.png

# Start Streamlit in background
echo "Starting Streamlit dashboard..."
STREAMLIT_SERVER_HEADLESS=true streamlit run src/ui/dashboard.py --server.port 8502 &
STREAMLIT_PID=$!

# Wait for server to start
echo "Waiting for server to start..."
sleep 5

# Check if server is running
if ! kill -0 $STREAMLIT_PID 2>/dev/null; then
    echo "Error: Streamlit failed to start"
    exit 1
fi

echo "Streamlit running on PID $STREAMLIT_PID"

# Run tests
echo "Running E2E tests..."
pytest tests/e2e/ -v --headed 2>&1 || TEST_RESULT=$?

# Stop Streamlit
echo "Stopping Streamlit..."
kill $STREAMLIT_PID 2>/dev/null || true
wait $STREAMLIT_PID 2>/dev/null || true

# Report results
echo ""
echo "=== E2E Test Results ==="
echo "Screenshots saved to: tests/screenshots/e2e/"
ls -la tests/screenshots/e2e/ 2>/dev/null || echo "No screenshots found"

if [ "${TEST_RESULT:-0}" -ne 0 ]; then
    echo ""
    echo "Some tests failed!"
    exit $TEST_RESULT
fi

echo ""
echo "All E2E tests passed!"
