"""Pytest configuration and shared fixtures."""

import json
from collections.abc import Generator
from pathlib import Path

import pytest

from opendental_query.models.config import AppConfig, OfficeConfig


@pytest.fixture
def tmp_config_dir(tmp_path: Path) -> Path:
    """Create a temporary configuration directory for testing.

    Args:
        tmp_path: Pytest temporary directory fixture

    Returns:
        Path to temporary config directory
    """
    config_dir = tmp_path / ".opendental-query-test"
    config_dir.mkdir(mode=0o700)
    return config_dir


@pytest.fixture
def sample_office_config() -> OfficeConfig:
    """Create a sample office configuration for testing.

    Returns:
        OfficeConfig instance with test data
    """
    return OfficeConfig(
        office_id="test-office",
        host="localhost",
        port=3306,
        database="test_opendental",
        username="test_user",
        description="Test office database",
    )


@pytest.fixture
def sample_app_config(tmp_config_dir: Path) -> AppConfig:
    """Create a sample application configuration for testing.

    Args:
        tmp_config_dir: Temporary config directory fixture

    Returns:
        AppConfig instance with test data
    """
    return AppConfig(
        config_dir=tmp_config_dir,
        vault_file="test.vault",
        log_file="test.log",
        audit_file="test_audit.jsonl",
        vault_auto_lock_seconds=300,
        query_timeout_seconds=60,
        max_concurrent_queries=5,
    )


@pytest.fixture
def mock_logger(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, str]]:
    """Mock logger to capture log messages during tests.

    Args:
        monkeypatch: Pytest monkeypatch fixture

    Returns:
        List that accumulates (level, message) tuples
    """
    log_messages: list[tuple[str, str]] = []

    class MockLogger:
        def debug(self, msg: str) -> None:
            log_messages.append(("DEBUG", msg))

        def info(self, msg: str) -> None:
            log_messages.append(("INFO", msg))

        def warning(self, msg: str) -> None:
            log_messages.append(("WARNING", msg))

        def error(self, msg: str) -> None:
            log_messages.append(("ERROR", msg))

    def mock_get_logger(name: str) -> MockLogger:
        return MockLogger()

    monkeypatch.setattr("opendental_query.utils.app_logger.get_logger", mock_get_logger)

    return log_messages


@pytest.fixture
def sample_vault_file(tmp_config_dir: Path) -> Path:
    """Create a sample vault file for testing.

    Args:
        tmp_config_dir: Temporary config directory fixture

    Returns:
        Path to created vault file
    """
    vault_file = tmp_config_dir / "test.vault"
    vault_data = {
        "version": "1.0",
        "encrypted_data": "dummy_encrypted_data",
        "salt": "dummy_salt",
    }

    with vault_file.open("w", encoding="utf-8") as f:
        json.dump(vault_data, f)

    vault_file.chmod(0o600)
    return vault_file


@pytest.fixture
def sample_audit_file(tmp_config_dir: Path) -> Path:
    """Create a sample audit log file for testing.

    Args:
        tmp_config_dir: Temporary config directory fixture

    Returns:
        Path to created audit log file
    """
    audit_file = tmp_config_dir / "test_audit.jsonl"
    audit_file.touch(mode=0o600)
    return audit_file


@pytest.fixture
def cleanup_loggers() -> Generator[None, None, None]:
    """Clean up logger state after tests.

    Yields:
        None (runs test, then cleans up)
    """
    yield

    # Clear logger registry
    import logging

    from opendental_query.utils import app_logger

    app_logger._loggers.clear()
    app_logger._configured = False

    # Remove all handlers from opendental_query logger
    logger = logging.getLogger("opendental_query")
    logger.handlers.clear()
