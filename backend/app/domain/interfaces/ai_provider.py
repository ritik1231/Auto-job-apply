"""AI provider interface and its value-object return types."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from pydantic import BaseModel, Field

from app.domain.entities.job_post import JobPostEntity

# ── Value objects returned by the AI provider ─────────────────────────────────


class JobExtractionResult(BaseModel):
    company: str | None = None
    recruiter_name: str | None = None
    recruiter_email: str | None = None
    job_title: str | None = None
    skills: list[str] = Field(default_factory=list)
    experience_required: str | None = None
    responsibilities: list[str] = Field(default_factory=list)
    location: str | None = None
    employment_type: str | None = None
    seniority: str | None = None
    job_summary: str | None = None
    required_candidate_info: list[str] = Field(default_factory=list)


class ResumeMatchResult(BaseModel):
    match_score: float = Field(ge=0.0, le=1.0)
    matching_skills: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
    fit_summary: str | None = None


class EmailGenerationResult(BaseModel):
    subject: str
    body: str


class UserProfileInfo(BaseModel):
    current_ctc: str | None = None
    expected_ctc: str | None = None
    notice_period: str | None = None
    current_location: str | None = None
    total_experience: str | None = None
    linkedin_url: str | None = None


@dataclass
class TokenUsage:
    input_tokens: int = 0
    output_tokens: int = 0
    provider: str = ""
    model: str = ""

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


# ── Interface ─────────────────────────────────────────────────────────────────


class IAIProvider(ABC):
    @abstractmethod
    async def extract_job_details(
        self, post_text: str
    ) -> tuple[JobExtractionResult, TokenUsage]: ...

    @abstractmethod
    async def analyze_resume_match(
        self,
        job: JobPostEntity,
        resume_text: str,
    ) -> tuple[ResumeMatchResult, TokenUsage]: ...

    @abstractmethod
    async def generate_application_email(
        self,
        job: JobPostEntity,
        resume_text: str,
        match: ResumeMatchResult,
        candidate_name: str = "",
        profile: UserProfileInfo | None = None,
    ) -> tuple[EmailGenerationResult, TokenUsage]: ...
