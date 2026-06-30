"""AI provider factory — builds a ProviderPool from configured keys."""

from __future__ import annotations

from app.core.config import settings
from app.domain.interfaces.ai_provider import IAIProvider


def get_ai_provider() -> IAIProvider:
    from app.infrastructure.ai.provider_pool import ProviderPool

    providers: list[tuple[str, IAIProvider]] = []

    if settings.GROQ_API_KEY:
        from app.infrastructure.ai.groq_provider import GroqProvider

        providers.append(
            (
                "groq_key1",
                GroqProvider(api_key=settings.GROQ_API_KEY, model_name=settings.GROQ_MODEL),
            )
        )

    if settings.GROQ_API_KEY_2:
        from app.infrastructure.ai.groq_provider import GroqProvider

        providers.append(
            (
                "groq_key2",
                GroqProvider(api_key=settings.GROQ_API_KEY_2, model_name=settings.GROQ_MODEL),
            )
        )

    if settings.GEMINI_API_KEY:
        from app.infrastructure.ai.gemini_provider import GeminiProvider

        providers.append(
            (
                "gemini",
                GeminiProvider(api_key=settings.GEMINI_API_KEY, model_name=settings.GEMINI_MODEL),
            )
        )

    if not providers:
        raise RuntimeError(
            "No AI provider keys configured. Set at least one of: GROQ_API_KEY, GROQ_API_KEY_2, GEMINI_API_KEY."
        )

    return ProviderPool(providers)
