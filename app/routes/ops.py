from fastapi import APIRouter, Query

from app.correlation.operational_analysis import analyze_ci


router = APIRouter(prefix="/tools/ops", tags=["ops"])


@router.get("/analyze")
def analyze(
    identifier: str = Query(..., description="CI name, hostname, or IP address"),
    hours: int = Query(24, description="Lookback window for log analysis"),
):
    return analyze_ci(identifier=identifier, hours=hours)
