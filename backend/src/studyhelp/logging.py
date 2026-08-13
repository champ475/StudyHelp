"""Structured JSON logging (CLAUDE.md: "structured (JSON) logging
throughout") — an ops necessity and, alongside the `events` table, part of
the research artifact. This is process-level operational logging; the
`events` table (db/models/event.py) is the durable, query-oriented
research dataset. They're deliberately separate: this can be shipped to a
log aggregator and rotated/dropped, the event log never is.
"""

import logging
import sys
from typing import Any

import structlog

from studyhelp.config import get_settings


def configure_logging() -> None:
    settings = get_settings()
    level = logging.getLevelName(settings.log_level.upper())
    if not isinstance(level, int):
        level = logging.INFO

    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=level)

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> Any:
    return structlog.get_logger(name)
