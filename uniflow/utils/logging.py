"""Logging utilities for UniFlow."""

import logging
import sys
from pathlib import Path


def setup_logger(
    name: str = "uniflow",
    level: int = logging.INFO,
    log_file: str = None,
) -> logging.Logger:
    """Setup logger for UniFlow.

    Args:
        name: Logger name
        level: Logging level
        log_file: Optional log file path

    Returns:
        Configured logger
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_format = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    console_handler.setFormatter(console_format)
    logger.addHandler(console_handler)

    # File handler if specified
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(level)
        file_handler.setFormatter(console_format)
        logger.addHandler(file_handler)

    return logger


# Default logger
logger = setup_logger()


def get_logger(name: str = "uniflow") -> logging.Logger:
    """Get a logger by name.

    Args:
        name: Logger name

    Returns:
        Logger instance
    """
    return logging.getLogger(name)
