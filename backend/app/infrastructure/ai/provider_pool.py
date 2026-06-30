"""ProviderPool — wraps multiple IAIProvider instances with automatic rotation.

On AIRateLimitError, the offending provider is put in cooldown and the next
provider in the list is tried. rpm → 65 s cooldown; rpd → until midnight UTC.
All providers cooling simultaneously → AIProviderError with user-friendly message.
"""

from __future__ import annotations

import time
from datetime import UTC, datetime, timedelta

import structlog

from app.domain.entities.job_post import JobPostEntity
from app.domain.exceptions import AIProviderError, AIRateLimitError
from app.domain.interfaces.ai_provider import (
    EmailGenerationResult,
    IAIProvider,
    JobExtractionResult,
    ResumeMatchResult,
    TokenUsage,
    UserProfileInfo,
)

logger = structlog.get_logger(__name__)

_RPM_COOLDOWN_SECONDS = 65


def _rpd_cooldown_seconds() -> float:
    now = datetime.now(UTC)
    midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    return (midnight - now).total_seconds()


class ProviderPool(IAIProvider):
    """Ordered list of providers with automatic cooldown-based rotation."""

    def __init__(self, providers: list[tuple[str, IAIProvider]]) -> None:
        if not providers:
            raise ValueError("ProviderPool requires at least one provider")
        self._providers = providers  # [(label, provider), ...]
        self._blocked_until: dict[str, float] = {}  # label → monotonic timestamp

    def _available(self) -> list[tuple[str, IAIProvider]]:
        now = time.monotonic()
        return [
            (label, p) for label, p in self._providers if self._blocked_until.get(label, 0) <= now
        ]

    def _block(self, label: str, limit_type: str) -> None:
        seconds = _rpd_cooldown_seconds() if limit_type == "rpd" else _RPM_COOLDOWN_SECONDS
        self._blocked_until[label] = time.monotonic() + seconds
        logger.warning(
            "ai provider rate-limited",
            provider=label,
            limit_type=limit_type,
            cooldown_seconds=round(seconds),
        )

    async def extract_job_details(self, post_text: str) -> tuple[JobExtractionResult, TokenUsage]:
        available = self._available()
        if not available:
            raise AIProviderError(
                "All AI providers are temporarily unavailable. Please try again in a moment."
            )
        for label, provider in available:
            try:
                result, usage = await provider.extract_job_details(post_text)
                usage.provider = label
                return result, usage
            except AIRateLimitError as exc:
                self._block(label, exc.limit_type)
        raise AIProviderError(
            "All AI providers are temporarily unavailable. Please try again in a moment."
        )

    async def analyze_resume_match(
        self, job: JobPostEntity, resume_text: str
    ) -> tuple[ResumeMatchResult, TokenUsage]:
        available = self._available()
        if not available:
            raise AIProviderError(
                "All AI providers are temporarily unavailable. Please try again in a moment."
            )
        for label, provider in available:
            try:
                result, usage = await provider.analyze_resume_match(job, resume_text)
                usage.provider = label
                return result, usage
            except AIRateLimitError as exc:
                self._block(label, exc.limit_type)
        raise AIProviderError(
            "All AI providers are temporarily unavailable. Please try again in a moment."
        )

    async def generate_application_email(
        self,
        job: JobPostEntity,
        resume_text: str,
        match: ResumeMatchResult,
        candidate_name: str = "",
        profile: UserProfileInfo | None = None,
    ) -> tuple[EmailGenerationResult, TokenUsage]:
        available = self._available()
        if not available:
            raise AIProviderError(
                "All AI providers are temporarily unavailable. Please try again in a moment."
            )
        for label, provider in available:
            try:
                result, usage = await provider.generate_application_email(
                    job, resume_text, match, candidate_name, profile
                )
                usage.provider = label
                return result, usage
            except AIRateLimitError as exc:
                self._block(label, exc.limit_type)
        raise AIProviderError(
            "All AI providers are temporarily unavailable. Please try again in a moment."
        )
