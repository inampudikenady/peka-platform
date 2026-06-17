import json
import os
import time

import requests


LOKI_URL = os.getenv("LOKI_URL", "http://localhost:3100").rstrip("/")


def _normalize_log_line(line: str) -> dict:
    """
    Normalize Linux plain text logs and Windows Event JSON logs.
    """

    # Windows Event logs from promtail come as JSON strings.
    try:
        event = json.loads(line)

        if isinstance(event, dict) and "channel" in event:
            return {
                "type": "windows_event",
                "channel": event.get("channel"),
                "computer": event.get("computer"),
                "event_id": event.get("event_id"),
                "level": event.get("levelText"),
                "source": event.get("source"),
                "time_created": event.get("timeCreated"),
                "user": (
                    event.get("security", {}).get("userName")
                    if isinstance(event.get("security"), dict)
                    else None
                ),
                "message": event.get("message") or event.get("event_data"),
                "raw": line,
            }

    except Exception:
        pass

    # Linux/syslog/raw fallback.
    return {
        "type": "text_log",
        "message": line,
        "raw": line,
    }


def query_logs(host: str, search: str = "", hours: int = 24, limit: int = 50):
    end_ns = int(time.time() * 1_000_000_000)
    start_ns = end_ns - (hours * 60 * 60 * 1_000_000_000)

    logql = f'{{host="{host}"}}'

    if search:
        logql += f' |= "{search}"'

    url = f"{LOKI_URL}/loki/api/v1/query_range"

    response = requests.get(
        url,
        params={
            "query": logql,
            "start": start_ns,
            "end": end_ns,
            "limit": limit,
            "direction": "backward",
        },
        timeout=20,
    )

    response.raise_for_status()

    data = response.json().get("data", {}).get("result", [])

    logs = []

    for stream in data:
        labels = stream.get("stream", {})

        for ts, line in stream.get("values", []):
            normalized = _normalize_log_line(line)

            logs.append(
                {
                    "timestamp_ns": ts,
                    "host": labels.get("host"),
                    "job": labels.get("job"),
                    "filename": labels.get("filename"),
                    "channel": labels.get("channel"),
                    "normalized": normalized,
                    "line": normalized.get("message") or line,
                    "raw_line": line,
                }
            )

    return {
        "host": host,
        "search": search,
        "hours": hours,
        "count": len(logs),
        "logs": logs,
    }


def query_errors(host: str, hours: int = 24, limit: int = 50):
    return query_logs(
        host=host,
        search="error",
        hours=hours,
        limit=limit,
    )
