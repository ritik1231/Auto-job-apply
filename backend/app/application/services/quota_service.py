"""Per-user daily quota service — token and request based."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta

import structlog

from app.core.config import settings
from app.domain.exceptions import DailyLimitError
from app.domain.interfaces.repositories import IUserDailyUsageRepository

logger = structlog.get_logger(__name__)


class QuotaInfo:
    def __init__(self, cap: int, used: int) -> None:
        self.cap = cap
        self.used = used
        self.remaining = max(0, cap - used)
        self.active_users = 1  # kept for API compat; no longer computed
        now = datetime.now(UTC)
        midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        self.resets_in_seconds = int((midnight - now).total_seconds())

    @property
    def exhausted(self) -> bool:
        return self.remaining == 0


class QuotaService:
    def __init__(self, usage_repo: IUserDailyUsageRepository) -> None:
        self._repo = usage_repo

    async def get_quota(self, user_id: uuid.UUID, override: int | None = None) -> QuotaInfo:
        today = date.today()
        row = await self._repo.get_today(user_id, today)
        used_requests = row.request_count if row else 0
        cap = override if override is not None else settings.USER_DAILY_REQUEST_LIMIT
        return QuotaInfo(cap=cap, used=used_requests)

    async def enforce(self, user_id: uuid.UUID, override: int | None = None) -> None:
        """Raise DailyLimitError if the user has hit today's request or token limit."""
        today = date.today()
        row = await self._repo.get_today(user_id, today)
        if row is None:
            return

        cap = override if override is not None else settings.USER_DAILY_REQUEST_LIMIT
        if row.request_count >= cap:
            now = datetime.now(UTC)
            midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
            resets_in = int((midnight - now).total_seconds())
            h, m = resets_in // 3600, (resets_in % 3600) // 60
            raise DailyLimitError(
                f"You've reached your daily limit of {cap} analyses. Resets in {h}h {m}m.",
                details={"cap": cap, "used": row.request_count, "resets_in_seconds": resets_in},
            )

        if row.total_tokens >= settings.USER_DAILY_TOKEN_LIMIT:
            now = datetime.now(UTC)
            midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
            resets_in = int((midnight - now).total_seconds())
            h, m = resets_in // 3600, (resets_in % 3600) // 60
            raise DailyLimitError(
                f"You've reached today's usage limit. Resets in {h}h {m}m.",
                details={"resets_in_seconds": resets_in},
            )

    async def record_usage(self, user_id: uuid.UUID, input_tokens: int, output_tokens: int) -> None:
        today = date.today()
        await self._repo.upsert(user_id, today, input_tokens, output_tokens)
        logger.info(
            "usage recorded",
            user_id=str(user_id),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )
