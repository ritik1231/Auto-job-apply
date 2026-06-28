"""Groq implementation of IAIProvider (OpenAI-compatible API)."""

from __future__ import annotations

import asyncio
import json
from typing import TypeVar

import structlog
from groq import AsyncGroq
from pydantic import BaseModel, ValidationError

from app.core.config import settings
from app.domain.entities.job_post import JobPostEntity
from app.domain.exceptions import AIProviderError, AIResponseParseError
from app.domain.interfaces.ai_provider import (
    EmailGenerationResult,
    IAIProvider,
    JobExtractionResult,
    ResumeMatchResult,
)
from app.infrastructure.ai import prompt_loader

logger = structlog.get_logger(__name__)

_RETRY_ATTEMPTS = 3
_RETRY_BASE_DELAY = 1.0

M = TypeVar("M", bound=BaseModel)


class GroqProvider(IAIProvider):
    def __init__(self, api_key: str, model_name: str) -> None:
        self._client = AsyncGroq(api_key=api_key)
        self._model = model_name

    async def extract_job_details(self, post_text: str) -> JobExtractionResult:
        truncated = post_text[: settings.AI_MAX_JOB_POST_TOKENS * 4]
        system, user = prompt_loader.render("job_extraction_v1", post_text=truncated)
        raw = await self._call_with_retry(system, user)
        return await self._parse_with_retry(
            JobExtractionResult, raw, system, user, label="job_extraction"
        )

    async def analyze_resume_match(self, job: JobPostEntity, resume_text: str) -> ResumeMatchResult:
        truncated_resume = resume_text[: settings.AI_MAX_RESUME_TOKENS * 4]
        system, user = prompt_loader.render(
            "resume_match_v1",
            job_title=job.job_title or "Not specified",
            skills=", ".join(job.skills) if job.skills else "Not specified",
            experience_required=job.experience_required or "Not specified",
            job_summary=job.job_summary or "Not specified",
            resume_text=truncated_resume,
        )
        raw = await self._call_with_retry(system, user)
        return await self._parse_with_retry(
            ResumeMatchResult, raw, system, user, label="resume_match"
        )

    async def generate_application_email(
        self,
        job: JobPostEntity,
        resume_text: str,
        match: ResumeMatchResult,
        candidate_name: str = "",
    ) -> EmailGenerationResult:
        truncated_resume = resume_text[: settings.AI_MAX_RESUME_TOKENS * 4]
        system, user = prompt_loader.render(
            "email_generation_v1",
            job_title=job.job_title or "the role",
            company=job.company or "",
            recruiter_name=_resolve_recruiter_first_name(job.recruiter_name, job.recruiter_email),
            skills=", ".join(job.skills) if job.skills else "Not specified",
            job_summary=job.job_summary or "Not specified",
            match_score=f"{match.match_score:.0%}",
            matching_skills=", ".join(match.matching_skills) if match.matching_skills else "None",
            missing_skills=", ".join(match.missing_skills) if match.missing_skills else "None",
            resume_text=truncated_resume,
            candidate_name=candidate_name,
        )
        raw = await self._call_with_retry(system, user)
        return await self._parse_with_retry(
            EmailGenerationResult, raw, system, user, label="email_generation"
        )

    async def _call_with_retry(self, system: str, user: str) -> str:
        last_exc: Exception | None = None
        for attempt in range(_RETRY_ATTEMPTS):
            try:
                response = await self._client.chat.completions.create(
                    model=self._model,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.2,
                )
                text = response.choices[0].message.content
                if not text:
                    raise AIProviderError("Groq returned an empty response")
                logger.debug("groq response received", attempt=attempt, length=len(text))
                return text
            except AIProviderError:
                raise
            except Exception as exc:
                last_exc = exc
                delay = _RETRY_BASE_DELAY * (2**attempt)
                logger.warning(
                    "groq call failed, retrying",
                    attempt=attempt,
                    delay=delay,
                    error=str(exc),
                )
                await asyncio.sleep(delay)

        raise AIProviderError(f"Groq call failed after {_RETRY_ATTEMPTS} attempts: {last_exc}")

    async def _parse_with_retry(
        self, model_cls: type[M], raw: str, system: str, user: str, label: str
    ) -> M:
        try:
            return self._parse(model_cls, raw)
        except AIResponseParseError as first_err:
            logger.warning(
                "ai response parse failed, retrying with clarification",
                label=label,
                error=str(first_err),
            )

        clarified_user = (
            user + "\n\nYour previous response could not be parsed as valid JSON. "
            "Respond ONLY with the raw JSON object — no markdown, no explanation."
        )
        raw2 = await self._call_with_retry(system, clarified_user)
        try:
            return self._parse(model_cls, raw2)
        except AIResponseParseError as second_err:
            raise AIResponseParseError(
                f"AI response parse failed after retry [{label}]: {second_err}"
            ) from second_err

    def _parse(self, model_cls: type[M], raw: str) -> M:
        try:
            data = json.loads(raw)
            return model_cls.model_validate(data)
        except json.JSONDecodeError as exc:
            raise AIResponseParseError(f"Invalid JSON in AI response: {exc}") from exc
        except ValidationError as exc:
            raise AIResponseParseError(f"AI response schema mismatch: {exc}") from exc


def _resolve_recruiter_first_name(name: str | None, _email: str | None) -> str:
    """Return recruiter first name only when explicitly extracted from the post.

    Email-based inference is intentionally excluded — formats like
    bansal_ritik@ vs riya.mishra@ are ambiguous and produce wrong names.
    'Dear Hiring Manager' is safer than a wrong name.
    """
    if name and name.strip():
        return name.strip().split()[0].capitalize()
    return ""
