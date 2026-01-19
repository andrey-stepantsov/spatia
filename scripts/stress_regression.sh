#!/bin/bash
set -e

RESET_CMD="/Users/stepants/dev/spatia/.venv/bin/python3 scripts/reset_env.py"
BACKEND_TEST_CMD="/Users/stepants/dev/spatia/.venv/bin/pytest tests"
FRONTEND_TEST_CMD="npx playwright test"
PROJECT_ROOT="/Users/stepants/dev/spatia"
FRONTEND_DIR="/Users/stepants/dev/spatia/frontend"

for i in {1..3}
do
    echo "============================================"
    echo "Staring Regression Run #$i"
    echo "============================================"
    
    echo "[1/3] Resetting Environment..."
    cd "$PROJECT_ROOT"
    $RESET_CMD
    
    echo "[2/3] Running Backend Tests..."
    $BACKEND_TEST_CMD
    
    echo "[3/3] Running Frontend E2E Tests..."
    cd "$FRONTEND_DIR"
    $FRONTEND_TEST_CMD
    
    echo "Run #$i Completed Successfully!"
    echo ""
done

echo "ALL 3 RUNS COMPLETED SUCCESSFULLY."
