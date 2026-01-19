#!/bin/bash
set -e

echo "Cleaning up..."
pkill -f "playwright" || true
pkill -f "uvicorn" || true
pkill -f "python3" || true
pkill -f "node" || true

echo "Resetting Environment..."
/Users/stepants/dev/spatia/.venv/bin/python3 scripts/reset_env.py

echo "Starting Backend..."
/Users/stepants/dev/spatia/.venv/bin/python3 -m uvicorn backend.main:app --port 8000 > backend.log 2>&1 &
BACKEND_PID=$!
echo "Backend PID: $BACKEND_PID"

echo "Waiting for health..."
sleep 5
for i in {1..10}; do
    if curl -s http://localhost:8000/api/health > /dev/null; then
        echo "Backend is UP"
        break
    fi
    echo "Waiting..."
    sleep 2
done

echo "Running Playwright..."
cd frontend
# Run WITHOUT webServer in config (since we started it manually) or rely on reuseExistingServer
# Setting CI=1 ensures it doesn't try to spin up webServer if reuseExistingServer check passes? 
# Actually playwright config has reuseExistingServer: true.
# But we verified the config command now points to valid python too.
npx playwright test

echo "Done."
kill $BACKEND_PID || true
