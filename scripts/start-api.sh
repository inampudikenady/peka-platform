#!/bin/bash

cd /data/peka
source /data/rag-api/venv/bin/activate

nohup uvicorn app.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  > /data/peka/api.log 2>&1 &
