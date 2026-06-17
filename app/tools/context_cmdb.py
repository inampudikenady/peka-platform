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

import os
from dotenv import load_dotenv

from app.tools.servicenow_client import get_ci_summary
from app.tools.cmdb_csv import get_ci

load_dotenv()

CMDB_PROVIDER = os.getenv("CMDB_PROVIDER", "servicenow").lower()


def build_cmdb_context(identifier: str):

    if CMDB_PROVIDER == "csv":
        return build_csv_cmdb_context(identifier)

    return build_servicenow_cmdb_context(identifier)


def build_csv_cmdb_context(identifier: str):

    ci = get_ci(identifier)

    if not ci:
        return f"""
===== Local CMDB Context =====

CI not found in local CMDB for:
{identifier}
"""

    return f"""
===== Local CMDB Context =====

CI_NAME: {ci.get("ci_name")}
HOSTNAME: {ci.get("hostname")}
IP_ADDRESS: {ci.get("ip")}
APPLICATION: {ci.get("application")}
OWNER: {ci.get("owner")}
ENVIRONMENT: {ci.get("environment")}
OS_TYPE: {ci.get("os_type")}
CRITICALITY: {ci.get("criticality")}
PATCH_GROUP: {ci.get("patch_group")}
NOTES: {ci.get("notes")}
"""


def build_servicenow_cmdb_context(identifier: str):

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