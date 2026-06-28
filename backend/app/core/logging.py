import logging
import sys

import structlog


def configure_logging(log_level: str = "INFO", *, is_development: bool = True) -> None:
    """Configure structlog for the application.

    In development: coloured console output.
    In production: JSON lines to stdout.
    """
    level = getattr(logging, log_level.upper(), logging.INFO)

    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
    ]

    if is_development:
        processors: list[structlog.types.Processor] = [
            *shared_processors,
            structlog.dev.ConsoleRenderer(colors=True),
        ]
    else:
        processors = [
            *shared_processors,
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Redirect stdlib logging through structlog so third-party logs share format.
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=level,
        force=True,
    )
    logging.getLogger("uvicorn").handlers = []
    logging.getLogger("uvicorn.access").handlers = []
