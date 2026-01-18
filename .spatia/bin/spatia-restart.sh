#!/bin/bash
# Spatia Orchestrated Restart Script

echo "🛑  Stopping Spatia Services..."
pkill -f "uvicorn backend.main:app"
pkill -f "vite"

# Wait a moment for ports to clear
sleep 2

echo "🧹  Services Stopped."

# Start Backend
echo "🚀  Starting Backend (Port 8000)..."
# We run in background with nohup to keep it alive
nohup devbox run -- bash -c "PYTHONPATH=. uvicorn backend.main:app --reload --port 8000" > backend.log 2>&1 &
BACKEND_PID=$!
echo "   - Backend PID: $BACKEND_PID"

# Start Frontend
echo "🎨  Starting Frontend (Port 5173)..."
cd frontend
nohup devbox run -- npm run dev > frontend.log 2>&1 &
FRONTEND_PID=$!
echo "   - Frontend PID: $FRONTEND_PID"
cd ..

echo "✅  Spatia is restarting."
echo "   - Backend Log: tail -f backend.log"
echo "   - Frontend Log: tail -f frontend/frontend.log"
