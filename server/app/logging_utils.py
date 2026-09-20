"""Shared logging helpers for Docify chat/retrieval diagnostics."""

from __future__ import annotations

import logging
import sys
import traceback

_configured = False


def get_logger(name: str = "docify") -> logging.Logger:
    global _configured
    logger = logging.getLogger(name)
    if not _configured:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s %(levelname)s [%(name)s] %(message)s",
                datefmt="%H:%M:%S",
            )
        )
        root = logging.getLogger("docify")
        if not root.handlers:
            root.addHandler(handler)
            root.setLevel(logging.INFO)
            root.propagate = False
        _configured = True
    return logger


def log_exception(logger: logging.Logger, stage: str, exc: BaseException) -> None:
    logger.error(
        "%s failed: %s: %s\n%s",
        stage,
        type(exc).__name__,
        exc,
        traceback.format_exc(),
    )
