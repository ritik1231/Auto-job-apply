"""SQLAlchemy implementation of IUserRepository."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.user import UserEntity
from app.domain.interfaces.repositories import GmailTokenData, IUserRepository
from app.infrastructure.database.models.user import User
from app.infrastructure.database.repositories.base import BaseRepository


class UserRepository(BaseRepository[User], IUserRepository):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, User)

    async def get_by_id(self, id: uuid.UUID) -> UserEntity | None:
        row = await super().get_by_id(id)
        return UserEntity.model_validate(row) if row else None

    async def get_by_email(self, email: str) -> UserEntity | None:
        result = await self._session.execute(select(User).where(User.email == email))
        row = result.scalar_one_or_none()
        return UserEntity.model_validate(row) if row else None

    async def get_by_google_id(self, google_id: str) -> UserEntity | None:
        result = await self._session.execute(select(User).where(User.google_id == google_id))
        row = result.scalar_one_or_none()
        return UserEntity.model_validate(row) if row else None

    async def create(self, **kwargs: Any) -> UserEntity:
        row = await super().create(**kwargs)
        return UserEntity.model_validate(row)

    async def update(self, id: uuid.UUID, **kwargs: Any) -> UserEntity | None:
        row = await super().update(id, **kwargs)
        return UserEntity.model_validate(row) if row else None

    async def get_gmail_tokens(self, user_id: uuid.UUID) -> GmailTokenData | None:
        user = await self._session.get(User, user_id)
        if user is None:
            return None
        return GmailTokenData(
            access_token_enc=user.gmail_access_token,
            refresh_token_enc=user.gmail_refresh_token,
            expiry=user.gmail_token_expiry,
        )

    async def update_gmail_tokens(
        self, user_id: uuid.UUID, access_token_enc: str, expiry: datetime
    ) -> None:
        user = await self._session.get(User, user_id)
        if user is None:
            return
        user.gmail_access_token = access_token_enc
        user.gmail_token_expiry = expiry
        await self._session.flush()
