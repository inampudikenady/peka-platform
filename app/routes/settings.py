from fastapi import APIRouter

from app.config import validate_settings

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("")
def read_settings():
    return validate_settings()
