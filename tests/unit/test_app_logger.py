"""Unit tests for application logger configuration and retention."""

from __future__ import annotations

import logging
import os
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from opendental_query.utils.app_logger import cleanup_old_logs, get_logger, setup_logging


def test_console_and_file_levels(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Console should respect console_level; file should respect file_level."""
    log_file = tmp_path / "app.log"

    # Configure logging: console=ERROR, file=DEBUG
    setup_logging(log_file=log_file, console_level=logging.ERROR, file_level=logging.DEBUG)
    logger = get_logger("opendental_query.test")

    logger.info("info message")
    logger.debug("debug message")
    logger.error("error message")

    # Console should only show ERROR message
    captured = capsys.readouterr()
    assert "info message" not in captured.err
    assert "debug message" not in captured.err
    assert "error message" in captured.err

    # File should contain DEBUG, INFO, and ERROR
    content = log_file.read_text(encoding="utf-8")
    assert "info message" in content
    assert "debug message" in content
    assert "error message" in content


def test_rotation_occurs_when_max_bytes_reached(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """RotatingFileHandler should roll over when maxBytes threshold is reached."""
    # Monkeypatch module-level values used by app_logger
    import opendental_query.utils.app_logger as app_logger

    monkeypatch.setattr(app_logger, "LOG_MAX_BYTES", 200, raising=False)
    monkeypatch.setattr(app_logger, "LOG_BACKUP_COUNT", 2, raising=False)

    log_file = tmp_path / "app.log"
    setup_logging(log_file=log_file, console_level=logging.CRITICAL, file_level=logging.DEBUG)
    logger = get_logger("opendental_query.test.rotation")

    # Write enough lines to exceed 200 bytes
    for i in range(400):
        logger.debug("x" * 50)

    # Allow IO to flush
    time.sleep(0.1)

    # Expect main file and at least one backup
    files = list(tmp_path.glob("app.log*"))
    assert any(f.name == "app.log" for f in files)
    assert any(f.name.startswith("app.log.") for f in files)


def test_cleanup_old_logs_removes_old_files(tmp_path: Path) -> None:
    """cleanup_old_logs should delete files older than retention cutoff."""
    log_file = tmp_path / "app.log"
    log_file.write_text("test\n", encoding="utf-8")

    # Create rotated backups
    backup1 = tmp_path / "app.log.1"
    backup2 = tmp_path / "app.log.2"
    backup1.write_text("old\n", encoding="utf-8")
    backup2.write_text("older\n", encoding="utf-8")

    # Set modification times to old dates
    old_time = (datetime.now(UTC) - timedelta(days=365)).timestamp()
    for f in (log_file, backup1, backup2):
        os.utime(f, (old_time, old_time))

    # All should be deleted with retention_days=0
    cleanup_old_logs(log_file, retention_days=0)

    assert not log_file.exists()
    assert not backup1.exists()
    assert not backup2.exists()


def test_cleanup_old_logs_handles_missing_log_file(tmp_path: Path) -> None:
    """cleanup_old_logs should handle missing log file gracefully."""
    log_file = tmp_path / "nonexistent.log"

    # Should not raise an error
    cleanup_old_logs(log_file, retention_days=30)


def test_cleanup_old_logs_keeps_recent_files(tmp_path: Path) -> None:
    """cleanup_old_logs should keep files within retention period."""
    log_file = tmp_path / "app.log"
    log_file.write_text("recent\n", encoding="utf-8")

    backup1 = tmp_path / "app.log.1"
    backup1.write_text("recent_backup\n", encoding="utf-8")

    # Files are recent (created just now), should not be deleted
    cleanup_old_logs(log_file, retention_days=30)

    assert log_file.exists()
    assert backup1.exists()
