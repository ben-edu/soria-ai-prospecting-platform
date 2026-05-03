from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.core.config import settings

router = APIRouter()


@router.get("/health")
def health_check():
    return JSONResponse(
        content={
            "status": "ok",
            "app": settings.APP_NAME,
        }
    )
