"""
context_builder.py

Purpose:
    Orchestrate PEKA operational context enrichment.

Flow:
    1. Detect user intent
    2. Extract CI hostname or IP address
    3. Route to the correct context builder:
       - CMDB / incident history
       - health / metrics / logs
       - logs
       - docs with live context
    4. Build a final enriched prompt for the RAG engine

This module should stay light.
ServiceNow, Prometheus, and Loki logic belongs in dedicated modules.
"""

from app.tools.intent_detector import (
    detect_intent,
    extract_identifier,
)

from app.tools.context_cmdb import build_cmdb_context
from app.tools.context_health import build_health_context
from app.tools.context_logs import build_logs_context

CURRENT_QUESTION = ""

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
        return build_logs_context(identifier, question), intent
    
    if intent == "docs":
        return build_health_context(identifier), intent

    return build_cmdb_context(identifier), intent


def enrich_question_with_operational_context(question: str):
    context, intent = build_operational_context(question)

    if not context:
        return question

    if intent == "health":
        format_instruction = """
The user is asking about server health or performance.

Use the context as evidence only.

Do not perform advanced correlation yet.
Do not claim an incident was caused by a metric.
Do not claim a log caused an incident.
Do not claim a change caused an incident.
Do not invent root cause.

Format exactly like this:

# Server Health Check - CI_NAME

## 1. CI Details

Show:
- CI link
- IP address
- OS
- description

## 2. Host Status

Show exact values if present:
- uptime hours
- uptime days
- load average 1m
- load average 5m
- load average 15m

## 3. Current Metrics

Show exact values from the Metrics Snapshot:
- node status
- CPU percent
- memory total, used, available, and used percent
- filesystems
- top CPU processes
- top memory processes

## 4. Logs - Last 2 Hours

Use only the Logs Last 2 Hours section.

Do not dump large raw logs.
If repeated errors are shown, keep them grouped.
Ignore informational/debug logs.
If no actionable logs are present, say so.

## 5. Incidents - Last 30 Days

Rules:
- If HAS_INCIDENTS is true, copy every INCIDENT_MARKDOWN line exactly.
- If HAS_INCIDENTS is false, write exactly: No incidents were found in the last 30 days.
- Never create a heading called "## 5" without the full title.
- Do not interpret incidents.
- Do not summarize incidents.
- Do not infer impact from incidents.
- Do not output placeholder text.
- Do not remove incident hyperlinks.

## Summary

Write exactly 3 short bullet points:

- Current state: include NODE_STATUS, UPTIME_HOURS, CPU_PERCENT, MEMORY_USED_PERCENT, and load average.
- Logs: state whether Logs Last 2 Hours has actionable errors.
- Incidents: if HAS_INCIDENTS is true, write exactly "Incident history exists in the last 30 days. See section 5." If HAS_INCIDENTS is false, write exactly "No incidents were found in the last 30 days."

Do not write any summary sentence outside these 3 bullets.
Do not infer impact from incidents.
Do not correlate incidents with metrics or logs.

Do not mention:
- RAG
- vector DB
- operational context
- provided context
- JSON
"""

    elif intent == "history":
        format_instruction = """
The user is asking about incident or ticket history.

Format exactly like this:

# Incident History - CI_NAME

**CI:** [CI_NAME](CI_LINK)
**IP Address:** IP_ADDRESS

## Related Incidents - Last 30 Days

If INCIDENT_MARKDOWN exists, copy every INCIDENT_MARKDOWN line exactly.

Only say "No incidents found in the last 30 days" when NO_INCIDENTS_FOUND is explicitly present.

Do not rewrite CI_NAME.
Do not rewrite incident numbers.
Do not remove incident hyperlinks.
Do not output placeholder text.
"""

    elif intent == "logs":
        format_instruction = """
The user is asking about logs, errors, or events.

Format exactly like this:

# Log Review - CI_NAME

**CI:** [CI_NAME](CI_LINK)
**IP Address:** IP_ADDRESS

## Log Search

Show LOG_SEARCH and LOG_COUNT_LAST_2H.

## Notable Log Entries

Summarize important logs/events in readable operator language.

For Windows events include:
- source
- event ID
- level
- message

Do not dump raw JSON.
Do not mention vector DB or RAG.
"""

    elif intent == "docs":
        format_instruction = """
The user is asking for an operational action or procedure involving this CI.

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

Do not mention vector DB or RAG.
"""

    else:
        format_instruction = """
The user is asking for a CI overview.

Format exactly like this:

# CI Overview - CI_NAME

**CI:** [CI_NAME](CI_LINK)
**OS:** OS
**IP Address:** IP_ADDRESS
**Description:** DESCRIPTION

## Related Incidents - Last 30 Days

If INCIDENT_MARKDOWN exists, copy every INCIDENT_MARKDOWN line exactly.

Only say "No incidents found in the last 30 days" when NO_INCIDENTS_FOUND is explicitly present.

Do not rewrite CI_NAME.
Do not rewrite incident numbers.
Do not remove incident hyperlinks.
Do not output placeholder text.
"""

    return f"""
The user asked:

{question}

Use the following live operational context as authoritative evidence.

Do not mention:
- RAG
- vector DB
- indexed knowledge
- provided context
- JSON

Do not dump raw fields.

Answer based on the user intent and the format instructions.

Operational context:

{context}

{format_instruction}
"""