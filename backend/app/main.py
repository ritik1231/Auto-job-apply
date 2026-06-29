"""FastAPI application factory."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.requests import Request

from app.core.config import settings
from app.core.exceptions import (
    AppException,
    app_exception_handler,
    generic_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)
from app.core.logging import configure_logging
from app.core.middleware import RequestIDMiddleware
from app.core.rate_limit import limiter

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    configure_logging(settings.LOG_LEVEL, is_development=settings.is_development)
    logger.info(
        "application starting",
        version=settings.APP_VERSION,
        env=settings.APP_ENV,
    )
    yield
    logger.info("application shutting down")


async def _rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    request_id = structlog.contextvars.get_contextvars().get("request_id", "")
    return JSONResponse(
        status_code=429,
        content={
            "error": {
                "code": "RATE_LIMIT_EXCEEDED",
                "message": "Rate limit exceeded. Please slow down.",
                "details": None,
                "request_id": request_id,
            }
        },
        headers={"Retry-After": "60"},
    )


def create_app() -> FastAPI:
    app = FastAPI(
        title="SmartApply API",
        version=settings.APP_VERSION,
        docs_url="/api/v1/docs",
        redoc_url="/api/v1/redoc",
        openapi_url="/api/v1/openapi.json",
        lifespan=lifespan,
    )

    # ─── Rate limiter state ────────────────────────────────────────────
    app.state.limiter = limiter

    # ─── Middleware (outermost first) ──────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )
    app.add_middleware(RequestIDMiddleware)

    # ─── Exception handlers ────────────────────────────────────────────
    app.add_exception_handler(RateLimitExceeded, _rate_limit_handler)  # type: ignore[arg-type]
    app.add_exception_handler(AppException, app_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, validation_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, generic_exception_handler)  # type: ignore[arg-type]

    # ─── Routers ──────────────────────────────────────────────────────
    from app.api.v1.router import router as v1_router

    app.include_router(v1_router)

    return app


app = create_app()
