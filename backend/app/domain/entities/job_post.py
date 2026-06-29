import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class JobPostEntity(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    raw_content: str
    content_hash: str
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
    required_candidate_info: list[str] = []
    source_url: str | None
    source_platform: str
    created_at: datetime
