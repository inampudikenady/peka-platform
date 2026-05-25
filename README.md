# PEKA — Private Enterprise Knowledge Assistant

PEKA is a private enterprise operational intelligence assistant.

It started as a RAG-based wiki assistant and has now evolved into a lightweight AIOps-style operational assistant that can correlate:

- Enterprise knowledge documents
- ServiceNow CMDB records
- ServiceNow incidents
- Prometheus metrics
- Linux process metrics
- Loki centralized logs
- Linux and Windows operational telemetry

The goal is not just document search. The goal is conversational operational visibility.

---

# Current Architecture

```text
OpenWebUI
   ↓
PEKA FastAPI API
   ↓
Intent Router / Context Builder
   ↓
RAG Engine + Operational Tools
   ↓
Qdrant / Ollama / ServiceNow / Prometheus / Loki
```

---

# Core Components

## FastAPI

Main API service.

### Location

```bash
/opt/peka/app
```

### Key Files

```text
app/main.py
app/rag_engine.py
app/prompts.py
app/config.py
app/models.py
```

### Routes

```text
app/routes/ask.py
app/routes/openai_v1.py
app/routes/ui.py
app/routes/servicenow.py
app/routes/monitoring.py
app/routes/logs.py
app/routes/ops.py
```

### Tools

```text
app/tools/servicenow_client.py
app/tools/prometheus_client.py
app/tools/loki_client.py
app/tools/operational_analysis.py
app/tools/context_builder.py
```

---

# RAG / Knowledge Layer

PEKA indexes internal wiki knowledge into Qdrant.

## Current Dataset

- DokuWiki exported text files

## RAG Components

| Component | Purpose |
|---|---|
| Qdrant | Vector database |
| Ollama | Local LLM runtime |
| FastAPI | PEKA API |
| OpenWebUI | Chat frontend |

## Current Model

```text
qwen2.5:3b
```

## OpenAI-Compatible Endpoint

```text
/v1/models
/v1/chat/completions
```

This allows OpenWebUI to use PEKA as a custom model endpoint.

---

# ServiceNow Integration

PEKA integrates with ServiceNow Developer Instance.

## Current Instance

```text
https://dev274568.service-now.com
```

## Environment Variables Required

```bash
SERVICENOW_INSTANCE=https://dev274568.service-now.com
SERVICENOW_USER=<user>
SERVICENOW_PASSWORD=<password>
```

## Supported ServiceNow Features

- CMDB CI lookup by hostname
- CMDB CI lookup by IP address
- Incident lookup for last 30 days
- ServiceNow direct links for CIs and incidents
- CI/IP resolution layer

## Example APIs

```bash
curl "http://localhost:8000/tools/servicenow/ci-summary?ci=peka-dev-linux-sea-001"

curl "http://localhost:8000/tools/servicenow/ci-summary?ci=10.70.1.5"
```

## Resolution Support

ServiceNow lookup supports both:

- hostname → IP
- IP → hostname

This is important because operators may know either hostname or IP.

## Current Demo CIs

```text
peka-dev-ai-001
peka-dev-linux-sea-001
peka-dev-win-sea-001
```

## Example Incident

```text
INC0010002 - High CPU observed on Linux application server
```

---

# Prometheus Monitoring

Prometheus runs on:

```text
peka-dev-ai-001
```

## Prometheus Location

```bash
/opt/peka/monitoring
```

## Compose File

```bash
/opt/peka/monitoring/docker-compose.yml
```

## Prometheus Config

```bash
/opt/peka/monitoring/prometheus/prometheus.yml
```

## Prometheus UI

```text
http://<ai-public-ip>:9090
```

## Current Scrape Targets

```yaml
linux-nodes:
  - 10.50.1.4:9100
  - 10.70.1.5:9100

linux-processes:
  - 10.50.1.4:9256
  - 10.70.1.5:9256

windows-nodes:
  - 10.70.1.4:9182
```

---

# Linux Monitoring

Linux uses:

- node_exporter
- process_exporter

## Installed On

```text
peka-dev-ai-001
peka-dev-linux-sea-001
```

## Ports

| Exporter | Port |
|---|---|
| node_exporter | 9100 |
| process_exporter | 9256 |

## Metrics Collected

- CPU usage
- Memory usage
- Filesystem usage
- Node up/down status
- Observed OS from Prometheus
- Top CPU processes
- Top memory processes

## Example APIs

```bash
curl "http://localhost:8000/tools/monitoring/linux-summary?ip=10.70.1.5"

curl "http://localhost:8000/tools/monitoring/ci-summary?identifier=peka-dev-linux-sea-001"

curl "http://localhost:8000/tools/monitoring/ci-summary?identifier=10.70.1.5"
```

---

# Windows Monitoring

Windows uses:

- windows_exporter

## Installed On

```text
peka-dev-win-sea-001
```

## Port

```text
9182
```

## Collectors Enabled

- cpu
- logical_disk
- memory
- net
- os
- service
- system
- process

## Important Notes

- Validated from Prometheus target health
- Windows ping may fail due to firewall
- TCP 9182 metrics still work correctly

---

# Loki Logging

Loki runs on:

```text
peka-dev-ai-001
```

## Loki Endpoint

```text
http://localhost:3100
```

## Environment Variable

```bash
LOKI_URL=http://localhost:3100
```

## Loki Config

```bash
/opt/peka/monitoring/loki/loki-config.yml
```

## Loki Data Path

```bash
/opt/peka/monitoring/data/loki
```

---

# Linux Log Collection

Linux uses Promtail.

## Installed On

```text
peka-dev-ai-001
peka-dev-linux-sea-001
```

## Promtail Config

```bash
/etc/promtail/config.yml
```

## Service Validation

```bash
systemctl status promtail
```

## Logs Collected

```text
/var/log/syslog
/var/log/auth.log
/var/log/kern.log
```

## Important Permission Fix

```bash
sudo usermod -aG adm promtail
sudo systemctl restart promtail
```

---

# Windows Log Collection

Windows uses Promtail with Windows Event Log scraping.

## Install Location

```text
C:\promtail
```

## Config

```text
C:\promtail\config.yml
```

## Service Wrapper

- NSSM

## Logs Collected

- Application
- System
- Security

## Validated Test Event

```powershell
eventcreate /ID 100 /L APPLICATION /T INFORMATION /SO PEKA /D "PEKA Windows logging test"
```

## Validated Loki Query

```bash
curl -G -s "http://localhost:3100/loki/api/v1/query_range" \
  --data-urlencode 'query={host="peka-dev-win-sea-001"} |= "PEKA Windows logging test"' \
  --data-urlencode 'limit=10'
```

## Windows Event Normalization

Implemented in:

```text
app/tools/loki_client.py
```

Normalized fields:

- event_id
- level
- source
- user
- message
- channel
- computer

---

# Logs API

## Current APIs

```bash
curl "http://localhost:8000/tools/logs/search?identifier=peka-dev-linux-sea-001&limit=5"

curl "http://localhost:8000/tools/logs/search?identifier=peka-dev-linux-sea-001&search=error&hours=24&limit=10"

curl "http://localhost:8000/tools/logs/errors?identifier=peka-dev-linux-sea-001&hours=24&limit=10"

curl "http://localhost:8000/tools/logs/search?identifier=peka-dev-win-sea-001&search=PEKA%20Windows%20logging%20test&hours=24&limit=5"
```

---

# Operational Analysis Engine

Implemented in:

```text
app/tools/operational_analysis.py
```

## Purpose

ServiceNow + Prometheus + Loki → structured operational findings

## Analysis Includes

- CI existence
- IP resolution
- Recent incidents
- Node exporter status
- CPU pressure
- Memory pressure
- Filesystem usage
- Recent error-like logs
- Sample logs
- Overall severity

## Example APIs

```bash
curl "http://localhost:8000/tools/ops/analyze?identifier=peka-dev-linux-sea-001&hours=24"

curl "http://localhost:8000/tools/ops/analyze?identifier=10.70.1.5&hours=24"
```

## Possible Severity

```text
info
warning
critical
```

---

# OpenWebUI Conversational Intents

OpenWebUI calls:

```text
/v1/chat/completions
```

Intent handling is done in:

```text
app/tools/context_builder.py
```

## Current Intent Routing

| User asks | Backend used |
|---|---|
| What do we know about CI? | ServiceNow CMDB + incidents |
| Show incident history | ServiceNow incidents |
| How is health/status/slow? | Operational analysis |
| Show logs/errors/events | Loki |
| Patch/upgrade/how-to | RAG + live CI context |
| Procedure/documentation | RAG + live CI context |

## Example Queries

```text
What do we know about peka-dev-linux-sea-001?
How is the health of peka-dev-linux-sea-001?
Why is peka-dev-linux-sea-001 slow?
Show errors from peka-dev-win-sea-001 in last 24 hours
Search logs for PEKA Windows logging test on peka-dev-win-sea-001
I want to patch peka-dev-linux-sea-001 to RHEL7. Validate current OS and provide relevant upgrade guidance.
```

---

# API Startup

## Start API

```bash
cd /opt/peka
./scripts/start-api.sh
```

## Stop API

```bash
./scripts/stop-api.sh
```

## Health Check

```bash
curl http://localhost:8000/health
```

## Logs

```bash
tail -f /opt/peka/logs/api.log
```

---

# Monitoring Stack Startup

## Start Prometheus and Loki

```bash
cd /opt/peka/monitoring
docker compose up -d
```

## Validation

```bash
docker ps
curl http://localhost:9090/-/healthy
curl http://localhost:3100/ready
```

---

# Important Design Decisions

## Do Not Dump Everything

PEKA should not dump CMDB + metrics + logs + docs for every question.

It should route by intent.

## ServiceNow is the Identity Source

ServiceNow resolves:

```text
hostname ↔ IP
```

Prometheus and Loki are queried using the resolved identity.

## Do Not Hardcode OS from Hostname

OS should come from:

1. CMDB OS field
2. Prometheus observed OS metric
3. Unknown

## Do Not Show RAG Sources for Pure Operational Questions

Show sources when the question is documentation/procedure oriented.

Examples:

```text
How do I patch RHEL7?
What document explains filesystem expansion?
Give me upgrade guidance.
```

Do not show wiki source files for:

```text
What do we know about this CI?
How is server health?
Show errors from last 24 hours.
```

## Logs Need Normalization

Windows logs are JSON from Event Viewer. PEKA normalizes them before sending context to the LLM.

Linux logs are plain text.

---

# Known Issues / Backlog

## Response Quality

Some responses still need polishing to avoid:

- misleading procedure summaries
- overconfident guidance
- generic wording
- unnecessary headings

## Noise Suppression

Current error search may match benign lines such as:

```text
error can be ignored
condition check resulted in process error reports being skipped
```

Need a noise suppression layer.

## Process Memory Values

`process_exporter` memory numbers may look inflated due to aggregation/virtual memory behavior.

Need refinement.

## Windows Metrics

Windows exporter works, but operational analysis currently focuses mostly on Linux host summary.

Need Windows-specific health summary.

## Change / Request Correlation

Future ServiceNow expansion:

- changes
- requests
- problems
- tasks

## Alertmanager

Not yet implemented.

Recommended future approach:

```text
Prometheus alerts → PEKA awareness first
Selective ticket creation later
```

Avoid alert spam.

## Grafana

Not required right now.

PEKA uses Prometheus/Loki APIs directly.

---

# Current Status

PEKA is now at a decent operational POC stage.

## Working Features

- RAG wiki retrieval
- OpenWebUI integration
- OpenAI-compatible API
- ServiceNow CMDB lookup
- ServiceNow incident lookup
- CI/IP resolution
- Prometheus metrics
- Linux node_exporter
- Linux process_exporter
- Windows windows_exporter
- Loki log aggregation
- Linux Promtail
- Windows Promtail
- Windows event normalization
- Operational analysis API
- Conversational intent routing

---

# Final Vision

PEKA is now more than a RAG chatbot.

It is the beginning of a private enterprise operational intelligence assistant.

