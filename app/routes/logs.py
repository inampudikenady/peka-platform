from fastapi import APIRouter, Query

from app.sources.cmdb.inventory import resolve_inventory
from app.sources.logs.loki_client import query_logs, query_errors


router = APIRouter(prefix="/tools/logs", tags=["logs"])


@router.get("/search")
def search_logs(
    identifier: str = Query(..., description="CI name, hostname, or IP"),
    search: str = Query("", description="Text to search in logs"),
    hours: int = Query(24, description="Lookback window in hours"),
    limit: int = Query(50, description="Max log lines"),
):
    resolved = resolve_inventory(identifier)

    if resolved.get("found"):
        ci = resolved["cmdb_record"]
        host = ci.get("name")
    else:
        host = identifier

    return query_logs(
        host=host,
        search=search,
        hours=hours,
        limit=limit,
    )


@router.get("/errors")
def error_logs(
    identifier: str = Query(..., description="CI name, hostname, or IP"),
    hours: int = Query(24, description="Lookback window in hours"),
    limit: int = Query(50, description="Max log lines"),
):
    resolved = resolve_inventory(identifier)

    if resolved.get("found"):
        ci = resolved["cmdb_record"]
        host = ci.get("name")
    else:
        host = identifier

    return query_errors(
        host=host,
        hours=hours,
        limit=limit,
    )
