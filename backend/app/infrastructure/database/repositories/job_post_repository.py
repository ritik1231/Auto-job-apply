"""SQLAlchemy implementation of IJobPostRepository."""

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.job_post import JobPostEntity
from app.domain.interfaces.repositories import IJobPostRepository
from app.infrastructure.database.models.job_post import JobPost
from app.infrastructure.database.repositories.base import BaseRepository


class JobPostRepository(BaseRepository[JobPost], IJobPostRepository):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, JobPost)

    async def get_by_id(self, id: uuid.UUID) -> JobPostEntity | None:
        row = await super().get_by_id(id)
        return JobPostEntity.model_validate(row) if row else None

    async def get_by_user_and_hash(
        self, user_id: uuid.UUID, content_hash: str
    ) -> JobPostEntity | None:
        result = await self._session.execute(
            select(JobPost).where(
                JobPost.user_id == user_id,
                JobPost.content_hash == content_hash,
            )
        )
        row = result.scalar_one_or_none()
        return JobPostEntity.model_validate(row) if row else None

    async def create(self, **kwargs: Any) -> JobPostEntity:
        row = await super().create(**kwargs)
        return JobPostEntity.model_validate(row)

    async def list_for_user(self, user_id: uuid.UUID, *, limit: int = 20) -> list[JobPostEntity]:
        result = await self._session.execute(
            select(JobPost)
            .where(JobPost.user_id == user_id)
            .order_by(JobPost.created_at.desc())
            .limit(limit)
        )
        return [JobPostEntity.model_validate(row) for row in result.scalars().all()]
