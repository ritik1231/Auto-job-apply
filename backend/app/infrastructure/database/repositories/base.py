"""Generic SQLAlchemy base repository — provides CRUD for any ORM model."""

from typing import Any, Generic, TypeVar
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    """Concrete CRUD base for SQLAlchemy models.

    Subclass and fix the model at construction time:

        class UserRepository(BaseRepository[User]):
            def __init__(self, session: AsyncSession) -> None:
                super().__init__(session, User)
    """

    def __init__(self, session: AsyncSession, model_class: type[ModelT]) -> None:
        self._session = session
        self._model = model_class

    async def get_by_id(self, id: UUID) -> ModelT | None:
        return await self._session.get(self._model, id)

    async def list(self, *, limit: int = 100, offset: int = 0) -> list[ModelT]:
        result = await self._session.execute(select(self._model).offset(offset).limit(limit))
        return list(result.scalars().all())

    async def create(self, **kwargs: Any) -> ModelT:
        instance = self._model(**kwargs)
        self._session.add(instance)
        await self._session.flush()
        await self._session.refresh(instance)
        return instance

    async def update(self, id: UUID, **kwargs: Any) -> ModelT | None:
        instance = await self._session.get(self._model, id)
        if instance is None:
            return None
        for key, value in kwargs.items():
            setattr(instance, key, value)
        await self._session.flush()
        await self._session.refresh(instance)
        return instance

    async def delete(self, id: UUID) -> bool:
        instance = await self.get_by_id(id)
        if instance is None:
            return False
        await self._session.delete(instance)
        await self._session.flush()
        return True
