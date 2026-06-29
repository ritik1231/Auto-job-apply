"""Job post extraction and retrieval service."""

from __future__ import annotations

import hashlib
import re
import uuid

import structlog

from app.core.sanitization import sanitize_post_text
from app.domain.entities.job_post import JobPostEntity
from app.domain.exceptions import InvalidJobPostError
from app.domain.interfaces.ai_provider import IAIProvider
from app.domain.interfaces.repositories import IJobPostRepository

logger = structlog.get_logger(__name__)

_MIN_POST_LENGTH = 50  # characters — below this we can't extract anything meaningful


def _normalize(text: str) -> str:
    """Collapse whitespace and lowercase for stable hashing."""
    return re.sub(r"\s+", " ", text.strip()).lower()


def compute_content_hash(raw_text: str) -> str:
    return hashlib.sha256(_normalize(raw_text).encode()).hexdigest()


class JobService:
    def __init__(
        self,
        job_repo: IJobPostRepository,
        ai_provider: IAIProvider,
    ) -> None:
        self._repo = job_repo
        self._ai = ai_provider

    async def process_post(
        self,
        user_id: uuid.UUID,
        raw_content: str,
        source_url: str | None = None,
        source_platform: str = "linkedin",
    ) -> tuple[JobPostEntity, bool]:
        """Extract and persist a job post.

        Returns (entity, from_cache). When from_cache is True the AI was not called.
        """
        clean_content = sanitize_post_text(raw_content)

        if len(clean_content) < _MIN_POST_LENGTH:
            raise InvalidJobPostError(
                f"Post text is too short (minimum {_MIN_POST_LENGTH} characters)"
            )

        content_hash = compute_content_hash(clean_content)

        cached = await self._repo.get_by_user_and_hash(user_id, content_hash)
        if cached is not None:
            logger.info(
                "job post cache hit — skipping AI call",
                user_id=str(user_id),
                job_post_id=str(cached.id),
            )
            return cached, True

        extraction = await self._ai.extract_job_details(clean_content)

        job = await self._repo.create(
            user_id=user_id,
            raw_content=clean_content,
            content_hash=content_hash,
            company=extraction.company,
            recruiter_name=extraction.recruiter_name,
            recruiter_email=extraction.recruiter_email,
            job_title=extraction.job_title,
            skills=extraction.skills,
            experience_required=extraction.experience_required,
            responsibilities=extraction.responsibilities,
            location=extraction.location,
            employment_type=extraction.employment_type,
            seniority=extraction.seniority,
            job_summary=extraction.job_summary,
            required_candidate_info=extraction.required_candidate_info,
            source_url=source_url,
            source_platform=source_platform,
        )
        logger.info(
            "job post extracted and persisted",
            user_id=str(user_id),
            job_post_id=str(job.id),
            company=job.company,
        )
        return job, False

    async def get_job_post(self, user_id: uuid.UUID, job_post_id: uuid.UUID) -> JobPostEntity:
        job = await self._repo.get_by_id(job_post_id)
        if job is None or job.user_id != user_id:
            raise InvalidJobPostError("Job post not found")
        return job

    async def list_job_posts(self, user_id: uuid.UUID, *, limit: int = 20) -> list[JobPostEntity]:
        return await self._repo.list_for_user(user_id, limit=limit)
