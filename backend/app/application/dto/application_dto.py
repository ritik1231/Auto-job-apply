"""DTOs for the application prepare-and-send flow."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.core.sanitization import is_valid_email
from app.domain.entities.application import ApplicationStatus


class ApplicationPrepareRequest(BaseModel):
    job_post_id: uuid.UUID


class ApplicationSendRequest(BaseModel):
    to_address: str | None = None
    subject_override: str | None = None
    body_override: str | None = None

    @field_validator("to_address")
    @classmethod
    def validate_email(cls, v: str | None) -> str | None:
        if v is not None:
            v = v.strip()
            if v and not is_valid_email(v):
                raise ValueError("Invalid email address format")
        return v or None


class ApplicationPrepareResponse(BaseModel):
    application_id: uuid.UUID
    match_score: float = Field(ge=0.0, le=1.0)
    matching_skills: list[str]
    missing_skills: list[str]
    generated_subject: str
    generated_email: str


class ApplicationSendResponse(BaseModel):
    application_id: uuid.UUID
    sent_at: datetime
    gmail_message_id: str


class ApplicationHistoryItem(BaseModel):
    id: uuid.UUID
    job_title: str | None
    company: str | None
    status: ApplicationStatus
    match_score: float | None
    sent_at: datetime | None
    created_at: datetime


class ApplicationHistoryResponse(BaseModel):
    applications: list[ApplicationHistoryItem]
    total: int
