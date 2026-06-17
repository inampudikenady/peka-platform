# app/routes/cmdb.py
from fastapi import APIRouter
from app.tools.cmdb_csv import get_ci

router = APIRouter()

@router.get("/tools/cmdb/ci")
def ci_lookup(ci: str):
    result = get_ci(ci)

    return {
        "found": result is not None,
        "ci": result
    }