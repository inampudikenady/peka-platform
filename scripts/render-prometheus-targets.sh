#!/bin/bash
set -euo pipefail

STOCK="/opt/peka/monitoring/targets/peka-stock.yml"

LINUX_OUT="/opt/peka/monitoring/prometheus/linux-targets.yml"
PROCESS_OUT="/opt/peka/monitoring/prometheus/linux-process-targets.yml"
WINDOWS_OUT="/opt/peka/monitoring/prometheus/windows-targets.yml"

: > "$LINUX_OUT"
: > "$PROCESS_OUT"
: > "$WINDOWS_OUT"

awk '
  /^linux:/ {section="linux"; next}
  /^windows:/ {section="windows"; next}

  /hostname:/ {
    hostname=$3
    gsub("\"","",hostname)
  }

  /ip:/ {
    ip=$2
    gsub("\"","",ip)

    if (section=="linux") {
      print "- targets: [\"" ip ":9100\"]\n  labels:\n    host: \"" hostname "\"\n    os: \"linux\"" >> linux_out
      print "- targets: [\"" ip ":9256\"]\n  labels:\n    host: \"" hostname "\"\n    os: \"linux\"" >> process_out
    }

    if (section=="windows") {
      print "- targets: [\"" ip ":9182\"]\n  labels:\n    host: \"" hostname "\"\n    os: \"windows\"" >> windows_out
    }
  }
' linux_out="$LINUX_OUT" process_out="$PROCESS_OUT" windows_out="$WINDOWS_OUT" "$STOCK"

echo "Rendered:"
echo "$LINUX_OUT"
echo "$PROCESS_OUT"
echo "$WINDOWS_OUT"
