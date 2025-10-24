"""
Unit tests for ConfigManager.

Tests config file loading, default creation, HTTPS validation, and rejection of HTTP URLs.
"""

import json
from pathlib import Path

import pytest

from opendental_query.core.config import ConfigManager
from opendental_query.models.config import AppConfig


class TestConfigLoad:
    """Test ConfigManager.load() behavior."""

    def test_load_creates_default_config_if_missing(self, tmp_path: Path) -> None:
        """Should create default config with HTTPS base URL if file missing."""
        config_dir = tmp_path / "config"
        config_path = config_dir / "config.json"
        manager = ConfigManager(config_path)

        config = manager.load()

        assert config_path.exists()
        assert isinstance(config, AppConfig)
        assert config.config_dir == config_dir
        assert config.api_base_url == "https://api.opendental.com/api/v1"
        assert config.max_concurrent_requests == 10
        assert config.query_timeout_seconds == 300

    def test_load_creates_parent_directory(self, tmp_path: Path) -> None:
        """Should create parent directories if they don't exist."""
        config_path = tmp_path / "nested" / "dir" / "config.json"
        manager = ConfigManager(config_path)

        config = manager.load()

        assert config_path.exists()
        assert config_path.parent.exists()
        assert isinstance(config, AppConfig)
        assert config.config_dir == config_path.parent

    def test_load_reads_existing_config(self, tmp_path: Path) -> None:
        """Should load config from existing file."""
        config_dir = tmp_path / "config"
        config_path = config_dir / "config.json"
        config_path.parent.mkdir(parents=True, exist_ok=True)

        # Write custom config (config_dir will be auto-added by manager)
        custom_config = {
            "api_base_url": "https://custom.example.com",
            "max_concurrent_requests": 5,
            "query_timeout_seconds": 120,
        }
        config_path.write_text(json.dumps(custom_config), encoding="utf-8")

        manager = ConfigManager(config_path)
        config = manager.load()

        assert config.config_dir == config_dir
        assert config.api_base_url == "https://custom.example.com"
        assert config.max_concurrent_requests == 5
        assert config.query_timeout_seconds == 120

    def test_load_rejects_invalid_json(self, tmp_path: Path) -> None:
        """Should raise ValueError for invalid JSON."""
        config_path = tmp_path / "config.json"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text("{ invalid json }", encoding="utf-8")

        manager = ConfigManager(config_path)

        with pytest.raises(ValueError, match="Invalid JSON"):
            manager.load()


class TestHTTPSValidation:
    """Test HTTPS URL validation and HTTP rejection."""

    def test_load_accepts_https_url(self, tmp_path: Path) -> None:
        """Should accept HTTPS URLs."""
        config_dir = tmp_path / "config"
        config_path = config_dir / "config.json"
        config_path.parent.mkdir(parents=True, exist_ok=True)

        custom_config = {
            "api_base_url": "https://secure.example.com",
            "max_concurrent_requests": 10,
            "query_timeout_seconds": 300,
        }
        config_path.write_text(json.dumps(custom_config), encoding="utf-8")

        manager = ConfigManager(config_path)
        config = manager.load()

        assert config.api_base_url == "https://secure.example.com"

    def test_load_rejects_http_url(self, tmp_path: Path) -> None:
        """Should reject HTTP URLs (insecure)."""
        config_dir = tmp_path / "config"
        config_path = config_dir / "config.json"
        config_path.parent.mkdir(parents=True, exist_ok=True)

        insecure_config = {
            "api_base_url": "http://insecure.example.com",
            "max_concurrent_requests": 10,
            "query_timeout_seconds": 300,
        }
        config_path.write_text(json.dumps(insecure_config), encoding="utf-8")

        manager = ConfigManager(config_path)

        with pytest.raises(ValueError, match="HTTPS required"):
            manager.load()

    def test_load_rejects_missing_scheme(self, tmp_path: Path) -> None:
        """Should reject URLs without scheme."""
        config_dir = tmp_path / "config"
        config_path = config_dir / "config.json"
        config_path.parent.mkdir(parents=True, exist_ok=True)

        invalid_config = {
            "api_base_url": "example.com",
            "max_concurrent_requests": 10,
            "query_timeout_seconds": 300,
        }
        config_path.write_text(json.dumps(invalid_config), encoding="utf-8")

        manager = ConfigManager(config_path)

        with pytest.raises(ValueError):
            manager.load()


class TestConfigSave:
    """Test ConfigManager.save() behavior."""

    def test_save_writes_config(self, tmp_path: Path) -> None:
        """Should write config to file."""
        config_dir = tmp_path / "config"
        config_path = config_dir / "config.json"
        manager = ConfigManager(config_path)

        config = AppConfig(
            config_dir=config_dir,
            api_base_url="https://test.example.com",
            max_concurrent_requests=3,
            query_timeout_seconds=60,
        )
        manager.save(config)

        assert config_path.exists()
        saved_data = json.loads(config_path.read_text(encoding="utf-8"))
        assert saved_data["api_base_url"] == "https://test.example.com"
        assert saved_data["max_concurrent_requests"] == 3
        assert saved_data["query_timeout_seconds"] == 60
        assert "config_dir" not in saved_data  # Should not be saved to file

    def test_save_creates_parent_directory(self, tmp_path: Path) -> None:
        """Should create parent directories if they don't exist."""
        config_dir = tmp_path / "deep" / "nested"
        config_path = config_dir / "config.json"
        manager = ConfigManager(config_path)

        config = AppConfig(
            config_dir=config_dir,
            api_base_url="https://test.example.com",
            max_concurrent_requests=10,
            query_timeout_seconds=300,
        )
        manager.save(config)

        assert config_path.exists()
        assert config_path.parent.exists()

    def test_save_overwrites_existing_config(self, tmp_path: Path) -> None:
        """Should overwrite existing config file."""
        config_dir = tmp_path / "config"
        config_path = config_dir / "config.json"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text('{"old": "data"}', encoding="utf-8")

        manager = ConfigManager(config_path)
        config = AppConfig(
            config_dir=config_dir,
            api_base_url="https://new.example.com",
            max_concurrent_requests=10,
            query_timeout_seconds=300,
        )
        manager.save(config)

        saved_data = json.loads(config_path.read_text(encoding="utf-8"))
        assert "old" not in saved_data
        assert saved_data["api_base_url"] == "https://new.example.com"
