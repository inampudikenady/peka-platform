"""
context_health.py

Purpose:
    Build a simple operational health context for a CI.

Flow for health questions:
    1. Get CI details and incidents from ServiceNow
    2. Get metrics from Prometheus
    3. Get logs from Loki for the last 2 hours
    4. Reduce log noise by grouping repeated error lines

This module does not perform correlation yet.
Correlation between alerts, incidents, logs, and changes is future roadmap.
"""

from collections import Counter
import re

from app.routes import monitoring
from app.tools.operational_analysis import analyze_ci
from app.tools.context_cmdb import build_cmdb_context


def _normalize_log_line(line: str) -> str:
    """
    Normalize noisy log lines so repeated errors can be grouped.

    Removes timestamps, ports, request IDs, websocket keys, and other
    values that change every time but represent the same error pattern.
    """
    if not line:
        return ""

    normalized = line

    normalized = re.sub(r"\b\d{1,3}(?:\.\d{1,3}){3}\b", "<ip>", normalized)
    normalized = re.sub(r":\d{2,5}\b", ":<port>", normalized)
    normalized = re.sub(r'"remote_port":"?\d+"?', '"remote_port":"<port>"', normalized)
    normalized = re.sub(r'"err_id":"[^"]+"', '"err_id":"<err_id>"', normalized)
    normalized = re.sub(r'"Sec-Websocket-Key":\[[^\]]+\]', '"Sec-Websocket-Key":["<key>"]', normalized)
    normalized = re.sub(r"\d{10}(?:\.\d+)?", "<epoch>", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()

    return normalized


def _is_noise_log(line: str) -> bool:
    """
    Return True for log lines that should not be shown in health output.
    """
    if not line:
        return True

    lower = line.lower()

    noise_words = [
        " info ",
        '"level":"info"',
        "level=info",
        "debug",
        '"level":"debug"',
        "healthcheck",
        "/health",
        "/metrics",
    ]

    return any(word in lower for word in noise_words)


def _build_deduped_log_summary(logs: dict, limit: int = 5) -> str:
    """
    Build a compact deduplicated error summary from Loki sample errors.
    """
    sample_errors = logs.get("sample_errors", []) or []

    grouped = Counter()
    examples = {}

    for log in sample_errors:
        line = log.get("line") or ""

        if _is_noise_log(line):
            continue

        key = _normalize_log_line(line)

        if not key:
            continue

        grouped[key] += 1
        examples.setdefault(key, line)

    if not grouped:
        return "No actionable error logs found in the last 2 hours.\n"

    output = ""

    for key, count in grouped.most_common(limit):
        example = examples.get(key, key)

        if count > 1:
            output += f"- Repeated {count} times: {example}\n"
        else:
            output += f"- {example}\n"

    return output


def build_health_context(identifier: str):
    """
    Build health context for a hostname or IP address.

    Args:
        identifier:
            CI hostname or IP address extracted from the user's question.

    Returns:
        str:
            Structured context containing CI details, metrics, logs,
            and recent incidents.
    """
    cmdb_context = build_cmdb_context(identifier)

    analysis = analyze_ci(identifier=identifier, hours=2)

    if not analysis.get("found"):
        return f"""
{cmdb_context}

===== Operational Health Context =====

CI not found in monitoring for:
{identifier}

SUMMARY:
{analysis.get("summary")}

FINDINGS:
{analysis.get("findings")}
"""

    ci = analysis.get("ci", {}) or {}
    monitoring = analysis.get("monitoring", {}) or {}
    logs = analysis.get("logs", {}) or {}

    observed_os = monitoring.get("observed_os") or {}

    os_display = (
        observed_os.get("pretty_name")
        or observed_os.get("product")
        or ci.get("os")
        or "Unknown"
    )

    memory = monitoring.get("memory", {}) or {}
    uptime = monitoring.get("uptime", {}) or {}
    load = monitoring.get("load_average", {}) or {}

    filesystem_text = ""

    for fs in monitoring.get("filesystems", []) or []:
        filesystem_text += (
            f"- {fs.get('mountpoint')} used "
            f"{round(fs.get('used_percent', 0), 2)}%\n"
        )

    if not filesystem_text:
        filesystem_text = "No filesystem metrics available.\n"

    top_cpu_text = ""

    for proc in (monitoring.get("top_cpu_processes", []) or [])[:5]:
        top_cpu_text += (
            f"- {proc.get('process')} approx "
            f"{round(proc.get('cpu_percent_estimate', 0), 2)}%\n"
        )

    if not top_cpu_text:
        top_cpu_text = "No process CPU metrics available.\n"

    top_mem_text = ""

    for proc in (monitoring.get("top_memory_processes", []) or [])[:5]:
        mem_gb = round(
            (proc.get("memory_bytes", 0) or 0)
            / 1024 / 1024 / 1024,
            2
        )

        top_mem_text += (
            f"- {proc.get('process')} approx {mem_gb} GB\n"
        )

    if not top_mem_text:
        top_mem_text = "No process memory metrics available.\n"

    log_summary = _build_deduped_log_summary(logs, limit=5)

    return f"""
{cmdb_context}

===== Operational Health Context =====

CI_NAME: {ci.get("name")}
CI_LINK: {ci.get("link")}
IP_ADDRESS: {ci.get("ip_address")}
OS: {os_display}
DESCRIPTION: {ci.get("short_description")}

===== Host Status =====

UPTIME_HOURS: {uptime.get("hours")}
UPTIME_DAYS: {uptime.get("days")}

LOAD_AVERAGE_1M: {load.get("load1")}
LOAD_AVERAGE_5M: {load.get("load5")}
LOAD_AVERAGE_15M: {load.get("load15")}

===== Metrics Snapshot =====

NODE_STATUS: {monitoring.get("status")}
CPU_PERCENT: {monitoring.get("cpu_percent")}

MEMORY_TOTAL_GB: {memory.get("total_gb")}
MEMORY_USED_GB: {memory.get("used_gb")}
MEMORY_AVAILABLE_GB: {memory.get("available_gb")}
MEMORY_USED_PERCENT: {memory.get("used_percent")}

FILESYSTEMS:
{filesystem_text}

TOP_CPU_PROCESSES:
{top_cpu_text}

TOP_MEMORY_PROCESSES:
{top_mem_text}

===== Logs Last 2 Hours =====

{log_summary}

===== Health Flow Note =====

This health check is evidence-only.
Do not infer incident/log/change correlation.
Do not claim an incident was caused by a log or metric.
"""