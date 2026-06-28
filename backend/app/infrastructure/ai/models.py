"""Re-export AI result types for use within the infrastructure layer."""

from app.domain.interfaces.ai_provider import (  # noqa: F401
    EmailGenerationResult,
    JobExtractionResult,
    ResumeMatchResult,
)
