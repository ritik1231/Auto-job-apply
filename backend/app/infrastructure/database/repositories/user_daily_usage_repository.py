"""SQLAlchemy implementation of IUserDailyUsageRepository."""

from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.interfaces.repositories import IUserDailyUsageRepository, UserDailyUsageData
from app.infrastructure.database.models.user_daily_usage import UserDailyUsage


class UserDailyUsageRepository(IUserDailyUsageRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_today(self, user_id: uuid.UUID, today: date) -> UserDailyUsageData | None:
        stmt = select(UserDailyUsage).where(
            UserDailyUsage.user_id == user_id,
            UserDailyUsage.date == today,
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        if row is None:
            return None
        return UserDailyUsageData(
            input_tokens=row.input_tokens,
            output_tokens=row.output_tokens,
            request_count=row.request_count,
        )

    async def upsert(
        self,
        user_id: uuid.UUID,
        today: date,
        input_tokens: int,
        output_tokens: int,
    ) -> None:
        stmt = (
            pg_insert(UserDailyUsage)
            .values(
                id=uuid.uuid4(),
                user_id=user_id,
                date=today,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                request_count=1,
            )
            .on_conflict_do_update(
                constraint="uq_user_daily_usage_user_date",
                set_={
                    "input_tokens": UserDailyUsage.input_tokens + input_tokens,
                    "output_tokens": UserDailyUsage.output_tokens + output_tokens,
                    "request_count": UserDailyUsage.request_count + 1,
                    "updated_at": pg_insert(UserDailyUsage).excluded.updated_at,
                },
            )
        )
        await self._session.execute(stmt)
