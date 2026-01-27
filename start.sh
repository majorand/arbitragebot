#!/bin/bash

# Arbitrage Bot Startup Script for Linux/Mac

echo ""
echo "========================================"
echo "  ARBITRAGE BOT - STARTUP SCRIPT"
echo "========================================"
echo ""

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "ERROR: Node.js is not installed"
    echo "Please install Node.js 18+ from https://nodejs.org/"
    exit 1
fi

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python is not installed"
    echo "Please install Python 3.11+ from https://python.org/"
    exit 1
fi

echo "[✓] Node.js and Python detected"
echo ""

# Get the project root directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Start Backend in background
echo "[*] Starting Backend (FastAPI on port 8000)..."
cd "$SCRIPT_DIR"
python -m uvicorn app:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# Wait for backend to start
sleep 3

# Start Frontend in background
echo "[*] Starting Frontend (Next.js on port 3000)..."
cd "$SCRIPT_DIR/web/frontend"
npm run dev &
FRONTEND_PID=$!

# Wait for frontend to start
sleep 3

echo ""
echo "========================================"
echo "  STARTUP COMPLETE"
echo "========================================"
echo ""
echo "Backend:   http://localhost:8000"
echo "Dashboard: http://localhost:3000"
echo "API Docs:  http://localhost:8000/docs"
echo ""
echo "Process IDs:"
echo "  Backend:  $BACKEND_PID"
echo "  Frontend: $FRONTEND_PID"
echo ""
echo "To stop the bot, run:"
echo "  kill $BACKEND_PID $FRONTEND_PID"
echo ""

# Open in browser (if available)
if command -v xdg-open &> /dev/null; then
    xdg-open http://localhost:3000
elif command -v open &> /dev/null; then
    open http://localhost:3000
fi

# Keep script running and handle signals
trap "kill $BACKEND_PID $FRONTEND_PID" INT TERM
wait $BACKEND_PID $FRONTEND_PID
