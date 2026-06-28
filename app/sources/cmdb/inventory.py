"""
Provider-aware CMDB inventory access.

All non-provider modules should use this module instead of importing a
specific CMDB backend directly.
"""

from app.config import settings
from app.sources.cmdb.cmdb_csv import get_ci
from app.sources.servicenow.servicenow_client import get_ci_summary, resolve_ci


def _csv_record(row: dict, identifier: str) -> dict:
    return {
        "sys_id": "",
        "name": row.get("ci_name"),
        "link": "",
        "ip_address": row.get("ip"),
        "os": row.get("os_type"),
        "short_description": row.get("notes"),
        "location": row.get("location"),
        "application": row.get("application"),
        "owner": row.get("owner"),
        "environment": row.get("environment"),
        "criticality": row.get("criticality"),
        "patch_group": row.get("patch_group"),
        "monitoring_host": row.get("monitoring_host"),
        "requested_identifier": identifier,
        "raw": row,
    }


def _csv_not_found(identifier: str) -> dict:
    return {
        "found": False,
        "provider": "csv",
        "identifier": identifier,
        "message": "CI not found in local CMDB",
        "cmdb_record": None,
    }


def _servicenow_not_found(identifier: str) -> dict:
    return {
        "found": False,
        "provider": "servicenow",
        "identifier": identifier,
        "message": "CI not found in ServiceNow CMDB",
        "cmdb_record": None,
    }


def resolve_inventory(identifier: str) -> dict:
    """
    Resolve a CI using the configured CMDB provider.

    CMDB_PROVIDER=csv        -> local CSV only
    CMDB_PROVIDER=servicenow -> ServiceNow only
    """
    provider = settings["cmdb_provider"]

    if provider == "csv":
        row = get_ci(identifier)

        if not row:
            return _csv_not_found(identifier)

        return {
            "found": True,
            "provider": "csv",
            "identifier": identifier,
            "cmdb_record": _csv_record(row, identifier),
        }

    if provider == "servicenow":
        resolved = resolve_ci(identifier)
        resolved["provider"] = "servicenow"
        return resolved

    raise RuntimeError(f"Unsupported CMDB provider: {provider}")


def get_inventory_summary(identifier: str) -> dict:
    """
    Return provider-aware CI summary.

    ServiceNow includes incident data from its provider implementation.
    CSV returns inventory only and an empty incident list.
    """
    provider = settings["cmdb_provider"]

    if provider == "csv":
        resolved = resolve_inventory(identifier)

        if not resolved.get("found"):
            return {
                **resolved,
                "ci_name": identifier,
                "incidents_last_30_days": [],
            }

        ci = resolved["cmdb_record"]
        return {
            **resolved,
            "ci_name": ci.get("name"),
            "requested_identifier": identifier,
            "incidents_last_30_days": [],
        }

    if provider == "servicenow":
        summary = get_ci_summary(identifier)
        summary["provider"] = "servicenow"
        return summary

    raise RuntimeError(f"Unsupported CMDB provider: {provider}")
