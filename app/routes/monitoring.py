from fastapi import APIRouter, Query

from app.tools.prometheus_client import get_linux_host_summary
from app.tools.servicenow_client import resolve_ci


router = APIRouter(prefix="/tools/monitoring", tags=["monitoring"])


@router.get("/ci-summary")
def ci_monitoring_summary(
    identifier: str = Query(..., description="CI name or IP address")
):
    ci_result = resolve_ci(identifier)

    if not ci_result.get("found"):
        return {
            "identifier": identifier,
            "found": False,
            "message": "CI not found in ServiceNow CMDB",
        }

    ci = ci_result["cmdb_record"]
    ip_address = ci.get("ip_address")

    if not ip_address:
        return {
            "identifier": identifier,
            "found": True,
            "cmdb_record": ci,
            "monitoring": None,
            "message": "CI found, but no IP address is available in CMDB",
        }

    monitoring = get_linux_host_summary(ip_address)

    return {
        "identifier": identifier,
        "found": True,
        "cmdb_record": ci,
        "monitoring": monitoring,
    }


@router.get("/linux-summary")
def linux_summary(ip: str = Query(..., description="Linux host private IP")):
    return get_linux_host_summary(ip)
