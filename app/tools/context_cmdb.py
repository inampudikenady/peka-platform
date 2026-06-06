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
