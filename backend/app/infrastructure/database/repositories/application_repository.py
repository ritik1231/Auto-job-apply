"""SQLAlchemy implementation of IApplicationRepository."""

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.application import ApplicationEntity
from app.domain.interfaces.repositories import IApplicationRepository
from app.infrastructure.database.models.application import Application
from app.infrastructure.database.repositories.base import BaseRepository


class ApplicationRepository(BaseRepository[Application], IApplicationRepository):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Application)

    async def get_by_id(self, id: uuid.UUID) -> ApplicationEntity | None:
        row = await super().get_by_id(id)
        return ApplicationEntity.model_validate(row) if row else None

    async def get_by_user_and_job_post(
        self, user_id: uuid.UUID, job_post_id: uuid.UUID
    ) -> ApplicationEntity | None:
        result = await self._session.execute(
            select(Application).where(
                Application.user_id == user_id,
                Application.job_post_id == job_post_id,
            )
        )
        row = result.scalar_one_or_none()
        return ApplicationEntity.model_validate(row) if row else None

    async def create(self, **kwargs: Any) -> ApplicationEntity:
        row = await super().create(**kwargs)
        return ApplicationEntity.model_validate(row)

    async def update(self, id: uuid.UUID, **kwargs: Any) -> ApplicationEntity | None:
        row = await super().update(id, **kwargs)
        return ApplicationEntity.model_validate(row) if row else None

    async def list_for_user(
        self, user_id: uuid.UUID, *, limit: int = 20, offset: int = 0
    ) -> list[ApplicationEntity]:
        result = await self._session.execute(
            select(Application)
            .where(Application.user_id == user_id)
            .order_by(Application.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return [ApplicationEntity.model_validate(row) for row in result.scalars().all()]
