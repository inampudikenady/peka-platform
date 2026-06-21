"""
context_logs.py

Purpose:
    Build Loki log context for a CI.

Responsibilities:
    - Resolve CI to hostname/IP
    - Detect log search intent from the question
    - Detect requested time window
    - Query Loki for recent logs
    - Convert log results into structured prompt context
"""

import re

from app.sources.servicenow.servicenow_client import resolve_ci
from app.sources.logs.loki_client import query_logs


def extract_log_search(question: str, identifier: str) -> str:
    q = question.strip()
    q_lower = q.lower()

    # Explicit search phrase support:
    # "search logs for database timeout on linux-demo-002"
    marker = "search logs for "
    if marker in q_lower:
        start = q_lower.find(marker) + len(marker)
        phrase = q[start:]

        stop_words = [
            f" on {identifier.lower()}",
            f" from {identifier.lower()}",
            f" for {identifier.lower()}",
        ]

        for stop_word in stop_words:
            idx = phrase.lower().find(stop_word)
            if idx != -1:
                phrase = phrase[:idx]

        return phrase.strip()

    # Generic category search.
    if "login" in q_lower or "auth" in q_lower or "authentication" in q_lower:
        return "login"

    if "database" in q_lower or "db" in q_lower:
        return "database"

    if "cpu" in q_lower:
        return "cpu"

    if "memory" in q_lower or "mem" in q_lower:
        return "memory"

    if "restart" in q_lower or "reboot" in q_lower:
        return "restart"

    if "failed" in q_lower or "failure" in q_lower:
        return "fail"

    if "error" in q_lower or "errors" in q_lower:
        return "error"

    if "warn" in q_lower or "warning" in q_lower:
        return "warn"

    if "sudo" in q_lower:
        return "sudo"

    # No filter: show recent logs.
    return ""


def extract_log_hours(question: str, default_hours: int = 2) -> int:
    q = question.lower()

    patterns = [
        r"last\s+(\d+)\s*hours?",
        r"past\s+(\d+)\s*hours?",
        r"previous\s+(\d+)\s*hours?",
        r"last\s+(\d+)\s*h\b",
        r"past\s+(\d+)\s*h\b",
    ]

    for pattern in patterns:
        match = re.search(pattern, q)
        if match:
            hours = int(match.group(1))
            return max(1, min(hours, 24))

    if "last day" in q or "past day" in q or "24 hours" in q:
        return 24

    if "12 hours" in q:
        return 12

    return default_hours


def build_logs_context(identifier: str, question: str = ""):
    resolved = resolve_ci(identifier)

    if resolved.get("found"):
        ci = resolved.get("cmdb_record", {})
        host = ci.get("name")
    else:
        ci = {
            "name": identifier,
            "link": "",
            "ip_address": "",
        }
        host = identifier

    search = extract_log_search(question, identifier)
    hours = extract_log_hours(question)

    logs = query_logs(
        host=host,
        search=search,
        hours=hours,
        limit=50,
    )

    sample_logs_text = ""

    for log in logs.get("logs", [])[:20]:
        normalized = log.get("normalized", {}) or {}

        if normalized.get("type") == "windows_event":
            sample_logs_text += f"""
EVENT_SOURCE: {normalized.get("source")}
EVENT_ID: {normalized.get("event_id")}
LEVEL: {normalized.get("level")}
USER: {normalized.get("user")}
MESSAGE: {normalized.get("message")}
"""
        else:
            sample_logs_text += f"""
LOG_FILE: {log.get("filename")}
LOG_LINE: {log.get("line")}
"""

    if not sample_logs_text:
        sample_logs_text = f"No matching logs found in the last {hours} hours.\n"

    search_display = search if search else "all logs"

    return f"""
===== Logs Context =====

CI_NAME: {ci.get("name")}
CI_LINK: {ci.get("link")}
IP_ADDRESS: {ci.get("ip_address")}

LOG_SEARCH: {search_display}
LOG_WINDOW_HOURS: {hours}
LOG_COUNT: {logs.get("count")}
LOG_COUNT_LAST_2H: {logs.get("count") if hours == 2 else "not_applicable"}

SAMPLE_LOGS:
{sample_logs_text}
"""
