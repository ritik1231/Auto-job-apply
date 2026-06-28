import uuid
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict


class ApplicationStatus(str, Enum):
    DRAFT = "draft"
    SENT = "sent"
    FAILED = "failed"


class ApplicationEntity(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    job_post_id: uuid.UUID
    resume_id: uuid.UUID
    match_score: float | None
    missing_skills: list[str]
    matching_skills: list[str]
    generated_subject: str | None
    generated_email: str | None
    status: ApplicationStatus
    sent_at: datetime | None
    gmail_message_id: str | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime
