"""Application prepare, send, and listing endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Request, status
from pydantic import BaseModel, Field

from app.application.dto.application_dto import (
    ApplicationHistoryItem,
    ApplicationPrepareRequest,
    ApplicationSendRequest,
    ApplicationSendResponse,
)
from app.application.services.application_service import ApplicationService
from app.application.services.email_send_service import EmailSendService
from app.application.services.quota_service import QuotaService
from app.core.config import settings
from app.core.rate_limit import get_user_key, limiter
from app.dependencies import (
    get_application_service,
    get_current_user,
    get_email_send_service,
    get_quota_service,
)
from app.domain.entities.application import ApplicationStatus
from app.domain.entities.user import UserEntity
from app.domain.interfaces.ai_provider import UserProfileInfo

router = APIRouter()


class ApplicationDraftResponse(BaseModel):
    id: uuid.UUID
    job_post_id: uuid.UUID
    resume_id: uuid.UUID
    match_score: float = Field(ge=0.0, le=1.0)
    matching_skills: list[str]
    missing_skills: list[str]
    generated_subject: str
    generated_email: str
    status: ApplicationStatus
    created_at: datetime


class ApplicationSummaryResponse(BaseModel):
    id: uuid.UUID
    job_post_id: uuid.UUID
    match_score: float | None
    status: ApplicationStatus
    sent_at: datetime | None
    created_at: datetime


@router.post(
    "/prepare",
    response_model=ApplicationDraftResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit(settings.RATE_LIMIT_APPLICATION, key_func=get_user_key)
async def prepare_application(
    request: Request,
    body: ApplicationPrepareRequest,
    current_user: UserEntity = Depends(get_current_user),
    service: ApplicationService = Depends(get_application_service),
    quota_service: QuotaService = Depends(get_quota_service),
) -> ApplicationDraftResponse:
    """Analyse resume against job post and generate a draft application email."""
    await quota_service.enforce(current_user.id, current_user.daily_quota_override)
    profile = UserProfileInfo(
        current_ctc=current_user.current_ctc,
        expected_ctc=current_user.expected_ctc,
        notice_period=current_user.notice_period,
        current_location=current_user.current_location,
        total_experience=current_user.total_experience,
        linkedin_url=current_user.linkedin_url,
    )
    app = await service.prepare_application(
        current_user.id, body.job_post_id, current_user.name or "", profile
    )
    return ApplicationDraftResponse(
        id=app.id,
        job_post_id=app.job_post_id,
        resume_id=app.resume_id,
        match_score=app.match_score or 0.0,
        matching_skills=app.matching_skills,
        missing_skills=app.missing_skills,
        generated_subject=app.generated_subject or "",
        generated_email=app.generated_email or "",
        status=app.status,
        created_at=app.created_at,
    )


@router.get("/", response_model=list[ApplicationSummaryResponse])
async def list_applications(
    limit: int = 20,
    offset: int = 0,
    current_user: UserEntity = Depends(get_current_user),
    service: ApplicationService = Depends(get_application_service),
) -> list[ApplicationSummaryResponse]:
    """List the authenticated user's applications (most recent first)."""
    apps = await service.list_applications(current_user.id, limit=limit, offset=offset)
    return [
        ApplicationSummaryResponse(
            id=a.id,
            job_post_id=a.job_post_id,
            match_score=a.match_score,
            status=a.status,
            sent_at=a.sent_at,
            created_at=a.created_at,
        )
        for a in apps
    ]


@router.get("/history", response_model=list[ApplicationHistoryItem])
async def list_applications_history(
    limit: int = 20,
    offset: int = 0,
    current_user: UserEntity = Depends(get_current_user),
    service: ApplicationService = Depends(get_application_service),
) -> list[ApplicationHistoryItem]:
    """List applications with job title/company joined in — for the extension history view."""
    return await service.list_applications_with_job_info(
        current_user.id, limit=limit, offset=offset
    )


@router.get("/{application_id}", response_model=ApplicationDraftResponse)
async def get_application(
    application_id: uuid.UUID,
    current_user: UserEntity = Depends(get_current_user),
    service: ApplicationService = Depends(get_application_service),
) -> ApplicationDraftResponse:
    """Get full details for a single application."""
    app = await service.get_application(current_user.id, application_id)
    return ApplicationDraftResponse(
        id=app.id,
        job_post_id=app.job_post_id,
        resume_id=app.resume_id,
        match_score=app.match_score or 0.0,
        matching_skills=app.matching_skills,
        missing_skills=app.missing_skills,
        generated_subject=app.generated_subject or "",
        generated_email=app.generated_email or "",
        status=app.status,
        created_at=app.created_at,
    )


@router.post("/{application_id}/send", response_model=ApplicationSendResponse)
async def send_application(
    application_id: uuid.UUID,
    body: ApplicationSendRequest,
    current_user: UserEntity = Depends(get_current_user),
    service: EmailSendService = Depends(get_email_send_service),
) -> ApplicationSendResponse:
    """Send the generated application email via Gmail.

    Optionally supply `to_address` to override the recruiter email extracted
    from the job post.
    """
    return await service.send_application(
        current_user.id,
        application_id,
        body.to_address,
        body.subject_override,
        body.body_override,
    )
