# PEKA

**Private Enterprise Knowledge Assistant**

PEKA is a private enterprise operational intelligence platform designed to integrate organizational knowledge, CMDB data, infrastructure telemetry, monitoring systems, logs, and operational procedures into a conversational assistant.

## Current POC Components

- FastAPI RAG API
- Qdrant vector database
- Ollama local LLM runtime
- Open WebUI container
- DokuWiki ingestion pipeline
- Lightweight reranking for technical infrastructure questions
- Simple browser UI at `/ui`

## Quick Start

```bash
cp .env.example .env
./scripts/bootstrap.sh
./scripts/pull-model.sh
./scripts/rebuild-index.sh
./scripts/start-api.sh
```

Open:

```text
http://<server-ip>:8000/ui
```

## Important Notes

- Do not commit customer wiki dumps, Qdrant storage, models, logs, or secrets.
- Keep customer/client identity in `.env`, not hardcoded platform code.
- For production-like performance, use GPU-backed inference.

## Status

POC / Active Development

## Runtime path customization

PEKA defaults to `/opt/peka` for the application and `/opt/peka/data` for runtime data.
Customers can change the runtime data path without editing Docker Compose by updating `.env`:

```env
PEKA_DATA_DIR=/srv/peka/data
PEKA_WIKI_PATH=/srv/peka/data/wiki
```

Docker Compose uses `${PEKA_DATA_DIR:-/opt/peka/data}`, so it stays portable across customer environments.

## Quick start

```bash
cd /opt/peka
cp .env.example .env
vi .env
./scripts/bootstrap.sh
./scripts/pull-model.sh
./scripts/rebuild-index.sh
./scripts/start-api.sh
```

UI: `http://<server-ip>:8000/ui`

