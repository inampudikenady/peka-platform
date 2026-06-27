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
from app.sources.azure.context_azure import build_azure_context


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
    if sources.get("docs"):
        return "", intent

    if sources.get("azure"):
        return build_azure_context(question), intent

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
- IP address: IP_ADDRESS
- OS: OS
- Description: DESCRIPTION

## 2. Runtime Status

Include only VM/host runtime fields from the context:
- Node exporter status
- Process exporter status, if available
- Uptime hours
- Uptime days
- Load average 1m
- Load average 5m
- Load average 15m

Do not mention Docker, containers, cAdvisor, or container mode.

## 3. Current Metrics

Include only VM/host metrics from the context:
- CPU percent
- Memory total GB
- Memory used GB
- Memory available GB
- Memory used percent
- Filesystems
- Top CPU processes
- Top memory processes

Do not mention Docker, containers, cAdvisor, or indexed knowledge.
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
- Logs: summarize only the actionable log result from section 4. If section 4 says no actionable error logs were found, do not mention older, ignored, filtered, or non-actionable log entries.
- Tickets: summarize ticket status.

Do not infer issues from ignored or filtered logs.
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

**CI:** CI_NAME
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
- Time window: last LOG_WINDOW_HOURS hours
- Matches: LOG_COUNT

## Summary

Summarize the log findings by category.
Group repeated messages together.
Do not list the same repeated error more than 3 times.
Prefer showing distinct issues over repeated duplicate lines.

Use categories such as:
- Authentication failures
- Database connectivity
- Application response/performance
- Container/runtime events
- CPU or memory warnings

## Notable Log Entries

List up to 8 distinct or representative log entries.
Do not dump all repeated logs.
If there are repeated login failures, summarize the count and show only the latest 2 examples.

If LOG_COUNT is 0, say:
No matching logs found in the selected time window.

Never show CI_LINK. Always show CI_NAME as plain text.
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

**CI:** CI_NAME
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
    elif intent == "cloud":
        format_instruction = """
The user is asking about Azure inventory, resources, virtual machines, or cost.

Use only the Azure Context as evidence.
Do not invent costs.
Do not rewrite subscription IDs. Copy exact values from Azure Context.
Do not repeat these instructions.
Do not output placeholder text.
Do not mention AZURE_QUERY_TYPE.

If AZURE_ERROR is true, format exactly:

# Azure Error

MESSAGE_FROM_AZURE

## Action Required

Run az login and confirm subscription access.

If AZURE_QUERY_TYPE is cost_month_to_date, format exactly:

# Azure Cost Summary

## Subscription

- Name: SUBSCRIPTION_NAME
- Subscription ID: SUBSCRIPTION_ID

## Month-to-Date Cost

- Actual cost: CURRENCY MONTH_TO_DATE_COST

No Details section for cost answers.

If AZURE_QUERY_TYPE is cost_breakdown_resource_group, format exactly:

# Azure Cost Breakdown

## Subscription

- Name: SUBSCRIPTION_NAME
- Subscription ID: SUBSCRIPTION_ID

## Month-to-Date Cost

- Total actual cost: CURRENCY MONTH_TO_DATE_COST

## Cost by Resource Group

List every COST_BY_RESOURCE_GROUP row with resource group and cost.

If AZURE_QUERY_TYPE is cost_breakdown_service, format exactly:

# Azure Cost by Service

## Subscription

- Name: SUBSCRIPTION_NAME
- Subscription ID: SUBSCRIPTION_ID

## Month-to-Date Cost

- Total actual cost: CURRENCY MONTH_TO_DATE_COST

## Cost by Service

List every COST_BY_SERVICE row with service name and cost.

If AZURE_QUERY_TYPE is resource_inventory, format exactly:

# Azure Resource Inventory

## Subscription

- Name: SUBSCRIPTION_NAME
- Subscription ID: SUBSCRIPTION_ID

## Summary

Summarize total resources and important categories.

## Resources

Group resources by type and list important resources.

If AZURE_QUERY_TYPE is resource_groups, format exactly:

# Azure Resource Groups

## Subscription

- Name: SUBSCRIPTION_NAME
- Subscription ID: SUBSCRIPTION_ID

## Resource Groups

List resource groups with location and status.

If AZURE_QUERY_TYPE is virtual_machines, format exactly:

# Azure Virtual Machines

## Subscription

- Name: SUBSCRIPTION_NAME
- Subscription ID: SUBSCRIPTION_ID

## Virtual Machines

List VMs with resource group, location, size, and OS type.

If AZURE_QUERY_TYPE is virtual_machine_detail, format exactly:

# Azure VM Detail - VM_NAME

## Subscription

- Name: SUBSCRIPTION_NAME
- Subscription ID: SUBSCRIPTION_ID

## VM Details

- Name: VM_NAME
- Resource Group: RESOURCE_GROUP
- Location: LOCATION
- Size: SIZE
- Power State: POWER_STATE
- Private IPs: PRIVATE_IPS
- Public IPs: PUBLIC_IPS
- OS Type: OS_TYPE

Do not infer issues from ignored or filtered logs.
Do not mention:
- RAG
- vector DB
- JSON
- operational context
- format instructions
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
    elif intent == "cloud":
        format_instruction = """
The user is asking about Azure inventory, resources, or cost.

Use only the Azure Context as evidence.
Do not invent costs.
Do not repeat these instructions.
Do not output placeholder text.
Do not mention AZURE_QUERY_TYPE.

If AZURE_ERROR is true, format exactly:

# Azure Error

MESSAGE_FROM_AZURE

## Action Required

Run az login and confirm subscription access.

If AZURE_QUERY_TYPE is cost_month_to_date, format exactly:

# Azure Cost Summary

## Subscription

- Name: SUBSCRIPTION_NAME
- Subscription ID: SUBSCRIPTION_ID

## Month-to-Date Cost

- Actual cost: CURRENCY MONTH_TO_DATE_COST

No Details section for cost answers.
Do not rewrite subscription IDs. Copy exact values from Azure Context.

If AZURE_QUERY_TYPE is resource_inventory, format exactly:

# Azure Resource Inventory

## Subscription

- Name: SUBSCRIPTION_NAME
- Subscription ID: SUBSCRIPTION_ID

## Summary

Summarize total resources and important categories.

## Resources

Group resources by type and list important resources.

If AZURE_QUERY_TYPE is resource_groups, format exactly:

# Azure Resource Groups

## Subscription

- Name: SUBSCRIPTION_NAME
- Subscription ID: SUBSCRIPTION_ID

## Resource Groups

List resource groups with location and status.

If AZURE_QUERY_TYPE is virtual_machines, format exactly:

# Azure Virtual Machines

## Subscription

- Name: SUBSCRIPTION_NAME
- Subscription ID: SUBSCRIPTION_ID

## Virtual Machines

List VMs with resource group, location, state, size, private IP, and public IP.

Do not infer issues from ignored or filtered logs.
Do not mention:
- RAG
- vector DB
- JSON
- operational context
- format instructions
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
    elif intent == "cloud":
        format_instruction = """
The user is asking about Azure inventory or cloud resources.

Use only the Azure Context as evidence.
Do not invent costs.
If cost data is not provided, clearly say cost is not available yet.

Format:

# Azure Summary

## Subscription

- Name: SUBSCRIPTION_NAME
- Subscription ID: SUBSCRIPTION_ID
- Tenant ID: TENANT_ID
- User: USER

## Summary

Summarize what was found.

## Details

If AZURE_QUERY_TYPE is cost_month_to_date:
Show month-to-date Azure cost and currency.

If AZURE_QUERY_TYPE is resource_inventory:
Group resources by type and list important resources.

If AZURE_QUERY_TYPE is resource_groups:
List resource groups with location and status.

If AZURE_QUERY_TYPE is virtual_machines:
List VMs with resource group, location, state, size, private IP, and public IP.

If AZURE_ERROR is true:
Show the Azure error message and action required.

Do not infer issues from ignored or filtered logs.
Do not mention:
- RAG
- vector DB
- JSON
- operational context
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

**CI:** CI_NAME
**IP Address:** IP_ADDRESS
**OS:** OS
**Application:** APPLICATION
**Owner:** OWNER
**Environment:** ENVIRONMENT
**Criticality:** CRITICALITY
**Patch Group:** PATCH_GROUP
**Description:** DESCRIPTION

Only include fields that exist in the context.
Always show CI_NAME as plain text. Never hyperlink CI_NAME.
"""

    return f"""
The user asked:

{question}

Use the following live operational context as authoritative evidence.

Do not infer issues from ignored or filtered logs.
Do not mention:
- RAG
- vector DB
- indexed knowledge
- provided context
- JSON

Do not dump raw fields.

Never create a hyperlink for CI_NAME. Ticket numbers may be hyperlinks, but CI names must be plain text.

Answer based on the user intent and the format instructions.

Operational context:

{context}

{format_instruction}
"""