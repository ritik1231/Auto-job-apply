"""Composition root — all FastAPI Depends() factories live here."""

from collections.abc import AsyncGenerator

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.application_service import ApplicationService
from app.application.services.auth_service import AuthService
from app.application.services.email_send_service import EmailSendService
from app.application.services.job_service import JobService
from app.application.services.resume_service import ResumeService
from app.domain.entities.user import UserEntity
from app.domain.interfaces.ai_provider import IAIProvider
from app.domain.interfaces.repositories import (
    IApplicationRepository,
    IJobPostRepository,
    IResumeRepository,
    IUserRepository,
)
from app.domain.interfaces.storage import IResumeStorage
from app.infrastructure.database.repositories.application_repository import ApplicationRepository
from app.infrastructure.database.repositories.job_post_repository import JobPostRepository
from app.infrastructure.database.repositories.resume_repository import ResumeRepository
from app.infrastructure.database.repositories.user_repository import UserRepository
from app.infrastructure.database.session import get_db_session
from app.infrastructure.storage.local_storage import LocalResumeStorage

_bearer = HTTPBearer()


# ── Database session ───────────────────────────────────────────────────────────


async def get_session(
    session: AsyncSession = Depends(get_db_session),
) -> AsyncGenerator[AsyncSession, None]:
    yield session


# ── Repository factories ───────────────────────────────────────────────────────


async def get_user_repo(
    session: AsyncSession = Depends(get_session),
) -> IUserRepository:
    return UserRepository(session)


async def get_resume_repo(
    session: AsyncSession = Depends(get_session),
) -> IResumeRepository:
    return ResumeRepository(session)


async def get_job_repo(
    session: AsyncSession = Depends(get_session),
) -> IJobPostRepository:
    return JobPostRepository(session)


async def get_application_repo(
    session: AsyncSession = Depends(get_session),
) -> IApplicationRepository:
    return ApplicationRepository(session)


# ── Storage factories ──────────────────────────────────────────────────────────


def get_resume_storage() -> IResumeStorage:
    return LocalResumeStorage()


# ── AI provider factory ────────────────────────────────────────────────────────


def get_ai_provider() -> IAIProvider:
    from app.infrastructure.ai.factory import get_ai_provider as _factory

    return _factory()


# ── Service factories ──────────────────────────────────────────────────────────


async def get_auth_service(
    user_repo: IUserRepository = Depends(get_user_repo),
) -> AuthService:
    return AuthService(user_repo)


async def get_resume_service(
    resume_repo: IResumeRepository = Depends(get_resume_repo),
    storage: IResumeStorage = Depends(get_resume_storage),
) -> ResumeService:
    return ResumeService(resume_repo, storage)


async def get_job_service(
    job_repo: IJobPostRepository = Depends(get_job_repo),
    ai_provider: IAIProvider = Depends(get_ai_provider),
) -> JobService:
    return JobService(job_repo, ai_provider)


async def get_application_service(
    application_repo: IApplicationRepository = Depends(get_application_repo),
    job_repo: IJobPostRepository = Depends(get_job_repo),
    resume_repo: IResumeRepository = Depends(get_resume_repo),
    ai_provider: IAIProvider = Depends(get_ai_provider),
) -> ApplicationService:
    return ApplicationService(application_repo, job_repo, resume_repo, ai_provider)


async def get_email_send_service(
    application_repo: IApplicationRepository = Depends(get_application_repo),
    job_repo: IJobPostRepository = Depends(get_job_repo),
    resume_repo: IResumeRepository = Depends(get_resume_repo),
    user_repo: IUserRepository = Depends(get_user_repo),
    storage: IResumeStorage = Depends(get_resume_storage),
) -> EmailSendService:
    return EmailSendService(application_repo, job_repo, resume_repo, user_repo, storage)


# ── Auth dependency ────────────────────────────────────────────────────────────


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    user_repo: IUserRepository = Depends(get_user_repo),
) -> UserEntity:
    service = AuthService(user_repo)
    return await service.get_current_user(credentials.credentials)
