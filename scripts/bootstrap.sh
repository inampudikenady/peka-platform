#!/bin/bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "======================================="
echo "PEKA Bootstrap Starting"
echo "Project root: $PROJECT_ROOT"
echo "======================================="

if [ ! -f .env ]; then
  echo "[1/7] Creating .env from .env.example"
  cp .env.example .env
else
  echo "[1/7] .env already exists"
fi

set -a
# shellcheck disable=SC1091
source .env
set +a

PEKA_DATA_DIR="${PEKA_DATA_DIR:-/opt/peka/data}"

echo "[2/7] Creating runtime data folders under: $PEKA_DATA_DIR"
mkdir -p "$PEKA_DATA_DIR"/{qdrant,ollama,openwebui,logs,wiki,cmdb,rvtools}
mkdir -p "$PROJECT_ROOT/logs"

echo "[3/7] Creating Python virtual environment"
if [ ! -d venv ]; then
  python3 -m venv venv
else
  echo "venv already exists"
fi

echo "[4/7] Installing Python requirements"
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo "[5/7] Starting Docker services"
docker compose --env-file .env -f docker/docker-compose.yml up -d

echo "[6/7] Waiting for services"

echo "[7/7] Verifying services"

qdrant_ok=0
for i in {1..30}; do
  if curl -fsS http://localhost:6333/collections >/dev/null; then
    echo "Qdrant OK"
    qdrant_ok=1
    break
  fi
  sleep 2
done
if [ "$qdrant_ok" -ne 1 ]; then
  echo "Qdrant FAILED"
fi

ollama_ok=0
for i in {1..30}; do
  if curl -fsS http://localhost:11434/api/tags >/dev/null; then
    echo "Ollama OK"
    ollama_ok=1
    break
  fi
  sleep 2
done
if [ "$ollama_ok" -ne 1 ]; then
  echo "Ollama FAILED"
fi

echo "======================================="
echo "PEKA Bootstrap Complete"
echo "Next: scripts/pull-model.sh or start API with scripts/start-api.sh"
echo "======================================="
