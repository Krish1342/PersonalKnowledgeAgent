"""
Logging configuration and utilities.
Supports both JSON and text formatting for different environments.
"""

import logging
import logging.config
import json
import sys
from typing import Any, Dict

from app.config import get_settings


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields
        if hasattr(record, "extra") and record.extra:
            log_data.update(record.extra)

        return json.dumps(log_data)


def setup_logging() -> None:
    """
    Configure application logging.
    Sets up appropriate formatters and handlers based on environment.
    """
    settings = get_settings()

    # Determine formatter
    if settings.LOG_FORMAT == "json":
        formatter = JSONFormatter()
    else:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.LOG_LEVEL))

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Suppress verbose logs from dependencies
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("fastapi").setLevel(logging.INFO)


def get_logger(name: str) -> logging.LoggerAdapter:
    """
    Get a logger instance with optional extra context.

    Args:
        name: Logger name (typically __name__)

    Returns:
        LoggerAdapter for structured logging
    """
    logger = logging.getLogger(name)
    return logging.LoggerAdapter(logger, extra={})
