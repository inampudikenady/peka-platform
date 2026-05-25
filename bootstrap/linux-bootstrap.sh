#!/bin/bash
set -euo pipefail

NODE_EXPORTER_VERSION="1.8.2"
PROCESS_EXPORTER_VERSION="0.8.3"

echo "PEKA Linux bootstrap started"

HOSTNAME_SHORT="$(hostname)"
IP_ADDR="$(hostname -I | awk '{print $1}')"

echo "Host: $HOSTNAME_SHORT"
echo "IP: $IP_ADDR"

echo "Installing node_exporter..."

if ! id node_exporter >/dev/null 2>&1; then
  useradd --no-create-home --shell /usr/sbin/nologin node_exporter
fi

WORKDIR="$(mktemp -d /tmp/peka-bootstrap.XXXXXX)"
cd "$WORKDIR"

curl -LO "https://github.com/prometheus/node_exporter/releases/download/v${NODE_EXPORTER_VERSION}/node_exporter-${NODE_EXPORTER_VERSION}.linux-amd64.tar.gz"
tar xzf "node_exporter-${NODE_EXPORTER_VERSION}.linux-amd64.tar.gz"
install -m 0755 "node_exporter-${NODE_EXPORTER_VERSION}.linux-amd64/node_exporter" /usr/local/bin/node_exporter

cat > /etc/systemd/system/node_exporter.service <<'SERVICE'
[Unit]
Description=Prometheus Node Exporter
After=network-online.target

[Service]
User=node_exporter
Group=node_exporter
Type=simple
ExecStart=/usr/local/bin/node_exporter

[Install]
WantedBy=multi-user.target
SERVICE

systemctl daemon-reload
systemctl enable --now node_exporter

echo "Installing process_exporter..."

if ! id process_exporter >/dev/null 2>&1; then
  useradd --no-create-home --shell /usr/sbin/nologin process_exporter
fi

curl -LO "https://github.com/ncabatoff/process-exporter/releases/download/v${PROCESS_EXPORTER_VERSION}/process-exporter-${PROCESS_EXPORTER_VERSION}.linux-amd64.tar.gz"
tar xzf "process-exporter-${PROCESS_EXPORTER_VERSION}.linux-amd64.tar.gz"
install -m 0755 "process-exporter-${PROCESS_EXPORTER_VERSION}.linux-amd64/process-exporter" /usr/local/bin/process-exporter

mkdir -p /etc/process-exporter

cat > /etc/process-exporter/config.yml <<'CONFIG'
process_names:
  - name: "{{.Comm}}"
    cmdline:
      - '.+'
CONFIG

cat > /etc/systemd/system/process_exporter.service <<'SERVICE'
[Unit]
Description=Prometheus Process Exporter
After=network-online.target

[Service]
User=process_exporter
Group=process_exporter
Type=simple
ExecStart=/usr/local/bin/process-exporter --config.path=/etc/process-exporter/config.yml --web.listen-address=:9256

[Install]
WantedBy=multi-user.target
SERVICE

systemctl daemon-reload
systemctl enable --now process_exporter

echo "Validating exporters..."
systemctl is-active --quiet node_exporter
systemctl is-active --quiet process_exporter

curl -s http://localhost:9100/metrics >/dev/null
curl -s http://localhost:9256/metrics >/dev/null

echo "node_exporter running on port 9100"
echo "process_exporter running on port 9256"

echo "Installing promtail..."

PROMTAIL_VERSION="2.9.8"
LOKI_URL="${LOKI_URL:-http://10.50.1.4:3100}"

if ! id promtail >/dev/null 2>&1; then
  useradd --no-create-home --shell /usr/sbin/nologin promtail
fi

WORKDIR="$(mktemp -d /tmp/peka-bootstrap.XXXXXX)"
cd "$WORKDIR"

curl -LO "https://github.com/grafana/loki/releases/download/v${PROMTAIL_VERSION}/promtail-linux-amd64.zip"

if ! command -v unzip >/dev/null 2>&1; then
  apt-get update
  apt-get install -y unzip
fi

unzip -o promtail-linux-amd64.zip
install -m 0755 promtail-linux-amd64 /usr/local/bin/promtail

mkdir -p /etc/promtail

cat > /etc/promtail/config.yml <<CONFIG
server:
  http_listen_port: 9080
  grpc_listen_port: 0

positions:
  filename: /var/lib/promtail/positions.yml

clients:
  - url: ${LOKI_URL}/loki/api/v1/push

scrape_configs:
  - job_name: linux-system-logs
    static_configs:
      - targets:
          - localhost
        labels:
          job: linux-system-logs
          host: ${HOSTNAME_SHORT}
          __path__: /var/log/syslog

  - job_name: linux-auth-logs
    static_configs:
      - targets:
          - localhost
        labels:
          job: linux-auth-logs
          host: ${HOSTNAME_SHORT}
          __path__: /var/log/auth.log

  - job_name: linux-kernel-logs
    static_configs:
      - targets:
          - localhost
        labels:
          job: linux-kernel-logs
          host: ${HOSTNAME_SHORT}
          __path__: /var/log/kern.log
CONFIG

mkdir -p /var/lib/promtail
chown -R promtail:promtail /var/lib/promtail /etc/promtail

usermod -aG adm promtail || true

cat > /etc/systemd/system/promtail.service <<'SERVICE'
[Unit]
Description=Promtail Log Shipper
After=network-online.target

[Service]
User=promtail
Group=promtail
Type=simple
ExecStart=/usr/local/bin/promtail -config.file=/etc/promtail/config.yml

[Install]
WantedBy=multi-user.target
SERVICE

systemctl daemon-reload
systemctl enable --now promtail

systemctl is-active --quiet promtail

echo "promtail installed and running"


echo "Registering host into PEKA stock..."

if [ -x /opt/peka/scripts/register-linux-host.sh ]; then
  /opt/peka/scripts/register-linux-host.sh "$HOSTNAME_SHORT" "$IP_ADDR"
fi

if [ -x /opt/peka/scripts/render-prometheus-targets.sh ]; then
  /opt/peka/scripts/render-prometheus-targets.sh
fi

if command -v curl >/dev/null 2>&1; then
  curl -s -X POST http://localhost:9090/-/reload >/dev/null || true
fi

echo "PEKA stock registration completed"

echo "PEKA Linux bootstrap completed"
