#!/bin/bash
set -euo pipefail

HOSTNAME_IN="$1"
IP_IN="$2"
STOCK="/opt/peka/monitoring/targets/peka-stock.yml"

if grep -q "hostname: ${HOSTNAME_IN}" "$STOCK"; then
  echo "Host already exists in stock: ${HOSTNAME_IN}"
  exit 0
fi

cat >> "$STOCK" <<EOF2
  - hostname: ${HOSTNAME_IN}
    ip: ${IP_IN}
EOF2

echo "Registered Windows host:"
echo "$HOSTNAME_IN $IP_IN"
