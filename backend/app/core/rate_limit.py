"""Slowapi rate limiter — singleton imported by all endpoint modules."""

from __future__ import annotations

import structlog
from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request

logger = structlog.get_logger(__name__)


def get_user_key(request: Request) -> str:
    """Rate-limit key for authenticated routes: the JWT subject (user UUID).

    Falls back to the client IP so unauthenticated calls are still bounded.
    """
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        try:
            # Import here to avoid circular imports at module load time
            from app.core.security import decode_token

            payload = decode_token(auth[7:])
            sub = payload.get("sub")
            if sub:
                return f"user:{sub}"
        except Exception:  # — any bad token falls through to IP
            pass
    return get_remote_address(request)


# Default key is IP address (used for the limiter-level default limit and
# any route that doesn't override key_func).
limiter = Limiter(key_func=get_remote_address)
