"""Structured, readable logging for the backend.

Logs request lifecycle events (upload, parse, analysis start/complete, timing,
failures) with request ids. Never logs contract contents, extracted legal
text, or secrets — only ids, counts and durations.
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

LOG_FORMAT = "%(asctime)s %(levelname)-7s [%(name)s] %(message)s"


def get_logger(name: str = "contractiq") -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt="%H:%M:%S"))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False
    return logger


def log_to_file(logger: logging.Logger, path: Path) -> None:
    """Optionally mirror logs to a project-relative file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if not any(isinstance(h, logging.FileHandler) and h.baseFilename == str(path) for h in logger.handlers):
        fh = logging.FileHandler(path, encoding="utf-8")
        fh.setFormatter(logging.Formatter(LOG_FORMAT))
        logger.addHandler(fh)


def log_event(logger: logging.Logger, event: str, request_id: str = "-", **fields) -> None:
    """One structured key=value line; values must be metadata, never content."""
    parts = [f"event={event}", f"request_id={request_id}"]
    parts += [f"{k}={v}" for k, v in fields.items() if v is not None]
    logger.info(" ".join(str(p) for p in parts))
