"""Dynamic per-user daily quota based on total active users."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from app.core.config import settings
from app.domain.exceptions import DailyLimitError
from app.domain.interfaces.repositories import IApplicationRepository


class QuotaInfo:
    def __init__(self, cap: int, used: int, active_users: int) -> None:
        self.cap = cap
        self.used = used
        self.remaining = max(0, cap - used)
        self.active_users = active_users
        # Seconds until UTC midnight
        now = datetime.now(UTC)
        midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        self.resets_in_seconds = int((midnight - now).total_seconds())

    @property
    def exhausted(self) -> bool:
        return self.remaining == 0


class QuotaService:
    def __init__(self, app_repo: IApplicationRepository) -> None:
        self._app_repo = app_repo

    def _compute_cap(self, active_users: int, override: int | None) -> int:
        if override is not None:
            return override
        raw = settings.DAILY_AI_BUDGET // max(active_users, 1)
        return max(settings.QUOTA_MIN_PER_USER, min(settings.QUOTA_MAX_PER_USER, raw))

    async def get_quota(self, user_id: uuid.UUID, override: int | None = None) -> QuotaInfo:
        active_users, used = await self._fetch(user_id)
        cap = self._compute_cap(active_users, override)
        return QuotaInfo(cap=cap, used=used, active_users=active_users)

    async def enforce(self, user_id: uuid.UUID, override: int | None = None) -> QuotaInfo:
        """Raise DailyLimitError if the user has exhausted today's quota."""
        quota = await self.get_quota(user_id, override)
        if quota.exhausted:
            h = quota.resets_in_seconds // 3600
            m = (quota.resets_in_seconds % 3600) // 60
            raise DailyLimitError(
                f"You've used all {quota.cap} analyses for today. " f"Limit resets in {h}h {m}m.",
                details={
                    "cap": quota.cap,
                    "used": quota.used,
                    "resets_in_seconds": quota.resets_in_seconds,
                },
            )
        return quota

    async def _fetch(self, user_id: uuid.UUID) -> tuple[int, int]:
        active_users = await self._app_repo.count_active_users(days=7)
        used = await self._app_repo.count_today_for_user(user_id)
        return active_users, used
