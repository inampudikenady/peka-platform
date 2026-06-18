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

from app.routing.source_router import route_sources

from app.sources.metrics.context_health import build_health_context
from app.sources.cmdb.context_inventory import build_inventory_context
from app.sources.logs.context_logs import build_logs_context
from app.sources.tickets.context_tickets import build_ticket_context


CURRENT_QUESTION = ""


def build_operational_context(question: str):
    global CURRENT_QUESTION

    CURRENT_QUESTION = question

    route = route_sources(question)
    intent = route["intent"]
    identifier = route.get("identifier")
    sources = route["sources"]

    context_parts = []

    # Docs-only and Azure-only questions do not need operational context here.
    # Docs are handled by RAG retrieval.
    # Azure will be handled by app/sources/azure later.
    if sources.get("docs") or sources.get("azure"):
        return "", intent

    if not identifier:
        return "", intent

    if sources.get("cmdb"):
        context_parts.append(build_inventory_context(identifier))

    if sources.get("metrics"):
        context_parts.append(build_health_context(identifier))

    if sources.get("logs"):
        context_parts.append(build_logs_context(identifier, question))

    if sources.get("tickets"):
        context_parts.append(build_ticket_context(identifier))

    context = "\n\n".join(part for part in context_parts if part)

    return context, intent


def enrich_question_with_operational_context(question: str):
    context, intent = build_operational_context(question)

    if not context:
        return question

    if intent == "operational_health":
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

    elif intent == "ticket_history":
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

**CI:** CI_NAME
**IP Address:** IP_ADDRESS

## Log Search

- Search term: LOG_SEARCH
- Matches in last 2 hours: LOG_COUNT_LAST_2H

## Notable Log Entries

If LOG_COUNT_LAST_2H is 0, say:
No matching logs found in the last 2 hours.

If logs exist, summarize important logs/events in readable operator language.

For Windows events include:
- source
- event ID
- level
- message

Do not show CI_LINK if it is empty.
Do not show placeholder text.
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

    elif intent.startswith("inventory_field_"):
        field_name = intent.replace("inventory_field_", "").upper()

        label_map = {
            "OWNER": "Owner",
            "IP_ADDRESS": "IP Address",
            "APPLICATION": "Application",
            "CRITICALITY": "Criticality",
            "ENVIRONMENT": "Environment",
            "OS": "OS",
            "PATCH_GROUP": "Patch Group",
        }

        label = label_map.get(field_name, field_name.replace("_", " ").title())

        format_instruction = f"""
The user is asking for one specific CI inventory field.

Return exactly one line in this format:

{label}: VALUE

Use only the value from {field_name}.
No heading.
No explanation.
No extra fields.
If the value is missing, say:
{label}: Not found
"""

    else:
        format_instruction = """
The user is asking for a CI inventory overview.

Use only inventory fields from the operational context.
Do not include tickets.
Do not include logs.
Do not include metrics.
Do not invent missing values.

Format exactly like this:

# CI Overview - CI_NAME

**CI:** [CI_NAME](CI_LINK)
**IP Address:** IP_ADDRESS
**OS:** OS
**Application:** APPLICATION
**Owner:** OWNER
**Environment:** ENVIRONMENT
**Criticality:** CRITICALITY
**Patch Group:** PATCH_GROUP
**Description:** DESCRIPTION

Only include fields that exist in the context.
If CI_LINK is empty, show CI_NAME as plain text, not a broken markdown link.
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