"""DTOs for the resume upload and retrieval flow."""

import uuid
from datetime import datetime

from pydantic import BaseModel


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
