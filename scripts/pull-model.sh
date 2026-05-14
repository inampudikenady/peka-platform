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

MODEL="${PEKA_MODEL:-qwen2.5:3b}"
echo "Pulling model: $MODEL"
docker exec -it peka-ollama ollama pull "$MODEL"
