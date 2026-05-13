"""structlog configuration — JSON output, request ID propagation.

Call configure_logging() once at application startup before any log output.
"""

import logging
import sys

import structlog
from structlog.types import EventDict

# Field names that must never appear in log output.
_REDACTED_FIELDS = frozenset(
    [
        "password",
        "secret",
        "token",
        "api_key",
        "access_token",
        "refresh_token",
        "authorization",
        "client_secret",
    ]
)


def _redact_secrets(
    logger: logging.Logger,
    method: str,
    event_dict: EventDict,
) -> EventDict:
    """Strip known secret field names from log events before output."""
    # logger and method are part of the structlog processor signature but unused here
    _ = logger, method
    for field in _REDACTED_FIELDS:
        if field in event_dict:
            event_dict[field] = "***REDACTED***"
    return event_dict


def configure_logging(log_level: str = "INFO") -> None:
    """Configure structlog for JSON output. Call once at startup."""
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            _redact_secrets,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelName(log_level.upper())
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )
