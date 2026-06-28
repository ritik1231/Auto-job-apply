"""AI provider factory — returns the configured IAIProvider implementation."""

from __future__ import annotations

from app.core.config import settings
from app.domain.interfaces.ai_provider import IAIProvider


def get_ai_provider() -> IAIProvider:
    provider_name = getattr(settings, "AI_PROVIDER", "gemini")

    if provider_name == "gemini":
        from app.infrastructure.ai.gemini_provider import GeminiProvider

        if not settings.GEMINI_API_KEY:
            raise RuntimeError("GEMINI_API_KEY is not set. Add it to your .env file.")
        return GeminiProvider(
            api_key=settings.GEMINI_API_KEY,
            model_name=settings.GEMINI_MODEL,
        )

    if provider_name == "groq":
        from app.infrastructure.ai.groq_provider import GroqProvider

        if not settings.GROQ_API_KEY:
            raise RuntimeError("GROQ_API_KEY is not set. Add it to your .env file.")
        return GroqProvider(
            api_key=settings.GROQ_API_KEY,
            model_name=settings.GROQ_MODEL,
        )

    raise NotImplementedError(
        f"AI provider '{provider_name}' is not implemented. " "Supported: 'gemini', 'groq'"
    )
