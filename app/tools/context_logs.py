"""
context_logs.py

Purpose:
    Build Loki log context for a CI.

Responsibilities:
    - Resolve CI to hostname/IP using ServiceNow
    - Detect log search intent from the question
    - Query Loki for recent logs
    - Convert log results into structured prompt context

Used By:
    context_builder.py
"""

from app.tools.servicenow_client import resolve_ci
from app.tools.loki_client import query_logs


def extract_log_search(question: str, identifier: str):
    q = question.strip()
    q_lower = q.lower()

    if "error" in q_lower or "errors" in q_lower:
        return "error"

    if "failed" in q_lower or "failure" in q_lower:
        return "fail"

    if "auth" in q_lower or "authentication" in q_lower:
        return "auth"

    if "sudo" in q_lower:
        return "sudo"

    marker = "search logs for "

    if marker in q_lower:
        start = q_lower.find(marker) + len(marker)
        phrase = q[start:]

        stop_words = [
            f" on {identifier.lower()}",
            f" from {identifier.lower()}",
        ]

        for stop_word in stop_words:
            idx = phrase.lower().find(stop_word)

            if idx != -1:
                phrase = phrase[:idx]

        return phrase.strip()

    return ""


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

    logs = query_logs(
        host=host,
        search=search,
        hours=2,
        limit=20,
    )

    sample_logs_text = ""

    for log in logs.get("logs", [])[:10]:
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
        sample_logs_text = "No matching logs found in the last 2 hours.\n"

    return f"""
===== Logs Context =====

CI_NAME: {ci.get("name")}
CI_LINK: {ci.get("link")}
IP_ADDRESS: {ci.get("ip_address")}

LOG_SEARCH: {search}
LOG_COUNT_LAST_2H: {logs.get("count")}

SAMPLE_LOGS:
{sample_logs_text}
"""