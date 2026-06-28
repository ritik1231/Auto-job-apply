from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import settings

router = APIRouter()


class HealthResponse(BaseModel):
    status: str
    version: str


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    description="Returns service status. No authentication required.",
    responses={200: {"description": "Service is healthy"}},
)
async def health_check() -> HealthResponse:
    return HealthResponse(status="ok", version=settings.APP_VERSION)
