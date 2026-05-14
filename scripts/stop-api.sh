#!/bin/bash
set -euo pipefail
pkill -f "uvicorn app.main:app" || true
echo "PEKA API stopped if it was running."
