import re

from app.tools.servicenow_client import (
    get_ci_summary,
    resolve_ci,
)

from app.tools.operational_analysis import analyze_ci
from app.tools.loki_client import query_logs


CURRENT_QUESTION = ""


def extract_identifier(question: str):
    ip_match = re.search(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", question)

    if ip_match:
        return ip_match.group(0)

    ci_match = re.search(
        r"\bpeka-dev-[a-z0-9-]+-\d{3}\b",
        question.lower()
    )

    if ci_match:
        return ci_match.group(0)

    return None


def detect_intent(question: str):
    q = question.lower()

    doc_words = [
        "patch",
        "upgrade",
        "install",
        "installation",
        "configure",
        "configuration",
        "procedure",
        "steps",
        "document",
        "documentation",
        "how do i",
        "how to",
        "runbook",
        "guide",
        "rhel",
        "ubuntu",
        "windows patch",
        "change plan",
    ]

    health_words = [
        "health",
        "status",
        "slow",
        "cpu",
        "memory",
        "mem",
        "disk",
        "filesystem",
        "process",
        "utilization",
        "usage",
        "load",
        "performance",
        "operational issue",
        "issue",
        "problem",
    ]

    history_words = [
        "incident",
        "ticket",
        "history",
        "past",
        "last 30",
        "recent issue",
    ]

    log_words = [
        "log",
        "logs",
        "error",
        "errors",
        "failed",
        "failure",
        "event",
        "events",
        "auth",
        "authentication",
        "sudo",
        "security",
        "last 24",
    ]

    if any(x in q for x in doc_words):
        return "docs"

    if any(x in q for x in health_words):
        return "health"

    if any(x in q for x in history_words):
        return "history"

    if any(x in q for x in log_words):
        return "logs"

    return "cmdb"


def build_cmdb_context(identifier: str):
    data = get_ci_summary(identifier)

    if not data.get("found"):
        return f"""
===== ServiceNow CMDB Context =====

CI not found in ServiceNow for:
{identifier}
"""

    cmdb = data.get("cmdb_record", {})
    incidents = data.get("incidents_last_30_days", [])

    context = f"""
===== ServiceNow CMDB Context =====

CI_NAME: {cmdb.get("name")}
CI_LINK: {cmdb.get("link")}
IP_ADDRESS: {cmdb.get("ip_address")}
CMDB_OS: {cmdb.get("os")}
DESCRIPTION: {cmdb.get("short_description")}
LOCATION: {cmdb.get("location")}
"""

    if incidents:
        context += "\n===== Related Incidents Last 30 Days =====\n"

        for inc in incidents:
            context += f"""
INC_NUMBER: {inc.get("number")}
INC_LINK: {inc.get("link")}
SHORT_DESCRIPTION: {inc.get("short_description")}
"""

    else:
        context += "\nNO_INCIDENTS_FOUND: true\n"

    return context


def build_health_context(identifier: str):
    analysis = analyze_ci(identifier=identifier, hours=24)

    if not analysis.get("found"):
        return f"""
===== Operational Analysis =====

CI not found for:
{identifier}

SUMMARY:
{analysis.get("summary")}

FINDINGS:
{analysis.get("findings")}
"""

    ci = analysis.get("ci", {})
    monitoring = analysis.get("monitoring", {}) or {}
    logs = analysis.get("logs", {}) or {}
    findings = analysis.get("findings", [])

    observed_os = monitoring.get("observed_os") or {}

    os_display = (
        observed_os.get("pretty_name")
        or observed_os.get("product")
        or ci.get("os")
        or "Unknown"
    )

    memory = monitoring.get("memory", {}) or {}

    filesystem_text = ""

    for fs in monitoring.get("filesystems", []) or []:
        filesystem_text += (
            f"- {fs.get('mountpoint')} used "
            f"{round(fs.get('used_percent', 0), 2)}%\n"
        )

    if not filesystem_text:
        filesystem_text = "No filesystem metrics available.\n"

    top_cpu_text = ""

    for proc in monitoring.get("top_cpu_processes", []) or []:
        top_cpu_text += (
            f"- {proc.get('process')} approx "
            f"{round(proc.get('cpu_percent_estimate', 0), 2)}%\n"
        )

    if not top_cpu_text:
        top_cpu_text = "No process CPU metrics available.\n"

    top_mem_text = ""

    for proc in monitoring.get("top_memory_processes", []) or []:
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

    findings_text = ""

    for finding in findings:
        findings_text += f"""
SEVERITY: {finding.get("severity")}
FINDING: {finding.get("finding")}
EVIDENCE: {finding.get("evidence")}
RECOMMENDATION: {finding.get("recommendation")}
"""

    sample_logs_text = ""

    for log in logs.get("sample_errors", [])[:5]:
        normalized = log.get("normalized", {}) or {}

        if normalized.get("type") == "windows_event":
            sample_logs_text += f"""
EVENT_SOURCE: {normalized.get("source")}
EVENT_ID: {normalized.get("event_id")}
LEVEL: {normalized.get("level")}
MESSAGE: {normalized.get("message")}
"""

        else:
            sample_logs_text += f"""
LOG_LINE:
{log.get("line")}
"""

    if not sample_logs_text:
        sample_logs_text = "No sample error logs found.\n"

    return f"""
===== Operational Analysis =====

CI_NAME: {ci.get("name")}
CI_LINK: {ci.get("link")}
IP_ADDRESS: {ci.get("ip_address")}
OS: {os_display}
DESCRIPTION: {ci.get("short_description")}

OVERALL_SEVERITY: {analysis.get("overall_severity")}
SUMMARY: {analysis.get("summary")}

===== Monitoring Snapshot =====

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

===== Operational Findings =====

{findings_text}

===== Sample Error Logs =====

{sample_logs_text}
"""


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


def build_logs_context(identifier: str):
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

    search = extract_log_search(CURRENT_QUESTION, identifier)

    logs = query_logs(
        host=host,
        search=search,
        hours=24,
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
        sample_logs_text = (
            "No matching logs found in the last 24 hours.\n"
        )

    return f"""
===== Logs Context =====

CI_NAME: {ci.get("name")}
CI_LINK: {ci.get("link")}
IP_ADDRESS: {ci.get("ip_address")}

LOG_SEARCH: {search}
LOG_COUNT_LAST_24H: {logs.get("count")}

SAMPLE_LOGS:
{sample_logs_text}
"""


def build_operational_context(question: str):
    global CURRENT_QUESTION

    CURRENT_QUESTION = question

    identifier = extract_identifier(question)

    if not identifier:
        return "", "none"

    intent = detect_intent(question)

    if intent == "health":
        return build_health_context(identifier), intent

    if intent == "history":
        return build_cmdb_context(identifier), intent

    if intent == "logs":
        return build_logs_context(identifier), intent

    if intent == "docs":
        return build_health_context(identifier), intent

    return build_cmdb_context(identifier), intent


def enrich_question_with_operational_context(question: str):
    context, intent = build_operational_context(question)

    if not context:
        return question

    if intent == "health":
        format_instruction = """
The user is asking about operational health/performance.

Use the operational findings as the PRIMARY source of truth.

Do NOT dump raw JSON.
Do NOT repeat every metric mechanically.
Summarize like an experienced operations engineer.

Format:

# Operational Health Summary - CI_NAME

**CI:** [CI_NAME](CI_LINK)
**IP Address:** IP_ADDRESS
**OS:** OS

## Overall Assessment

Summarize whether:
- healthy
- degraded
- warning signs
- critical condition

## Key Findings

Summarize important findings from:
- CPU
- memory
- filesystem
- logs
- incidents

## Probable Causes

Explain likely operational causes if visible.

## Recommended Actions

Summarize recommended next steps.

## Supporting Evidence

Mention:
- top processes
- notable logs
- incidents
- filesystem pressure
- repeated errors

Do NOT mention:
- vector DB
- RAG
- operational context
- provided context
- JSON
"""

    elif intent == "history":
        format_instruction = """
Format the response like this:

# Incident History - CI_NAME

**CI:** [CI_NAME](CI_LINK)
**IP Address:** IP_ADDRESS

## Related incidents in the last 30 days

- [INC_NUMBER](INC_LINK) - SHORT_DESCRIPTION

If no incidents exist, say:
No incidents found in the last 30 days.

Always render CI and incidents as markdown hyperlinks.
"""

    elif intent == "logs":
        format_instruction = """
The user is asking about logs/errors/events.

Format:

# Log Review - CI_NAME

**CI:** [CI_NAME](CI_LINK)
**IP Address:** IP_ADDRESS

## Error/Event Summary

Summarize:
- how many logs/events were found
- whether they appear actionable
- whether they appear informational/noisy

## Notable Log Entries

Summarize important logs/events in readable operator language.

For Windows events include:
- source
- event ID
- level
- message

Always render CI as a markdown hyperlink.

Do NOT:
- dump raw JSON
- mention vector DB
- mention operational context
"""

    elif intent == "docs":
        format_instruction = """
The user is asking for an operational action/procedure involving this CI.

Use live CI/monitoring context to identify:
- current host
- IP
- observed OS

Also use retrieved documentation context from the knowledge base if relevant.

Format:

# Procedure Check - CI_NAME

**CI:** [CI_NAME](CI_LINK)
**Observed OS:** OS
**IP Address:** IP_ADDRESS

## Compatibility / Reality Check

Explain whether the requested action matches the observed OS/platform.

If the user asks for RHEL guidance but the observed OS is Ubuntu,
clearly say the RHEL document may not directly apply.

## Relevant Procedure Guidance

Summarize useful procedure steps from retrieved documents.

## Sources

List document sources if provided by retrieval.

Always render CI as a markdown hyperlink.
"""

    else:
        format_instruction = """
Format the response like this:

# CI Overview - CI_NAME

**CI:** [CI_NAME](CI_LINK)
**OS:** OS
**IP Address:** IP_ADDRESS
**Description:** DESCRIPTION

## Related incidents in the last 30 days

- [INC_NUMBER](INC_LINK) - SHORT_DESCRIPTION

If no incidents exist, say:
No incidents found in the last 30 days.

Always render CI and incidents as markdown hyperlinks.
"""

    return f"""
The user asked:

{question}

Use the following live operational context as authoritative.

Do not mention:
- RAG
- vector DB
- indexed knowledge
- provided context
- JSON

Do not dump raw fields.

Answer based on user intent.

Operational context:

{context}

{format_instruction}
"""
