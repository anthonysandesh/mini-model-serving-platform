"""Logging configuration."""

from __future__ import annotations

import logging
import os
from typing import Optional

try:
    from pythonjsonlogger import jsonlogger
except ImportError:  # pragma: no cover - fallback for limited environments
    class _PlainFormatter(logging.Formatter):
        def format(self, record: logging.LogRecord) -> str:  # type: ignore[override]
            return super().format(record)

    class jsonlogger:  # type: ignore
        JsonFormatter = _PlainFormatter


def configure_logging(level: str = "INFO") -> logging.Logger:
    logger = logging.getLogger("mmsp")
    if logger.handlers:
        return logger

    log_level = getattr(logging, os.environ.get("LOG_LEVEL", level).upper(), logging.INFO)
    logger.setLevel(log_level)
    handler = logging.StreamHandler()
    formatter = jsonlogger.JsonFormatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger


def get_logger(name: Optional[str] = None) -> logging.Logger:
    base = logging.getLogger("mmsp")
    if not base.handlers:
        configure_logging()
    return base if name is None else base.getChild(name)
