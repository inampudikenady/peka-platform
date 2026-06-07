"""
context_cmdb.py

Purpose:
    Retrieve Configuration Item (CI) information and related incidents
    from ServiceNow and convert them into structured context that PEKA
    can inject into the LLM prompt.

Responsibilities:
    - Query ServiceNow CMDB
    - Retrieve recent incidents for a CI
    - Build structured context for RAG enrichment

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
    ServiceNow CMDB + Incidents
         |
         v
    Structured Prompt Context
"""
from app.tools.servicenow_client import get_ci_summary


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
