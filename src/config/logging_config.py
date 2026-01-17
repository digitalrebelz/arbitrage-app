"""Logging configuration using Loguru."""

import sys
from pathlib import Path

from loguru import logger

from src.config.settings import settings


def setup_logging() -> None:
    """Configure logging for the application."""
    # Remove default handler
    logger.remove()

    # Console handler - INFO level
    logger.add(
        sys.stderr,
        format=(
            "<green>{time:HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan> - "
            "<level>{message}</level>"
        ),
        level=settings.LOG_LEVEL,
        colorize=True,
    )

    # Ensure logs directory exists
    log_dir = Path(settings.LOG_FILE).parent
    log_dir.mkdir(parents=True, exist_ok=True)

    # File handler - DEBUG level, rotating
    logger.add(
        settings.LOG_FILE,
        rotation="10 MB",
        retention="7 days",
        level="DEBUG",
        format=(
            "{time:YYYY-MM-DD HH:mm:ss} | " "{level: <8} | " "{name}:{function}:{line} - {message}"
        ),
        compression="zip",
    )

    # Error file - ERROR level only
    error_log = str(Path(settings.LOG_FILE).parent / "errors.log")
    logger.add(
        error_log,
        rotation="10 MB",
        retention="30 days",
        level="ERROR",
        format=(
            "{time:YYYY-MM-DD HH:mm:ss} | "
            "{level: <8} | "
            "{name}:{function}:{line} - {message}\n{exception}"
        ),
        backtrace=True,
        diagnose=True,
    )

    logger.info("Logging configured")


def get_logger(name: str) -> logger:
    """
    Get a logger instance with a specific name.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured logger instance
    """
    return logger.bind(name=name)
