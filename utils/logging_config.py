"""
Logging configuration for the AI Organization system.
Structured JSON logging via structlog for CloudWatch compatibility.
"""

import logging
import structlog
import sys


def configure_logging(level: str = "INFO", json_output: bool = False):
    """Configure structlog with appropriate processors for env."""

    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    if json_output:
        # Production: JSON for CloudWatch
        processors = shared_processors + [
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ]
    else:
        # Development: colored console
        processors = shared_processors + [structlog.dev.ConsoleRenderer(colors=True)]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, level.upper(), logging.INFO),
    )


# Convenience alias used by agent_service.py and other entry points
def setup_logging(level: str = "INFO", json_output: bool = False):
    """Alias for configure_logging - preferred entry-point name."""
    configure_logging(level=level, json_output=json_output)
