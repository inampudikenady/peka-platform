from fastapi import APIRouter, Query
from app.tools.servicenow_client import get_ci_summary

router = APIRouter(prefix="/tools/servicenow", tags=["servicenow"])


@router.get("/ci-summary")
def ci_summary(ci: str = Query(..., description="CI name / hostname")):
    return get_ci_summary(ci)
