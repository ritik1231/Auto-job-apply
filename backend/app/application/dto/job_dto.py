"""DTOs for the job-extraction flow (extension ↔ API layer)."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class JobExtractionRequest(BaseModel):
    raw_content: str = Field(min_length=1, max_length=20_000)
    source_url: str | None = None
    source_platform: str = "linkedin"


class JobExtractionResponse(BaseModel):
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
