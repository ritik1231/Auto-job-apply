"""Daily quota endpoint — returns cap/used/remaining for the authenticated user."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.application.services.quota_service import QuotaService
from app.dependencies import get_current_user, get_quota_service
from app.domain.entities.user import UserEntity

router = APIRouter()


class QuotaResponse(BaseModel):
    cap: int
    used: int
    remaining: int
    active_users: int
    resets_in_seconds: int


@router.get("/quota", response_model=QuotaResponse)
async def get_quota(
    current_user: UserEntity = Depends(get_current_user),
    service: QuotaService = Depends(get_quota_service),
) -> QuotaResponse:
    """Return today's analysis quota for the authenticated user."""
    q = await service.get_quota(current_user.id, current_user.daily_quota_override)
    return QuotaResponse(
        cap=q.cap,
        used=q.used,
        remaining=q.remaining,
        active_users=q.active_users,
        resets_in_seconds=q.resets_in_seconds,
    )
