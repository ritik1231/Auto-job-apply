"""FastAPI exception handlers.

Exception classes themselves live in app/domain/exceptions.py (no framework
dependency). This module re-exports them for convenience and wires them to
FastAPI's handler system.
"""

from __future__ import annotations

import structlog
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

# Re-export so existing imports of the form
#   from app.core.exceptions import ResumeNotFoundError
# continue to work without changes.
from app.domain.exceptions import (  # noqa: F401
    AIProviderError,
    AIResponseParseError,
    AppException,
    ApplicationAlreadySentError,
    AuthenticationException,
    DatabaseError,
    DomainException,
    GmailSendError,
    InfrastructureException,
    InvalidJobPostError,
    InvalidTokenError,
    OAuthError,
    ResumeNotFoundError,
    StorageError,
    TokenExpiredError,
)

logger = structlog.get_logger(__name__)


# ── Error response helper ──────────────────────────────────────────────────────


def _error_response(
    status_code: int,
    error_code: str,
    message: str,
    request: Request,
    details: object = None,
) -> JSONResponse:
    from structlog.contextvars import get_contextvars

    request_id = get_contextvars().get("request_id", "")
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": error_code,
                "message": message,
                "details": details,
                "request_id": request_id,
            }
        },
    )


# ── Exception handlers ────────────────────────────────────────────────────────


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    logger.warning("application error", error_code=exc.error_code, message=exc.message)
    return _error_response(exc.status_code, exc.error_code, exc.message, request, exc.details)


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    error_codes = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        405: "METHOD_NOT_ALLOWED",
        409: "CONFLICT",
        422: "UNPROCESSABLE_ENTITY",
        429: "RATE_LIMIT_EXCEEDED",
    }
    code = error_codes.get(exc.status_code, "HTTP_ERROR")
    message = str(exc.detail) if exc.detail else "An error occurred"
    return _error_response(exc.status_code, code, message, request)


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    details = [
        {"field": ".".join(str(loc) for loc in err["loc"]), "message": err["msg"]}
        for err in exc.errors()
    ]
    return _error_response(422, "VALIDATION_ERROR", "Request validation failed", request, details)


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("unhandled exception", exc_info=exc)
    return _error_response(500, "INTERNAL_ERROR", "An unexpected error occurred", request)
