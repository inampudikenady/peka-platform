"""
context_cmdb.py

Purpose:
    Retrieve Configuration Item (CI) information and related incidents
    from the configured CMDB provider and convert them into structured
    context that PEKA can inject into the LLM prompt.

Supported Providers:
    - ServiceNow
    - Local CSV CMDB

Used By:
    context_builder.py

Flow:
    User Question
         |
         v
    extract_identifier()
         |
         v
    build_cmdb_context()
         |
         v
    CMDB Provider
         |
         v
    Structured Prompt Context
"""

from app.sources.cmdb.inventory import get_inventory_summary, resolve_inventory


def build_cmdb_context(identifier: str):
    data = resolve_inventory(identifier)
    provider = data.get("provider")

    if provider == "csv":
        return build_csv_cmdb_context(identifier)

    if provider == "servicenow":
        return build_servicenow_cmdb_context(identifier)

    raise RuntimeError(f"Unsupported CMDB provider: {provider}")


def build_csv_cmdb_context(identifier: str):
    data = resolve_inventory(identifier)
    ci = data.get("cmdb_record", {}) or {}

    if not data.get("found"):
        return f"""
===== Local CMDB Context =====

CI not found in local CMDB for:
{identifier}
"""

    return f"""
===== Local CMDB Context =====

CI_NAME: {ci.get("name")}
HOSTNAME: {ci.get("monitoring_host")}
IP_ADDRESS: {ci.get("ip_address")}
APPLICATION: {ci.get("application")}
OWNER: {ci.get("owner")}
ENVIRONMENT: {ci.get("environment")}
OS_TYPE: {ci.get("os")}
CRITICALITY: {ci.get("criticality")}
PATCH_GROUP: {ci.get("patch_group")}
NOTES: {ci.get("short_description")}
"""


def build_servicenow_cmdb_context(identifier: str):
    data = get_inventory_summary(identifier)

    if data.get("provider") != "servicenow":
        return build_cmdb_context(identifier)

    if not data.get("found"):
        return f"""
===== ServiceNow CMDB Context =====

CI not found in ServiceNow for:
{identifier}
"""

    cmdb = data.get("cmdb_record", {})
    incidents = data.get("incidents_last_30_days", [])
    incident_count = len(incidents)
    has_incidents = incident_count > 0

    context = f"""
===== ServiceNow CMDB Context =====

CI_NAME: {cmdb.get("name")}
CI_LINK: {cmdb.get("link")}
IP_ADDRESS: {cmdb.get("ip_address")}
CMDB_OS: {cmdb.get("os")}
DESCRIPTION: {cmdb.get("short_description")}
LOCATION: {cmdb.get("location")}

INCIDENT_COUNT_30D: {incident_count}
HAS_INCIDENTS: {str(has_incidents).lower()}
"""

    if incidents:
        context += "\n===== Related Incidents Last 30 Days =====\n"

        for inc in incidents:
            context += f"""
INC_NUMBER: {inc.get("number")}
INC_LINK: {inc.get("link")}
SHORT_DESCRIPTION: {inc.get("short_description")}
INCIDENT_MARKDOWN: - [{inc.get("number")}]({inc.get("link")}) - {inc.get("short_description")}
"""

    else:
        context += "\nNO_INCIDENTS_FOUND: true\n"

    return context
