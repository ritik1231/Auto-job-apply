"""Repository interfaces — defines WHAT operations exist, not HOW.

SQLAlchemy implementations live in app/infrastructure/database/repositories/.
"""

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

from app.domain.entities.application import ApplicationEntity
from app.domain.entities.job_post import JobPostEntity
from app.domain.entities.resume import ResumeEntity
from app.domain.entities.user import UserEntity


@dataclass
class GmailTokenData:
    """Encrypted Gmail OAuth credentials fetched from the database."""

    access_token_enc: str | None
    refresh_token_enc: str | None
    expiry: datetime | None


class IUserRepository(ABC):
    @abstractmethod
    async def get_by_id(self, id: uuid.UUID) -> UserEntity | None: ...

    @abstractmethod
    async def get_by_email(self, email: str) -> UserEntity | None: ...

    @abstractmethod
    async def get_by_google_id(self, google_id: str) -> UserEntity | None: ...

    @abstractmethod
    async def create(self, **kwargs: object) -> UserEntity: ...

    @abstractmethod
    async def update(self, id: uuid.UUID, **kwargs: object) -> UserEntity | None: ...

    @abstractmethod
    async def get_gmail_tokens(self, user_id: uuid.UUID) -> GmailTokenData | None: ...

    @abstractmethod
    async def update_gmail_tokens(
        self, user_id: uuid.UUID, access_token_enc: str, expiry: datetime
    ) -> None: ...


class IResumeRepository(ABC):
    @abstractmethod
    async def get_by_id(self, id: uuid.UUID) -> ResumeEntity | None: ...

    @abstractmethod
    async def get_active_for_user(self, user_id: uuid.UUID) -> ResumeEntity | None: ...

    @abstractmethod
    async def list_for_user(self, user_id: uuid.UUID) -> list[ResumeEntity]: ...

    @abstractmethod
    async def create(self, **kwargs: object) -> ResumeEntity: ...

    @abstractmethod
    async def deactivate_all_for_user(self, user_id: uuid.UUID) -> None: ...

    @abstractmethod
    async def soft_delete(self, id: uuid.UUID) -> None:
        """Mark a resume inactive (does not remove the stored file)."""
        ...


class IJobPostRepository(ABC):
    @abstractmethod
    async def get_by_id(self, id: uuid.UUID) -> JobPostEntity | None: ...

    @abstractmethod
    async def get_by_user_and_hash(
        self, user_id: uuid.UUID, content_hash: str
    ) -> JobPostEntity | None: ...

    @abstractmethod
    async def create(self, **kwargs: object) -> JobPostEntity: ...

    @abstractmethod
    async def list_for_user(
        self, user_id: uuid.UUID, *, limit: int = 20
    ) -> list[JobPostEntity]: ...


class IApplicationRepository(ABC):
    @abstractmethod
    async def get_by_id(self, id: uuid.UUID) -> ApplicationEntity | None: ...

    @abstractmethod
    async def get_by_user_and_job_post(
        self, user_id: uuid.UUID, job_post_id: uuid.UUID
    ) -> ApplicationEntity | None: ...

    @abstractmethod
    async def create(self, **kwargs: object) -> ApplicationEntity: ...

    @abstractmethod
    async def update(self, id: uuid.UUID, **kwargs: object) -> ApplicationEntity | None: ...

    @abstractmethod
    async def list_for_user(
        self, user_id: uuid.UUID, *, limit: int = 20, offset: int = 0
    ) -> list[ApplicationEntity]: ...

    @abstractmethod
    async def count_today_for_user(self, user_id: uuid.UUID) -> int:
        """Count applications prepared by this user since UTC midnight today."""
        ...

    @abstractmethod
    async def count_active_users(self, days: int = 7) -> int:
        """Count distinct users who prepared at least one application in the last N days."""
        ...
