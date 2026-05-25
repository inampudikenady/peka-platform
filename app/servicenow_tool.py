import os
from datetime import datetime, timedelta, timezone
import requests
from requests.auth import HTTPBasicAuth


SN_INSTANCE = os.getenv("SERVICENOW_INSTANCE")
SN_USER = os.getenv("SERVICENOW_USER")
SN_PASSWORD = os.getenv("SERVICENOW_PASSWORD")


def _headers():
    return {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


def _auth():
    return HTTPBasicAuth(SN_USER, SN_PASSWORD)


def get_ci_summary(ci_name: str) -> dict:
    if not all([SN_INSTANCE, SN_USER, SN_PASSWORD]):
        return {"error": "ServiceNow environment variables are not configured"}

    ci_url = f"{SN_INSTANCE}/api/now/table/cmdb_ci_server"
    ci_params = {
        "sysparm_query": f"name={ci_name}",
        "sysparm_limit": "1",
        "sysparm_fields": "sys_id,name,ip_address,os,location,short_description,sys_updated_on",
    }

    ci_resp = requests.get(ci_url, auth=_auth(), headers=_headers(), params=ci_params, timeout=20)
    ci_resp.raise_for_status()

    ci_results = ci_resp.json().get("result", [])
    if not ci_results:
        return {
            "ci_name": ci_name,
            "found": False,
            "message": "CI not found in ServiceNow CMDB",
            "incidents_last_30_days": [],
        }

    ci = ci_results[0]
    ci_sys_id = ci["sys_id"]

    since = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")

    inc_url = f"{SN_INSTANCE}/api/now/table/incident"
    inc_params = {
        "sysparm_query": f"cmdb_ci={ci_sys_id}^sys_created_on>={since}",
        "sysparm_limit": "10",
        "sysparm_fields": "number,short_description,state,priority,impact,urgency,sys_created_on,sys_updated_on",
        "sysparm_order_by": "sys_created_on",
    }

    inc_resp = requests.get(inc_url, auth=_auth(), headers=_headers(), params=inc_params, timeout=20)
    inc_resp.raise_for_status()

    return {
        "ci_name": ci_name,
        "found": True,
        "cmdb_record": ci,
        "incidents_last_30_days": inc_resp.json().get("result", []),
    }
