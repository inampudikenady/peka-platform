# app/routes/cmdb.py
from fastapi import APIRouter

from app.sources.cmdb.inventory import resolve_inventory

router = APIRouter()

@router.get("/tools/cmdb/ci")
def ci_lookup(ci: str):
    result = resolve_inventory(ci)

    return {
        "found": result.get("found", False),
        "provider": result.get("provider"),
        "ci": result.get("cmdb_record"),
    }
