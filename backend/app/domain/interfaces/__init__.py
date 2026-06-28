from app.domain.interfaces.ai_provider import (
    EmailGenerationResult,
    IAIProvider,
    JobExtractionResult,
    ResumeMatchResult,
)
from app.domain.interfaces.email_sender import IEmailSender
from app.domain.interfaces.repositories import (
    GmailTokenData,
    IApplicationRepository,
    IJobPostRepository,
    IResumeRepository,
    IUserRepository,
)
from app.domain.interfaces.storage import IResumeStorage

__all__ = [
    "IUserRepository",
    "IResumeRepository",
    "IJobPostRepository",
    "IApplicationRepository",
    "GmailTokenData",
    "IAIProvider",
    "JobExtractionResult",
    "ResumeMatchResult",
    "EmailGenerationResult",
    "IResumeStorage",
    "IEmailSender",
]
