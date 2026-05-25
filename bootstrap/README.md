# PEKA Endpoint Bootstrap README

## Overview

PEKA endpoint bootstrap enables rapid onboarding of Linux and Windows systems into the PEKA operational monitoring stack.

The bootstrap workflow automates or standardizes:

- Exporter installation
- Log shipping configuration
- PEKA stock registration
- Prometheus target rendering
- Prometheus reload
- Endpoint validation

This enables near one-click onboarding of infrastructure into PEKA operational visibility.

---

# Architecture

```text
Endpoint
  ↓
Bootstrap Script
  ↓
Exporter + Promtail Install
  ↓
PEKA Stock Registration
  ↓
Prometheus Target Rendering
  ↓
Prometheus Reload
  ↓
Metrics + Logs Available in PEKA
```

---

# PEKA Server Structure

## Bootstrap Directory

```bash
/opt/peka/bootstrap
```

## Bootstrap Files

```text
linux-bootstrap.sh
windows-bootstrap.ps1
```

## Script Directory

```bash
/opt/peka/scripts
```

## Supporting Scripts

```text
register-linux-host.sh
register-windows-host.sh
render-prometheus-targets.sh
```

---

# PEKA Stock Inventory

## Stock File

```bash
/opt/peka/monitoring/targets/peka-stock.yml
```

## Purpose

The PEKA stock file is the current lightweight inventory source for monitored endpoints.

It tracks Linux and Windows hosts and is used to generate Prometheus file-based scrape targets.

## Example

```yaml
linux:
  - hostname: peka-dev-ai-001
    ip: 10.50.1.4

  - hostname: peka-dev-linux-sea-001
    ip: 10.70.1.5

windows:
  - hostname: peka-dev-win-sea-001
    ip: 10.70.1.4
```

## Notes

- This is the current POC inventory source.
- Future state should use ServiceNow CMDB as the authoritative source.
- The stock file is Git-friendly and easy to review.

---

# Prometheus Dynamic Target Rendering

## Renderer Script

```bash
/opt/peka/scripts/render-prometheus-targets.sh
```

## Purpose

The renderer reads PEKA stock and generates Prometheus file service discovery target files.

## Generated Files

```bash
/opt/peka/monitoring/prometheus/linux-targets.yml
/opt/peka/monitoring/prometheus/linux-process-targets.yml
/opt/peka/monitoring/prometheus/windows-targets.yml
```

## Generated Target Ports

| OS | Component | Port |
|---|---:|---:|
| Linux | node_exporter | 9100 |
| Linux | process_exporter | 9256 |
| Windows | windows_exporter | 9182 |

---

# Prometheus Configuration

## Prometheus Config File

```bash
/opt/peka/monitoring/prometheus/prometheus.yml
```

## Dynamic Scrape Jobs

```yaml
- job_name: "linux-nodes"
  file_sd_configs:
    - files:
        - /etc/prometheus/linux-targets.yml

- job_name: "linux-processes"
  file_sd_configs:
    - files:
        - /etc/prometheus/linux-process-targets.yml

- job_name: "windows-nodes"
  file_sd_configs:
    - files:
        - /etc/prometheus/windows-targets.yml
```

---

# Docker Compose Requirements

## Compose File

```bash
/opt/peka/monitoring/docker-compose.yml
```

## Required Prometheus Volume Mounts

```yaml
volumes:
  - ./prometheus/prometheus.yml:/etc/prometheus/prometheus.yml:ro
  - ./prometheus/linux-targets.yml:/etc/prometheus/linux-targets.yml:ro
  - ./prometheus/linux-process-targets.yml:/etc/prometheus/linux-process-targets.yml:ro
  - ./prometheus/windows-targets.yml:/etc/prometheus/windows-targets.yml:ro
  - ./data/prometheus:/prometheus
```

## Prometheus Reload Requirement

Prometheus container must include lifecycle reload support:

```yaml
command:
  - '--config.file=/etc/prometheus/prometheus.yml'
  - '--storage.tsdb.path=/prometheus'
  - '--web.enable-lifecycle'
```

## Reload Command

```bash
curl -X POST http://localhost:9090/-/reload
```

---

# Linux Bootstrap

## Bootstrap File

```bash
/opt/peka/bootstrap/linux-bootstrap.sh
```

## Components Installed

### node_exporter

Linux system metrics.

```text
Port: 9100
```

Metrics include:

- CPU
- Memory
- Filesystem
- Network
- Load
- OS-level metrics

### process_exporter

Linux process-level metrics.

```text
Port: 9256
```

Metrics include:

- Process CPU
- Process memory
- Process counts

### Promtail

Linux log shipping to Loki.

```text
Port: 9080
```

Logs collected:

```text
/var/log/syslog
/var/log/auth.log
/var/log/kern.log
```

## Linux Bootstrap Current Behavior

```text
- Detect hostname
- Detect primary IP
- Install node_exporter
- Install process_exporter
- Install Promtail
- Configure systemd services
- Configure Promtail log scraping
- Register host into PEKA stock
- Render Prometheus target files
- Reload Prometheus
```

## Linux Idempotency Status

Current state:

```text
POC-level idempotent
```

Safe re-run behavior:

```text
- No duplicate PEKA stock entry
- Services remain enabled and running
- Prometheus targets regenerate cleanly
- Prometheus reload is safe
```

Current limitations:

```text
- Re-downloads binaries every run
- Rewrites service files every run
- Rewrites Promtail config every run
- Loki endpoint currently defaults to hardcoded PEKA AI server IP
```

---

# Linux Validation

## Validate node_exporter

```bash
systemctl status node_exporter --no-pager
curl -s http://localhost:9100/metrics | head
```

## Validate process_exporter

```bash
systemctl status process_exporter --no-pager
curl -s http://localhost:9256/metrics | head
```

## Validate Promtail

```bash
systemctl status promtail --no-pager
curl -s http://localhost:9080/metrics | head
```

## Generate Linux Test Log

```bash
logger "PEKA Linux bootstrap Loki validation test from $(hostname)"
```

## Query Loki for Linux Test Log

```bash
curl -G -s "http://localhost:3100/loki/api/v1/query_range" \
  --data-urlencode 'query={host="peka-dev-ai-001"} |= "PEKA Linux bootstrap Loki validation test"' \
  --data-urlencode 'limit=5' | jq
```

---

# Windows Bootstrap

## Bootstrap File

```powershell
/opt/peka/bootstrap/windows-bootstrap.ps1
```

## Components Installed or Deployed

### windows_exporter

Windows system metrics.

```text
Port: 9182
```

Enabled collectors:

```text
cpu
logical_disk
memory
net
os
service
system
process
```

### Promtail

Windows Event Log shipping to Loki.

```text
Install path: C:\promtail
Config file: C:\promtail\config.yml
Metrics port: 9080
```

Windows logs collected:

```text
Application
System
Security
```

---

# Windows Bootstrap Current Behavior

```text
- Detect hostname
- Detect primary IP
- Install windows_exporter
- Validate windows_exporter metrics
- Deploy Promtail binary
- Create Promtail config
```

## Current Manual Step

Promtail Windows service creation is currently handled manually with NSSM.

This was chosen because:

- NSSM download from the public site was unreliable during testing
- New-Service quoting caused the Promtail service to stop
- NSSM is more reliable for wrapping Promtail as a Windows service

Future improvement should host NSSM internally under PEKA bootstrap tools.

---

# Windows Promtail Config

## Config Path

```powershell
C:\promtail\config.yml
```

## Required Data Directory

```powershell
mkdir C:\promtail\data -Force
```

## Example Config

```yaml
server:
  http_listen_port: 9080
  grpc_listen_port: 0

positions:
  filename: C:\promtail\data\positions.yml

clients:
  - url: http://10.50.1.4:3100/loki/api/v1/push

scrape_configs:

  - job_name: windows_system

    windows_events:
      use_incoming_timestamp: true
      bookmark_path: C:\promtail\data\bookmark_system.xml
      eventlog_name: System

      labels:
        job: windows_system
        host: peka-dev-win-sea-001

  - job_name: windows_application

    windows_events:
      use_incoming_timestamp: true
      bookmark_path: C:\promtail\data\bookmark_application.xml
      eventlog_name: Application

      labels:
        job: windows_application
        host: peka-dev-win-sea-001

  - job_name: windows_security

    windows_events:
      use_incoming_timestamp: true
      bookmark_path: C:\promtail\data\bookmark_security.xml
      eventlog_name: Security

      labels:
        job: windows_security
        host: peka-dev-win-sea-001
```

---

# Windows NSSM Manual Service Setup

## Recommended Path

```powershell
C:\tools\nssm.exe
```

## Remove Existing Promtail Service

```powershell
sc.exe delete promtail
```

Ignore the error if the service does not exist.

## Create Promtail Service with NSSM

```powershell
C:\tools\nssm.exe install promtail C:\promtail\promtail.exe "-config.file=C:\promtail\config.yml"
```

## Set Auto Start

```powershell
C:\tools\nssm.exe set promtail Start SERVICE_AUTO_START
```

## Optional stdout/stderr Logs

```powershell
C:\tools\nssm.exe set promtail AppStdout C:\promtail\promtail.out.log
C:\tools\nssm.exe set promtail AppStderr C:\promtail\promtail.err.log
```

## Start Service

```powershell
Start-Service promtail
```

## Validate Service

```powershell
Get-Service promtail
Invoke-WebRequest http://localhost:9080/metrics -UseBasicParsing
```

---

# Windows Validation

## Validate windows_exporter Locally

```powershell
Get-Service windows_exporter
Invoke-WebRequest http://localhost:9182/metrics -UseBasicParsing
```

## Validate windows_exporter from PEKA AI Server

```bash
curl -s http://10.70.1.4:9182/metrics | head
```

## Validate Prometheus Windows Target

```bash
curl -s http://localhost:9090/api/v1/targets | jq '.data.activeTargets[] | select(.labels.job=="windows-nodes") | {host: .labels.host, instance: .labels.instance, health: .health, lastError: .lastError}'
```

Expected:

```json
{
  "host": "peka-dev-win-sea-001",
  "instance": "10.70.1.4:9182",
  "health": "up",
  "lastError": ""
}
```

---

# Windows Loki Validation

## Generate Windows Test Event

```powershell
eventcreate /ID 100 /L APPLICATION /T INFORMATION /SO PEKA /D "PEKA Windows logging test"
```

## Query Loki from PEKA AI Server

```bash
curl -G -s "http://localhost:3100/loki/api/v1/query_range" \
  --data-urlencode 'query={host="peka-dev-win-sea-001"} |= "PEKA Windows logging test"' \
  --data-urlencode 'limit=10' | jq
```

## Broader Windows Log Query

```bash
curl -G -s "http://localhost:3100/loki/api/v1/query_range" \
  --data-urlencode 'query={host="peka-dev-win-sea-001"}' \
  --data-urlencode 'limit=5' | jq
```

## Query by Job

```bash
curl -G -s "http://localhost:3100/loki/api/v1/query_range" \
  --data-urlencode 'query={job="windows_system"}' \
  --data-urlencode 'limit=5' | jq
```

---

# Register Linux Host Script

## File

```bash
/opt/peka/scripts/register-linux-host.sh
```

## Purpose

Adds a Linux host to the Linux section of PEKA stock if it does not already exist.

## Usage

```bash
/opt/peka/scripts/register-linux-host.sh <hostname> <ip>
```

## Example

```bash
/opt/peka/scripts/register-linux-host.sh peka-dev-linux-002 10.70.1.6
```

## Behavior

```text
- Checks if hostname already exists
- Avoids duplicate stock entry
- Inserts Linux host before the windows section
```

---

# Register Windows Host Script

## File

```bash
/opt/peka/scripts/register-windows-host.sh
```

## Purpose

Adds a Windows host to the Windows section of PEKA stock if it does not already exist.

## Usage

```bash
/opt/peka/scripts/register-windows-host.sh <hostname> <ip>
```

## Example

```bash
/opt/peka/scripts/register-windows-host.sh peka-dev-win-002 10.70.1.6
```

## Behavior

```text
- Checks if hostname already exists
- Avoids duplicate stock entry
- Appends Windows host under windows section
```

---

# Prometheus Target Validation

## View All Active Targets

```bash
curl -s http://localhost:9090/api/v1/targets | jq '.data.activeTargets[] | {job: .labels.job, host: .labels.host, instance: .labels.instance, health: .health}'
```

## Expected Jobs

```text
linux-nodes
linux-processes
windows-nodes
```

## Expected Endpoint Examples

```text
10.50.1.4:9100
10.50.1.4:9256
10.70.1.5:9100
10.70.1.5:9256
10.70.1.4:9182
```

---

# Current Working Status

## Linux

```text
Working:
- node_exporter install
- process_exporter install
- Promtail install
- Linux log shipping
- PEKA stock registration
- Prometheus target rendering
- Prometheus reload
- Loki validation
```

## Windows

```text
Working:
- windows_exporter install
- Prometheus scrape validation
- Promtail config validated conceptually
- Manual NSSM service approach selected
```

## Windows Remaining Manual Step

```text
- Promtail service creation via NSSM
```

---

# Known Limitations

```text
- Loki endpoint is currently hardcoded to 10.50.1.4
- PEKA controller discovery is not dynamic yet
- NSSM is not internally hosted yet
- Windows Promtail service creation is manual for now
- No bootstrap authentication/token yet
- No ServiceNow CMDB write-back yet
- No uninstall workflow yet
```

---

# Future Improvements

```text
- Pass PEKA/Loki controller URL dynamically
- Discover PEKA controller via DNS
- Host NSSM and binaries internally under PEKA
- Add bootstrap API token authentication
- Add Windows stock registration automation
- Add ServiceNow CMDB registration/update
- Add uninstall scripts
- Add endpoint health dashboard
- Add bootstrap version tracking
- Add upgrade orchestration
```

---

# Recommended Git Files to Commit

```text
bootstrap/linux-bootstrap.sh
bootstrap/windows-bootstrap.ps1
scripts/register-linux-host.sh
scripts/register-windows-host.sh
scripts/render-prometheus-targets.sh
monitoring/targets/peka-stock.yml
monitoring/prometheus/prometheus.yml
monitoring/docker-compose.yml
bootstrap_readme.md
```

---

# Summary

The endpoint bootstrap work completed in this session establishes PEKA's first repeatable onboarding model for operational telemetry.

Linux onboarding is POC-level idempotent and functional end-to-end.

Windows onboarding has working metrics and a clear manual NSSM path for Promtail service creation.

The next major improvement is removing hardcoded PEKA server IPs and making endpoint bootstrap controller-aware through DNS or runtime parameters.

