"""
utils/logger.py
───────────────
Centralized logging. Call setup_logging() once at startup (in main.py).
All other modules import logger from loguru directly:
    from loguru import logger
"""

import sys
from pathlib import Path

from loguru import logger

from config.settings import LOG_DIR


def setup_logging(verbose: bool = False) -> None:
    """
    Configure loguru for the application.
    - Console: INFO (or DEBUG if verbose)
    - File: DEBUG, rotated daily, kept 14 days
    """
    logger.remove()  # remove default handler

    level = "DEBUG" if verbose else "INFO"

    # Console handler — clean format for humans
    logger.add(
        sys.stderr,
        level=level,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan> — {message}",
        colorize=True,
    )

    # File handler — full debug info
    logger.add(
        LOG_DIR / "piano_leads_{time:YYYY-MM-DD}.log",
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{line} — {message}",
        rotation="00:00",   # new file each day
        retention="14 days",
        compression="zip",
    )
