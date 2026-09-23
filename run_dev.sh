#!/usr/bin/env bash
set -e

# BioKG - Local Development Startup Script
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"

echo "=========================================================="
echo "  BioKG: Biomedical Knowledge Graph Extraction System"
echo "=========================================================="

# 1. Find a safe Python version (3.10 - 3.12) to avoid incompatible edge versions
PYTHON_CMD=""
for cmd in python3.12 python3.11 python3.10 python3; do
    if command -v $cmd &> /dev/null; then
        # Check if the version is strictly between 3.9 and 3.12
        VER=$($cmd -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
        if awk "BEGIN {exit !($VER >= 3.9 && $VER <= 3.12)}"; then
            PYTHON_CMD=$cmd
            break
        fi
    fi
done

if [ -z "$PYTHON_CMD" ]; then
    echo "ERROR: Could not find a compatible Python version (3.9 - 3.12)."
    echo "Please install Python 3.10, 3.11, or 3.12 to proceed."
    exit 1
fi

echo "Using $PYTHON_CMD for the virtual environment..."

# 2. Setup Backend virtualenv if missing
if [ ! -d "$BACKEND_DIR/.venv" ]; then
    echo "Creating Python virtual environment in backend/.venv..."
    $PYTHON_CMD -m venv "$BACKEND_DIR/.venv"
    echo "Installing backend dependencies from requirements.txt..."
    "$BACKEND_DIR/.venv/bin/pip" install --upgrade pip
    "$BACKEND_DIR/.venv/bin/pip" install -r "$BACKEND_DIR/requirements.txt"
fi

VENV_PYTHON="$BACKEND_DIR/.venv/bin/python"
VENV_UVICORN="$BACKEND_DIR/.venv/bin/uvicorn"

# 2. Setup Frontend node_modules if missing
if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
    echo "Installing frontend dependencies from package.json..."
    (cd "$FRONTEND_DIR" && npm install)
fi

cleanup() {
    echo ""
    echo "Stopping servers..."
    kill $(jobs -p) 2>/dev/null || true
    exit 0
}
trap cleanup SIGINT SIGTERM EXIT

# Start backend
echo "[1/2] Starting FastAPI backend on http://localhost:8000..."
cd "$BACKEND_DIR"
PYTHONPATH="$BACKEND_DIR" "$VENV_UVICORN" app.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

# Wait for backend health
echo "Waiting for backend to be healthy..."
for i in {1..15}; do
    if curl -s http://localhost:8000/health >/dev/null 2>&1; then
        echo "Backend is online and healthy!"
        break
    fi
    sleep 1
done

# Start frontend
echo "[2/2] Starting Vite React frontend on http://localhost:5173..."
cd "$FRONTEND_DIR"
npm run dev &
FRONTEND_PID=$!

echo ""
echo "=========================================================="
echo "  BioKG Application is running!"
echo "  - Frontend Web UI:  http://localhost:5173"
echo "  - Backend REST API: http://localhost:8000"
echo "  - API Swagger Docs: http://localhost:8000/docs"
echo "  Press Ctrl+C to stop both servers."
echo "=========================================================="

wait $BACKEND_PID $FRONTEND_PID
