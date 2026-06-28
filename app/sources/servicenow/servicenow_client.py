import os

import requests


SN_INSTANCE = os.getenv("SERVICENOW_INSTANCE", "").rstrip("/")
SN_USERNAME = os.getenv("SERVICENOW_USERNAME") or os.getenv("SERVICENOW_USER", "")
SN_PASSWORD = os.getenv("SERVICENOW_PASSWORD", "")


def _auth():
    return (SN_USERNAME, SN_PASSWORD)


def _headers():
    return {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


def _check_config():
    return all([SN_INSTANCE, SN_USERNAME, SN_PASSWORD])


def _record_link(table: str, sys_id: str):
    return f"{SN_INSTANCE}/{table}.do?sys_id={sys_id}"


def _is_ip(value: str) -> bool:
    parts = value.split(".")

    if len(parts) != 4:
        return False

    try:
        return all(0 <= int(part) <= 255 for part in parts)
    except ValueError:
        return False


def resolve_ci(identifier: str) -> dict:
    """
    Resolve a CI by hostname/name or IP address.
    """

    if not _check_config():
        return {
            "found": False,
            "error": "ServiceNow environment variables are not configured",
        }

    identifier = identifier.strip()

    if _is_ip(identifier):
        query = f"ip_address={identifier}"
    else:
        query = f"name={identifier}"

    url = f"{SN_INSTANCE}/api/now/table/cmdb_ci_server"

    params = {
        "sysparm_query": query,
        "sysparm_limit": "1",
        "sysparm_fields": (
            "sys_id,name,ip_address,os,location,"
            "short_description,sys_updated_on"
        ),
    }

    response = requests.get(
        url,
        auth=_auth(),
        headers=_headers(),
        params=params,
        timeout=20,
    )

    response.raise_for_status()

    results = response.json().get("result", [])

    if not results:
        return {
            "found": False,
            "identifier": identifier,
            "message": "CI not found in ServiceNow CMDB",
        }

    ci = results[0]
    ci["link"] = _record_link("cmdb_ci_server", ci["sys_id"])

    return {
        "found": True,
        "identifier": identifier,
        "cmdb_record": ci,
    }


def get_ci_summary(identifier: str) -> dict:
    """
    Return CI summary by hostname OR IP address.

    Includes:
    - CMDB CI record
    - incidents from last 30 days
    """

    resolved = resolve_ci(identifier)

    if not resolved.get("found"):
        return {
            "ci_name": identifier,
            "found": False,
            "message": "CI not found in ServiceNow CMDB",
            "cmdb_record": None,
            "incidents_last_30_days": [],
        }

    ci = resolved["cmdb_record"]
    ci_name = ci.get("name")

    incident_url = f"{SN_INSTANCE}/api/now/table/incident"

    incident_query = (
        f"cmdb_ci={ci.get('sys_id')}^"
        f"sys_created_on>=javascript:gs.daysAgoStart(30)"
    )

    incident_params = {
        "sysparm_query": incident_query,
        "sysparm_limit": "10",
        "sysparm_fields": (
            "sys_id,number,short_description,state,"
            "priority,impact,urgency,sys_created_on,"
            "sys_updated_on"
        ),
    }

    incident_response = requests.get(
        incident_url,
        auth=_auth(),
        headers=_headers(),
        params=incident_params,
        timeout=20,
    )

    incident_response.raise_for_status()

    incidents = incident_response.json().get("result", [])

    for incident in incidents:
        incident["link"] = _record_link(
            "incident",
            incident["sys_id"],
        )

    return {
        "ci_name": ci_name,
        "requested_identifier": identifier,
        "found": True,
        "cmdb_record": ci,
        "incidents_last_30_days": incidents,
    }


def get_servicenow_ci_summary(identifier: str) -> dict:
    return get_ci_summary(identifier)
