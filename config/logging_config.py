"""
JTech Tally Bridge - Logging configuration

Provides a single configured logger for the whole application.
Use `from config.logging_config import get_logger` everywhere
instead of bare `print()` calls.
"""

import logging
from logging.handlers import RotatingFileHandler

from config.settings import LOG_FILE, LOG_LEVEL

_CONFIGURED = False


def configure_logging():
    """Configure root logger once. Safe to call multiple times."""

    global _CONFIGURED
    if _CONFIGURED:
        return

    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console = logging.StreamHandler()
    console.setLevel(LOG_LEVEL)
    console.setFormatter(formatter)

    file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=2_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setLevel(LOG_LEVEL)
    file_handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(LOG_LEVEL)
    root.addHandler(console)
    root.addHandler(file_handler)

    # Silence noisy third-party libs
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    _CONFIGURED = True


def get_logger(name):
    configure_logging()
    return logging.getLogger(name)
