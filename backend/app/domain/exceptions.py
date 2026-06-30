"""Domain exception hierarchy — zero framework dependencies.

FastAPI exception handlers in app/core/exceptions.py import from here.
"""


class AppException(Exception):
    """Root for all application exceptions."""

    status_code: int = 500
    error_code: str = "INTERNAL_ERROR"

    def __init__(self, message: str, details: object = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details


# ── Domain ────────────────────────────────────────────────────────────────────


class DomainException(AppException):
    """A domain invariant was violated."""


class ResumeNotFoundError(DomainException):
    status_code = 404
    error_code = "RESUME_NOT_FOUND"


class ApplicationAlreadySentError(DomainException):
    status_code = 409
    error_code = "APPLICATION_ALREADY_SENT"


class DailyLimitError(DomainException):
    status_code = 429
    error_code = "DAILY_LIMIT_REACHED"


class InvalidJobPostError(DomainException):
    status_code = 400
    error_code = "INVALID_JOB_POST"


class InvalidFileTypeError(DomainException):
    status_code = 400
    error_code = "INVALID_FILE_TYPE"


class FileTooLargeError(DomainException):
    status_code = 400
    error_code = "FILE_TOO_LARGE"


# ── Infrastructure ────────────────────────────────────────────────────────────


class InfrastructureException(AppException):
    """An external dependency failed."""


class AIProviderError(InfrastructureException):
    status_code = 503
    error_code = "AI_PROVIDER_ERROR"


class AIRateLimitError(AIProviderError):
    """Provider returned 429. limit_type: 'rpm' → 60 s cooldown; 'rpd' → until midnight UTC."""

    status_code = 503
    error_code = "AI_RATE_LIMIT"

    def __init__(self, message: str, limit_type: str = "rpm") -> None:
        super().__init__(message)
        self.limit_type = limit_type  # "rpm" | "rpd"


class AIResponseParseError(InfrastructureException):
    status_code = 503
    error_code = "AI_RESPONSE_PARSE_ERROR"


class GmailSendError(InfrastructureException):
    status_code = 503
    error_code = "GMAIL_SEND_ERROR"


class DatabaseError(InfrastructureException):
    status_code = 500
    error_code = "DATABASE_ERROR"


class StorageError(InfrastructureException):
    status_code = 500
    error_code = "STORAGE_ERROR"


# ── Authentication ────────────────────────────────────────────────────────────


class AuthenticationException(AppException):
    status_code = 401


class InvalidTokenError(AuthenticationException):
    error_code = "INVALID_TOKEN"


class TokenExpiredError(AuthenticationException):
    error_code = "TOKEN_EXPIRED"


class OAuthError(AuthenticationException):
    error_code = "OAUTH_ERROR"
