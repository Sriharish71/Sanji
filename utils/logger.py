"""
Central logging configuration for SANJI.
Provides structured formatting with both console and rotating file outputs.
"""

import logging
import sys
from pathlib import Path
from typing import Optional


def setup_logger(
    name: str = "SANJI",
    level: str = "INFO",
    log_file: Optional[str] = "sanji.log",
) -> logging.Logger:
    """Configures and returns a standardized logger."""
    logger = logging.getLogger(name)

    # Avoid duplicate handlers if setup is called multiple times
    if logger.handlers:
        return logger

    log_level = getattr(logging, level.upper(), logging.INFO)
    logger.setLevel(log_level)

    formatter = logging.Formatter(
        fmt="[%(asctime)s] [%(levelname)s] [%(name)s:%(module)s]: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console Handler (Stdout)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File Handler
    if log_file:
        try:
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(log_path, encoding="utf-8")
            file_handler.setLevel(log_level)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except Exception as e:
            logger.warning(f"Failed to initialize file logger: {e}")

    logger.propagate = False
    return logger


# Default application-wide logger
logger = setup_logger()
