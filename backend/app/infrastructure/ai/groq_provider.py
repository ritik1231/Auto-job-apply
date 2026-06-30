"""Groq implementation of IAIProvider (OpenAI-compatible API)."""

from __future__ import annotations

import asyncio
import json
from typing import TypeVar

import structlog
from groq import AsyncGroq
from groq import RateLimitError as GroqRateLimitError
from pydantic import BaseModel, ValidationError

from app.core.config import settings
from app.domain.entities.job_post import JobPostEntity
from app.domain.exceptions import AIProviderError, AIRateLimitError, AIResponseParseError
from app.domain.interfaces.ai_provider import (
    EmailGenerationResult,
    IAIProvider,
    JobExtractionResult,
    ResumeMatchResult,
    TokenUsage,
    UserProfileInfo,
)
from app.infrastructure.ai import prompt_loader

logger = structlog.get_logger(__name__)

_RETRY_ATTEMPTS = 3
_RETRY_BASE_DELAY = 1.0

M = TypeVar("M", bound=BaseModel)


def _rate_limit_type(exc: Exception) -> str:
    s = str(exc).lower()
    return "rpd" if ("day" in s or "daily" in s or "per day" in s) else "rpm"


class GroqProvider(IAIProvider):
    def __init__(self, api_key: str, model_name: str) -> None:
        self._client = AsyncGroq(api_key=api_key)
        self._model = model_name

    async def extract_job_details(self, post_text: str) -> tuple[JobExtractionResult, TokenUsage]:
        truncated = post_text[: settings.AI_MAX_JOB_POST_TOKENS * 4]
        system, user = prompt_loader.render("job_extraction_v1", post_text=truncated)
        text, inp, out = await self._call_with_retry(system, user)
        result = await self._parse_with_retry(
            JobExtractionResult, text, system, user, label="job_extraction"
        )
        return result, TokenUsage(
            input_tokens=inp, output_tokens=out, provider="", model=self._model
        )

    async def analyze_resume_match(
        self, job: JobPostEntity, resume_text: str
    ) -> tuple[ResumeMatchResult, TokenUsage]:
        truncated_resume = resume_text[: settings.AI_MAX_RESUME_TOKENS * 4]
        system, user = prompt_loader.render(
            "resume_match_v1",
            job_title=job.job_title or "Not specified",
            skills=", ".join(job.skills) if job.skills else "Not specified",
            experience_required=job.experience_required or "Not specified",
            job_summary=job.job_summary or "Not specified",
            resume_text=truncated_resume,
        )
        text, inp, out = await self._call_with_retry(system, user)
        result = await self._parse_with_retry(
            ResumeMatchResult, text, system, user, label="resume_match"
        )
        return result, TokenUsage(
            input_tokens=inp, output_tokens=out, provider="", model=self._model
        )

    async def generate_application_email(
        self,
        job: JobPostEntity,
        resume_text: str,
        match: ResumeMatchResult,
        candidate_name: str = "",
        profile: UserProfileInfo | None = None,
    ) -> tuple[EmailGenerationResult, TokenUsage]:
        truncated_resume = resume_text[: settings.AI_MAX_RESUME_TOKENS * 4]
        p = profile or UserProfileInfo()
        requested = set(job.required_candidate_info)
        required_info = ", ".join(requested) if requested else "none"

        def _if_requested(key: str, value: str | None) -> str:
            return (value or "Not specified") if key in requested else "Not specified"

        system, user = prompt_loader.render(
            "email_generation_v2",
            job_title=job.job_title or "the role",
            company=job.company or "",
            recruiter_name=_resolve_recruiter_first_name(job.recruiter_name, job.recruiter_email),
            skills=", ".join(job.skills) if job.skills else "Not specified",
            job_summary=job.job_summary or "Not specified",
            required_candidate_info=required_info,
            match_score=f"{match.match_score:.0%}",
            matching_skills=", ".join(match.matching_skills) if match.matching_skills else "None",
            missing_skills=", ".join(match.missing_skills) if match.missing_skills else "None",
            resume_text=truncated_resume,
            candidate_name=candidate_name,
            current_ctc=_if_requested("current_ctc", p.current_ctc),
            expected_ctc=_if_requested("expected_ctc", p.expected_ctc),
            notice_period=_if_requested("notice_period", p.notice_period),
            current_location=_if_requested("current_location", p.current_location),
            total_experience=_if_requested("total_experience", p.total_experience),
            linkedin_url=p.linkedin_url or "",
        )
        text, inp, out = await self._call_with_retry(system, user)
        result = await self._parse_with_retry(
            EmailGenerationResult, text, system, user, label="email_generation"
        )
        return result, TokenUsage(
            input_tokens=inp, output_tokens=out, provider="", model=self._model
        )

    async def _call_with_retry(self, system: str, user: str) -> tuple[str, int, int]:
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
                usage = response.usage
                inp = getattr(usage, "prompt_tokens", 0) or 0
                out = getattr(usage, "completion_tokens", 0) or 0
                logger.debug(
                    "groq response received",
                    attempt=attempt,
                    length=len(text),
                    input_tokens=inp,
                    output_tokens=out,
                )
                return text, inp, out
            except AIRateLimitError:
                raise
            except AIProviderError:
                raise
            except GroqRateLimitError as exc:
                raise AIRateLimitError(
                    f"Groq rate limit: {exc}",
                    limit_type=_rate_limit_type(exc),
                ) from exc
            except Exception as exc:
                last_exc = exc
                delay = _RETRY_BASE_DELAY * (2**attempt)
                logger.warning(
                    "groq call failed, retrying", attempt=attempt, delay=delay, error=str(exc)
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
        text2, _, _ = await self._call_with_retry(system, clarified_user)
        try:
            return self._parse(model_cls, text2)
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
    if name and name.strip():
        return name.strip().split()[0].capitalize()
    return ""
