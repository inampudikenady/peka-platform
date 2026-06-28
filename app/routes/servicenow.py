from fastapi import APIRouter, Query
from app.sources.servicenow.servicenow_client import get_servicenow_ci_summary

router = APIRouter(prefix="/tools/servicenow", tags=["servicenow"])


@router.get("/ci-summary")
def ci_summary(ci: str = Query(..., description="CI name / hostname")):
    return get_servicenow_ci_summary(ci)
