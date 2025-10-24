"""Application logging configuration and utilities."""

import logging
import sys
from datetime import UTC, datetime, timedelta
from logging.handlers import RotatingFileHandler
from pathlib import Path

from opendental_query.constants import (
    LOG_BACKUP_COUNT,
    LOG_MAX_BYTES,
)

# Global logger registry
_loggers: dict[str, logging.Logger] = {}
_configured: bool = False


def setup_logging(
    log_file: Path | None = None,
    *,
    console_level: int = logging.INFO,
    file_level: int = logging.DEBUG,
) -> None:
    """Configure application logging with file rotation and console output.

    Sets up two handlers:
    - Console handler: INFO level, simple format for user messages
    - File handler: DEBUG level, detailed format with rotation

    Args:
        log_file: Path to log file (None = console only)
        console_level: Logging level for console output (default: INFO)
        file_level: Logging level for file output (default: DEBUG)
    """
    global _configured

    # Get root logger for opendental_query package
    root_logger = logging.getLogger("opendental_query")
    root_logger.setLevel(logging.DEBUG)  # Capture all levels
    root_logger.handlers.clear()  # Remove existing handlers

    # Console handler - simple format for users
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(console_level)
    console_formatter = logging.Formatter(fmt="%(levelname)s: %(message)s")
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # File handler - detailed format with rotation
    if log_file is not None:
        # Ensure log directory exists
        from opendental_query.utils.file_utils import ensure_directory

        ensure_directory(log_file.parent)

        file_handler = RotatingFileHandler(
            filename=log_file,
            maxBytes=LOG_MAX_BYTES,
            backupCount=LOG_BACKUP_COUNT,
            encoding="utf-8",
        )
        file_handler.setLevel(file_level)
        file_formatter = logging.Formatter(
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)

    _configured = True


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for a module.

    Args:
        name: Logger name (typically __name__ from the calling module)

    Returns:
        Logger instance
    """
    if name not in _loggers:
        _loggers[name] = logging.getLogger(name)
    return _loggers[name]


def is_configured() -> bool:
    """Check if logging has been configured.

    Returns:
        True if setup_logging() has been called
    """
    return _configured


def cleanup_old_logs(log_file: Path, retention_days: int = 30) -> None:
    """Remove old application log files based on retention period.

    Deletes log files (main file and rotated backups) that are older than
    the specified retention period.

    Args:
        log_file: Path to the main log file
        retention_days: Number of days to retain logs (default: 30)
    """
    if not log_file.exists():
        return

    cutoff_date = datetime.now(UTC) - timedelta(days=retention_days)
    logger = get_logger(__name__)

    # Check main log file
    try:
        mtime = datetime.fromtimestamp(log_file.stat().st_mtime, tz=UTC)
        if mtime < cutoff_date:
            log_file.unlink()
            logger.info(f"Deleted old log file: {log_file}")
    except OSError as e:
        logger.error(f"Failed to check/delete log file {log_file}: {e}")

    # Check rotated backup files (app.log.1, app.log.2, etc.)
    log_dir = log_file.parent
    log_name = log_file.name
    for backup_file in log_dir.glob(f"{log_name}.*"):
        try:
            if not backup_file.is_file():
                continue
            mtime = datetime.fromtimestamp(backup_file.stat().st_mtime, tz=UTC)
            if mtime < cutoff_date:
                backup_file.unlink()
                logger.info(f"Deleted old backup log: {backup_file}")
        except OSError as e:
            logger.error(f"Failed to check/delete backup log {backup_file}: {e}")
