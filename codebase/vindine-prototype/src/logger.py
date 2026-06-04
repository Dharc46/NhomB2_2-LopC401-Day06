"""Structured logging for VinDine demo visibility."""

import logging
import sys


_configured = False


def setup_logging() -> None:
    """Configure root logger with a clean format for demo terminal output."""
    global _configured
    if _configured:
        return
    _configured = True

    formatter = logging.Formatter(
        "%(asctime)s | %(name)-20s | %(levelname)-5s | %(message)s",
        datefmt="%H:%M:%S",
    )
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root = logging.getLogger("vindine")
    root.setLevel(logging.INFO)
    root.addHandler(handler)
    root.propagate = False


def get_logger(name: str) -> logging.Logger:
    setup_logging()
    return logging.getLogger(f"vindine.{name}")
