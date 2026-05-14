#!/bin/bash
set -euo pipefail
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

if [ -f .env ]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

source venv/bin/activate
mkdir -p logs

# Stop existing API process if already running
pkill -f "uvicorn app.main:app" || true

nohup uvicorn app.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  > logs/api.log 2>&1 &

echo "PEKA API started. Logs: $PROJECT_ROOT/logs/api.log"
echo "Health: curl http://localhost:8000/health"
echo "UI: http://<server-ip>:8000/ui"
