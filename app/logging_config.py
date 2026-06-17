"""Shared logging configuration for the learning lab API."""

from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

DEFAULT_LOG_FILE = "outputs/logs/app.log"
LOG_FILE_ENV = "APP_LOG_FILE"
LOG_LEVEL_ENV = "APP_LOG_LEVEL"
BASE_LOGGER_NAME = "lab"


def configure_logging(name: str | None = None) -> logging.Logger:
    """Configure file and console logging, then return a project logger."""
    base_logger = logging.getLogger(BASE_LOGGER_NAME)
    if not base_logger.handlers:
        level_name = os.environ.get(LOG_LEVEL_ENV, "INFO").strip().upper()
        level = getattr(logging, level_name, logging.INFO)
        formatter = logging.Formatter(
            "%(asctime)s %(levelname)s %(name)s %(message)s"
        )

        base_logger.setLevel(level)
        base_logger.propagate = False

        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        base_logger.addHandler(stream_handler)

        log_file = Path(os.environ.get(LOG_FILE_ENV, DEFAULT_LOG_FILE))
        try:
            log_file.parent.mkdir(parents=True, exist_ok=True)
            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=1_000_000,
                backupCount=3,
                encoding="utf-8",
            )
            file_handler.setFormatter(formatter)
            base_logger.addHandler(file_handler)
        except OSError as exc:
            base_logger.warning("File logging disabled: %s", exc)

    if not name or name == BASE_LOGGER_NAME:
        return base_logger
    return logging.getLogger(f"{BASE_LOGGER_NAME}.{name}")
