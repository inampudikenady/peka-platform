#!/bin/bash
set -euo pipefail

HOSTNAME_IN="$1"
IP_IN="$2"
STOCK="/opt/peka/monitoring/targets/peka-stock.yml"

if grep -q "hostname: ${HOSTNAME_IN}" "$STOCK"; then
  echo "Host already exists in stock: ${HOSTNAME_IN}"
  exit 0
fi

awk -v host="$HOSTNAME_IN" -v ip="$IP_IN" '
  /^windows:/ && !inserted {
    print "  - hostname: " host
    print "    ip: " ip
    inserted=1
  }
  { print }
' "$STOCK" > /tmp/peka-stock.yml

mv /tmp/peka-stock.yml "$STOCK"

echo "Registered Linux host:"
echo "$HOSTNAME_IN $IP_IN"
