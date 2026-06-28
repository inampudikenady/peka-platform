#!/bin/zsh
set -e

cd ~/Documents/Peka-routing

mkdir -p logs

echo "Stopping existing services..."
pkill -f "uvicorn app.main:app" 2>/dev/null || true
pkill -f "http.server 3001" 2>/dev/null || true
PORT_3001_PIDS=$(lsof -ti tcp:3001 2>/dev/null || true)
if [ -n "$PORT_3001_PIDS" ]; then
    kill $PORT_3001_PIDS 2>/dev/null || true
fi

echo "Starting FastAPI..."
source venv/bin/activate
nohup uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    > logs/api.log 2>&1 &
API_PID=$!
disown $API_PID 2>/dev/null || true

echo "Starting Tuple portal..."
cd frontend/portal
nohup python3 -m http.server 3001 \
    > ../../logs/tuple.log 2>&1 &
PORTAL_PID=$!
disown $PORTAL_PID 2>/dev/null || true
cd ../..

sleep 2

echo
echo "PEKA API started. Logs: ./logs/api.log"
echo "Tuple portal started. Logs: ./logs/tuple.log"
echo
echo "Verification commands:"
echo "  curl http://localhost:8000/health"
echo "  http://localhost:8000/docs"
echo "  http://localhost:3001"
