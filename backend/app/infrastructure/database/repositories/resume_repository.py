"""SQLAlchemy implementation of IResumeRepository."""

import uuid
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.resume import ResumeEntity
from app.domain.interfaces.repositories import IResumeRepository
from app.infrastructure.database.models.resume import Resume
from app.infrastructure.database.repositories.base import BaseRepository


class ResumeRepository(BaseRepository[Resume], IResumeRepository):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Resume)

    async def get_by_id(self, id: uuid.UUID) -> ResumeEntity | None:
        row = await super().get_by_id(id)
        return ResumeEntity.model_validate(row) if row else None

    async def get_active_for_user(self, user_id: uuid.UUID) -> ResumeEntity | None:
        result = await self._session.execute(
            select(Resume).where(Resume.user_id == user_id, Resume.is_active.is_(True))
        )
        row = result.scalar_one_or_none()
        return ResumeEntity.model_validate(row) if row else None

    async def list_for_user(self, user_id: uuid.UUID) -> list[ResumeEntity]:
        result = await self._session.execute(
            select(Resume).where(Resume.user_id == user_id).order_by(Resume.created_at.desc())
        )
        return [ResumeEntity.model_validate(row) for row in result.scalars().all()]

    async def create(self, **kwargs: Any) -> ResumeEntity:
        row = await super().create(**kwargs)
        return ResumeEntity.model_validate(row)

    async def deactivate_all_for_user(self, user_id: uuid.UUID) -> None:
        await self._session.execute(
            update(Resume).where(Resume.user_id == user_id).values(is_active=False)
        )

    async def soft_delete(self, id: uuid.UUID) -> None:
        await self._session.execute(update(Resume).where(Resume.id == id).values(is_active=False))
