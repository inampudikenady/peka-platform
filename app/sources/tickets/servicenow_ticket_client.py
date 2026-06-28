"""
ServiceNow ticket provider adapter.
"""

from app.sources.servicenow.servicenow_client import get_ci_summary


def get_incidents_for_ci(identifier: str) -> list[dict]:
    data = get_ci_summary(identifier)
    return data.get("incidents_last_30_days", []) or []
