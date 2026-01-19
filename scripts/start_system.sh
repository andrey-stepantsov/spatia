#!/bin/bash
set -e

# Define cleanup function
cleanup() {
    echo "Stopping Spatia..."
    kill $(jobs -p) 2>/dev/null || true
    wait
    echo "Spatia has learned to stop."
}

# Set trap for cleanup on SIGINT (Ctrl+C) and SIGTERM
trap cleanup SIGINT SIGTERM EXIT

# Pre-flight cleanup
echo "Checking for existing processes..."
pkill -f "uvicorn backend.main:app" || true
# We don't want to kill all nodes broadly, but identifying the vite process is tricky without lsof.
# Relying on uvicorn cleanup mostly as that was the error.
lsof -ti:8000 | xargs kill -9 2>/dev/null || true

echo "Starting Spatia System..."

# Activate Virtual Environment (if not already active in devbox)
if [ -z "$VIRTUAL_ENV" ]; then
    source .venv/bin/activate
fi

# Start Backend
echo "Starting Backend (Port 8000)..."
python3 -m uvicorn backend.main:app --port 8000 &
BACKEND_PID=$!

# Start Frontend
echo "Starting Frontend..."
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

# Wait for all background processes
wait
