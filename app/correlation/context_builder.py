"""
context_builder.py

Purpose:
    Orchestrate PEKA operational context enrichment.

Flow:
    1. Detect user intent
    2. Extract CI hostname or IP address
    3. Route to the correct context builder:
       - inventory / CI details
       - ticket history
       - health / metrics / logs / tickets
       - logs
       - docs with live context
    4. Build a final enriched prompt for the RAG engine

This module should stay light.
Provider-specific logic belongs in dedicated modules.
"""

from app.routing.intent_detector import (
    detect_intent,
    extract_identifier,
)

from app.sources.metrics.context_health import build_health_context
from app.sources.cmdb.context_inventory import build_inventory_context
from app.sources.logs.context_logs import build_logs_context
from app.sources.tickets.context_tickets import build_ticket_context


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
        context = f"""
{build_inventory_context(identifier)}

{build_ticket_context(identifier)}
"""
        return context, intent

    if intent == "logs":
        return build_logs_context(identifier, question), intent

    if intent == "docs":
        return build_health_context(identifier), intent

    context = f"""
{build_inventory_context(identifier)}

{build_ticket_context(identifier)}
"""
    return context, intent


def enrich_question_with_operational_context(question: str):
    context, intent = build_operational_context(question)

    if not context:
        return question

    if intent == "health":
     format_instruction = """
The user is asking about server health or performance.

Use only the operational context as evidence.
Do not use document sources.
Do not invent missing values.
Do not perform correlation.

Return only the final answer. Do not repeat these instructions.

Format:

# Server Health Check - CI_NAME

## 1. CI Details

- CI link: CI_LINK
- IP address: IP_ADDRESS
- OS: OS
- Description: DESCRIPTION

## 2. Runtime Status

For Docker/container mode include:
- Node status: NODE_STATUS
- Container state: CONTAINER_STATE
- Container running: CONTAINER_RUNNING
- Container status: CONTAINER_STATUS
- Container ID: CONTAINER_ID

For VM mode include:
- Node status: NODE_STATUS
- Uptime hours: UPTIME_HOURS
- Uptime days: UPTIME_DAYS
- Load average 1m: LOAD_AVERAGE_1M
- Load average 5m: LOAD_AVERAGE_5M
- Load average 15m: LOAD_AVERAGE_15M

Only include fields that exist in the context.

## 3. Current Metrics

For Docker/container mode include:
- CPU percent: CPU_PERCENT
- Memory used MB: MEMORY_USED_MB
- Memory working set MB: MEMORY_WORKING_SET_MB

For VM mode include:
- CPU percent: CPU_PERCENT
- Memory total GB: MEMORY_TOTAL_GB
- Memory used GB: MEMORY_USED_GB
- Memory available GB: MEMORY_AVAILABLE_GB
- Memory used percent: MEMORY_USED_PERCENT
- Filesystems
- Top CPU processes
- Top memory processes

Only include fields that exist in the context.

## 4. Logs - Last 2 Hours

Use the Logs Last 2 Hours section.
If no actionable logs are present, say:
No actionable error logs found in the last 2 hours.

## 5. Tickets - Last 30 Days

If HAS_TICKETS is true, list every TICKET_MARKDOWN line.
If HAS_TICKETS is false, say:
No tickets were found in the last 30 days.

## Summary

Write exactly 3 bullets:
- Current state: summarize current status and metrics.
- Logs: summarize log status.
- Tickets: summarize ticket status.

Do not mention:
- RAG
- vector DB
- JSON
- operational context
- provided context
- format instructions
"""

    elif intent == "history":
        format_instruction = """
The user is asking about ticket or incident history.

Format exactly like this:

# Ticket History - CI_NAME

**CI:** [CI_NAME](CI_LINK)
**IP Address:** IP_ADDRESS

## Related Tickets - Last 30 Days

If HAS_TICKETS is true, copy every TICKET_MARKDOWN line exactly.

If HAS_TICKETS is false, say:
No tickets were found in the last 30 days.

Do not rewrite CI_NAME.
Do not rewrite ticket numbers.
Do not remove ticket hyperlinks.
Do not output placeholder text.
Do not infer impact from tickets.
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

## Related Tickets - Last 30 Days

If HAS_TICKETS is true, copy every TICKET_MARKDOWN line exactly.

If HAS_TICKETS is false, say:
No tickets were found in the last 30 days.

Do not rewrite CI_NAME.
Do not rewrite ticket numbers.
Do not remove ticket hyperlinks.
Do not output placeholder text.
Do not infer impact from tickets.
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