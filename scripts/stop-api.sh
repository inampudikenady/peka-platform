#!/bin/bash
set -euo pipefail

pkill -f "uvicorn app.main:app" || true
pkill -f "http.server 3001" || true

PORT_3001_PIDS=$(lsof -ti tcp:3001 2>/dev/null || true)
if [ -n "$PORT_3001_PIDS" ]; then
    kill $PORT_3001_PIDS 2>/dev/null || true
fi

echo "PEKA API and Tuple portal stopped if they were running."
