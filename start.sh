#!/bin/bash

# Instructor Assistant - Start Script
# This script starts both the backend and frontend dev servers

cd "$(dirname "$0")"

echo "🚀 Starting Instructor Assistant..."
echo ""

# Check if backend venv exists
if [ ! -d "backend/.webenv" ]; then
    echo "❌ Backend virtual environment not found. Creating it..."
    python3 -m venv backend/.webenv
    source backend/.webenv/bin/activate
    pip install -r backend/requirements.txt
    deactivate
fi

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "❌ Node modules not found. Installing..."
    npm install
fi

echo "✅ Starting backend on http://127.0.0.1:8010"
backend/.webenv/bin/python -m uvicorn backend.main:app --host 127.0.0.1 --port 8010 --reload &
BACKEND_PID=$!

echo "✅ Starting frontend on http://localhost:5173"
npm run dev:client &
FRONTEND_PID=$!

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✨ Instructor Assistant is starting..."
echo ""
echo "   Backend:  http://127.0.0.1:8010/api"
echo "   Frontend: http://localhost:5173"
echo ""
echo "   Press Ctrl+C to stop both servers"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Wait and cleanup on exit
trap "echo ''; echo '🛑 Stopping servers...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM

wait
