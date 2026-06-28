import uuid
from collections.abc import Awaitable, Callable

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

logger = structlog.get_logger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Attach a UUID to every request and expose it in the response headers.

    The ID is also bound to the structlog context so every log line emitted
    during the request automatically includes `request_id`.
    """

    def __init__(self, app: ASGIApp, header_name: str = "X-Request-ID") -> None:
        super().__init__(app)
        self.header_name = header_name

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        structlog.contextvars.clear_contextvars()

        request_id = request.headers.get(self.header_name) or str(uuid.uuid4())
        structlog.contextvars.bind_contextvars(request_id=request_id)

        logger.debug(
            "request started",
            method=request.method,
            path=request.url.path,
        )

        response: Response = await call_next(request)
        response.headers[self.header_name] = request_id

        logger.info(
            "request completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
        )

        return response
