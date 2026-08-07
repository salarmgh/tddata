#!/bin/bash

# Start script for Trading Data Dashboard
# This script starts both the Flask API and React frontend

set -e

echo "=================================================="
echo "Starting Trading Data Dashboard"
echo "=================================================="
echo ""

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "❌ Virtual environment not found. Please run: python -m venv .venv"
    exit 1
fi

# Check if dependencies are installed
if [ ! -d "frontend/node_modules" ]; then
    echo "❌ Frontend dependencies not installed. Please run: cd frontend && npm install"
    exit 1
fi

# Check if database exists
if [ ! -f "database/telegram_data.db" ]; then
    echo "⚠️  Warning: database/telegram_data.db not found. Please crawl data first using:"
    echo "   python -m crawler.web_crawler crawl-manual"
    echo ""
fi

# Start Flask API in background
echo "🚀 Starting Flask API on http://localhost:5000..."
source .venv/bin/activate
python -m api.app &
API_PID=$!
echo "   API started with PID: $API_PID"
echo ""

# Wait a bit for API to start
sleep 3

# Start React frontend
echo "🚀 Starting React frontend on http://localhost:3000..."
cd frontend
npm start &
FRONTEND_PID=$!
echo "   Frontend started with PID: $FRONTEND_PID"
echo ""

echo "=================================================="
echo "✅ Dashboard is running!"
echo "=================================================="
echo ""
echo "📊 Frontend: http://localhost:3000"
echo "🔌 API:      http://localhost:5000/api/health"
echo ""
echo "Press Ctrl+C to stop all services"
echo ""

# Wait for Ctrl+C
trap "echo ''; echo '🛑 Stopping services...'; kill $API_PID $FRONTEND_PID 2>/dev/null; echo '✅ Stopped'; exit 0" INT

# Keep script running
wait

