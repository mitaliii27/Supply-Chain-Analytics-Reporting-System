# etl/logger.py – Centralised logging setup

import logging
import sys
from etl.config import LOG_LEVEL, LOG_FORMAT, LOG_FILE


def get_logger(name: str) -> logging.Logger:
    """Return a configured logger writing to both console and file."""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))

    fmt = logging.Formatter(LOG_FORMAT, datefmt="%Y-%m-%d %H:%M:%S")

    # Console handler
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    # File handler
    try:
        fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
        fh.setFormatter(fmt)
        logger.addHandler(fh)
    except OSError:
        pass

    return logger
