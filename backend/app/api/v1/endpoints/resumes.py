"""Resume management endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, File, Request, UploadFile, status
from pydantic import BaseModel

from app.application.services.resume_service import ResumeService
from app.core.config import settings
from app.core.rate_limit import get_user_key, limiter
from app.dependencies import get_current_user, get_resume_service
from app.domain.entities.user import UserEntity

router = APIRouter()


class ResumeResponse(BaseModel):
    id: uuid.UUID
    file_name: str
    file_size: int
    mime_type: str
    is_active: bool
    created_at: datetime


class ResumeListResponse(BaseModel):
    resumes: list[ResumeResponse]
    active_id: uuid.UUID | None


@router.post("/", response_model=ResumeResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(settings.RATE_LIMIT_RESUME_UPLOAD, key_func=get_user_key)
async def upload_resume(
    request: Request,
    file: UploadFile = File(...),
    current_user: UserEntity = Depends(get_current_user),
    service: ResumeService = Depends(get_resume_service),
) -> ResumeResponse:
    """Upload a PDF resume. Replaces the current active resume."""
    content = await file.read()
    resume = await service.upload_resume(
        user_id=current_user.id,
        file_content=content,
        original_filename=file.filename or "resume.pdf",
        content_type=file.content_type or "application/octet-stream",
        file_size=len(content),
    )
    return ResumeResponse.model_validate(resume, from_attributes=True)


@router.get("/", response_model=ResumeListResponse)
async def list_resumes(
    current_user: UserEntity = Depends(get_current_user),
    service: ResumeService = Depends(get_resume_service),
) -> ResumeListResponse:
    """List all resumes for the authenticated user."""
    resumes = await service.list_resumes(current_user.id)
    active = next((r for r in resumes if r.is_active), None)
    return ResumeListResponse(
        resumes=[ResumeResponse.model_validate(r, from_attributes=True) for r in resumes],
        active_id=active.id if active else None,
    )


@router.get("/{resume_id}", response_model=ResumeResponse)
async def get_resume(
    resume_id: uuid.UUID,
    current_user: UserEntity = Depends(get_current_user),
    service: ResumeService = Depends(get_resume_service),
) -> ResumeResponse:
    """Get metadata for a specific resume."""
    resume = await service.get_resume(current_user.id, resume_id)
    return ResumeResponse.model_validate(resume, from_attributes=True)


@router.delete("/{resume_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_resume(
    resume_id: uuid.UUID,
    current_user: UserEntity = Depends(get_current_user),
    service: ResumeService = Depends(get_resume_service),
) -> None:
    """Soft-delete a resume (marks inactive, does not remove file)."""
    await service.delete_resume(current_user.id, resume_id)
