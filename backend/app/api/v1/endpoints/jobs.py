"""Job post extraction and listing endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Request, status
from pydantic import BaseModel

from app.application.dto.job_dto import JobExtractionRequest
from app.application.services.job_service import JobService
from app.core.config import settings
from app.core.rate_limit import get_user_key, limiter
from app.dependencies import get_current_user, get_job_service
from app.domain.entities.user import UserEntity

router = APIRouter()


class JobPostResponse(BaseModel):
    id: uuid.UUID
    company: str | None
    recruiter_name: str | None
    recruiter_email: str | None
    job_title: str | None
    skills: list[str]
    experience_required: str | None
    responsibilities: list[str]
    location: str | None
    employment_type: str | None
    seniority: str | None
    job_summary: str | None
    source_platform: str
    created_at: datetime
    from_cache: bool = False


@router.post(
    "/extract",
    response_model=JobPostResponse,
    status_code=status.HTTP_200_OK,
)
@limiter.limit(settings.RATE_LIMIT_JOB_EXTRACT, key_func=get_user_key)
async def extract_job(
    request: Request,
    body: JobExtractionRequest,
    current_user: UserEntity = Depends(get_current_user),
    service: JobService = Depends(get_job_service),
) -> JobPostResponse:
    """Extract structured data from a raw hiring post. Returns cached data if seen before."""
    job, from_cache = await service.process_post(
        user_id=current_user.id,
        raw_content=body.raw_content,
        source_url=body.source_url,
        source_platform=body.source_platform,
    )
    data = job.model_dump()
    data["from_cache"] = from_cache
    return JobPostResponse(**data)


@router.get("/", response_model=list[JobPostResponse])
async def list_jobs(
    limit: int = 20,
    current_user: UserEntity = Depends(get_current_user),
    service: JobService = Depends(get_job_service),
) -> list[JobPostResponse]:
    """List this user's extracted job posts (most recent first)."""
    jobs = await service.list_job_posts(current_user.id, limit=limit)
    return [JobPostResponse(**j.model_dump()) for j in jobs]


@router.get("/{job_post_id}", response_model=JobPostResponse)
async def get_job(
    job_post_id: uuid.UUID,
    current_user: UserEntity = Depends(get_current_user),
    service: JobService = Depends(get_job_service),
) -> JobPostResponse:
    """Get a single extracted job post."""
    job = await service.get_job_post(current_user.id, job_post_id)
    return JobPostResponse(**job.model_dump())
