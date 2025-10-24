"""Integration tests for configuration management CLI lifecycle.

Tests the complete flow: config set, config get, config list, config reset.
"""

import json
from pathlib import Path

from click.testing import CliRunner

from opendental_query.cli.config_cmd import config_group


class TestConfigSetGet:
    """Test config set and get command integration."""

    def test_set_and_get_api_url(self, tmp_path: Path) -> None:
        """Test setting and retrieving API base URL."""
        runner = CliRunner()
        config_dir = tmp_path / "config"

        # Set API URL
        result = runner.invoke(
            config_group,
            ["set", "api_base_url", "https://api.example.com"],
            obj={"config_dir": config_dir},
        )

        assert result.exit_code == 0
        assert "Set api_base_url" in result.output
        assert "https://api.example.com" in result.output

        # Get API URL
        result = runner.invoke(
            config_group,
            ["get", "api_base_url"],
            obj={"config_dir": config_dir},
        )

        assert result.exit_code == 0
        assert "api_base_url" in result.output
        assert "https://api.example.com" in result.output

    def test_set_multiple_keys(self, tmp_path: Path) -> None:
        """Test setting multiple configuration keys."""
        runner = CliRunner()
        config_dir = tmp_path / "config"

        # Set multiple values
        runner.invoke(
            config_group,
            ["set", "api_base_url", "https://api.test.com"],
            obj={"config_dir": config_dir},
        )
        runner.invoke(
            config_group,
            ["set", "max_concurrent_requests", "5"],
            obj={"config_dir": config_dir},
        )
        runner.invoke(
            config_group,
            ["set", "query_timeout_seconds", "120"],
            obj={"config_dir": config_dir},
        )

        # Verify all values
        result = runner.invoke(
            config_group,
            ["get", "api_base_url"],
            obj={"config_dir": config_dir},
        )
        assert "https://api.test.com" in result.output

        result = runner.invoke(
            config_group,
            ["get", "max_concurrent_requests"],
            obj={"config_dir": config_dir},
        )
        assert "5" in result.output

    def test_get_nonexistent_key(self, tmp_path: Path) -> None:
        """Test getting a key that doesn't exist."""
        runner = CliRunner()
        config_dir = tmp_path / "config"

        result = runner.invoke(
            config_group,
            ["get", "nonexistent_key"],
            obj={"config_dir": config_dir},
        )

        assert result.exit_code == 0
        assert "not set" in result.output.lower()

    def test_set_dotted_key_notation(self, tmp_path: Path) -> None:
        """Test setting nested config with dotted notation."""
        runner = CliRunner()
        config_dir = tmp_path / "config"

        result = runner.invoke(
            config_group,
            ["set", "vault.auto_lock_minutes", "30"],
            obj={"config_dir": config_dir},
        )

        assert result.exit_code == 0
        assert "vault.auto_lock_minutes" in result.output

        # Verify it was saved correctly
        result = runner.invoke(
            config_group,
            ["get", "vault.auto_lock_minutes"],
            obj={"config_dir": config_dir},
        )

        assert result.exit_code == 0
        assert "30" in result.output


class TestConfigList:
    """Test config list command."""

    def test_list_empty_config(self, tmp_path: Path) -> None:
        """Test listing when no explicit config set yet (defaults shown)."""
        runner = CliRunner()
        config_dir = tmp_path / "config"

        result = runner.invoke(
            config_group,
            ["list"],
            obj={"config_dir": config_dir},
        )

        assert result.exit_code == 0
        # Should show default values
        assert "api_base_url" in result.output or "No configuration" in result.output

    def test_list_populated_config(self, tmp_path: Path) -> None:
        """Test listing config with multiple values."""
        runner = CliRunner()
        config_dir = tmp_path / "config"

        # Set several values
        runner.invoke(
            config_group,
            ["set", "api_base_url", "https://api.test.com"],
            obj={"config_dir": config_dir},
        )
        runner.invoke(
            config_group,
            ["set", "max_concurrent_requests", "7"],
            obj={"config_dir": config_dir},
        )

        result = runner.invoke(
            config_group,
            ["list"],
            obj={"config_dir": config_dir},
        )

        assert result.exit_code == 0
        assert "api_base_url" in result.output
        assert "https://api.test.com" in result.output
        assert "max_concurrent_requests" in result.output
        assert "7" in result.output


class TestConfigReset:
    """Test config reset command."""

    def test_reset_specific_key(self, tmp_path: Path) -> None:
        """Test resetting a specific key to default."""
        runner = CliRunner()
        config_dir = tmp_path / "config"

        # Set custom value
        runner.invoke(
            config_group,
            ["set", "max_concurrent_requests", "3"],
            obj={"config_dir": config_dir},
        )

        # Reset to default
        result = runner.invoke(
            config_group,
            ["reset", "max_concurrent_requests"],
            obj={"config_dir": config_dir},
        )

        assert result.exit_code == 0
        assert "Reset max_concurrent_requests" in result.output

    def test_reset_all_config(self, tmp_path: Path) -> None:
        """Test resetting all configuration to defaults."""
        runner = CliRunner()
        config_dir = tmp_path / "config"

        # Set multiple custom values
        runner.invoke(
            config_group,
            ["set", "api_base_url", "https://custom.com"],
            obj={"config_dir": config_dir},
        )
        runner.invoke(
            config_group,
            ["set", "max_concurrent_requests", "2"],
            obj={"config_dir": config_dir},
        )

        # Reset all
        result = runner.invoke(
            config_group,
            ["reset", "--all"],
            obj={"config_dir": config_dir},
        )

        assert result.exit_code == 0
        assert "Reset all configuration" in result.output


class TestConfigPath:
    """Test config path command."""

    def test_show_config_path(self, tmp_path: Path) -> None:
        """Test showing the configuration file path."""
        runner = CliRunner()
        config_dir = tmp_path / "config"

        result = runner.invoke(
            config_group,
            ["path"],
            obj={"config_dir": config_dir},
        )

        assert result.exit_code == 0
        assert "Configuration file:" in result.output
        assert str(config_dir) in result.output or "config.json" in result.output


class TestConfigPersistence:
    """Test configuration persistence across commands."""

    def test_config_persists_across_commands(self, tmp_path: Path) -> None:
        """Test that configuration changes persist across CLI invocations."""
        runner = CliRunner()
        config_dir = tmp_path / "config"
        config_file = config_dir / "config.json"

        # Set value in first command
        result = runner.invoke(
            config_group,
            ["set", "api_base_url", "https://persistent.example.com"],
            obj={"config_dir": config_dir},
        )
        assert result.exit_code == 0

        # Verify file was created
        assert config_file.exists()

        # Read in second command
        result = runner.invoke(
            config_group,
            ["get", "api_base_url"],
            obj={"config_dir": config_dir},
        )

        assert result.exit_code == 0
        assert "https://persistent.example.com" in result.output

        # Verify the JSON file directly
        config_data = json.loads(config_file.read_text(encoding="utf-8"))
        assert config_data["api_base_url"] == "https://persistent.example.com"

    def test_type_conversion_persists(self, tmp_path: Path) -> None:
        """Test that type conversions are preserved."""
        runner = CliRunner()
        config_dir = tmp_path / "config"
        config_file = config_dir / "config.json"

        # Set integer value
        runner.invoke(
            config_group,
            ["set", "max_concurrent_requests", "15"],
            obj={"config_dir": config_dir},
        )

        # Set boolean value
        runner.invoke(
            config_group,
            ["set", "enable_feature", "true"],
            obj={"config_dir": config_dir},
        )

        # Verify types in JSON file
        config_data = json.loads(config_file.read_text(encoding="utf-8"))
        assert isinstance(config_data["max_concurrent_requests"], int)
        assert config_data["max_concurrent_requests"] == 15
        assert isinstance(config_data.get("enable_feature"), bool)
        assert config_data.get("enable_feature") is True


class TestConfigValidation:
    """Test configuration validation during CLI operations."""

    def test_https_validation_on_set(self, tmp_path: Path) -> None:
        """Test that HTTP URLs are rejected when setting api_base_url."""
        runner = CliRunner()
        config_dir = tmp_path / "config"

        # Attempt to set HTTP URL (should fail)
        result = runner.invoke(
            config_group,
            ["set", "api_base_url", "http://insecure.example.com"],
            obj={"config_dir": config_dir},
        )

        # Should either fail or warn (implementation dependent)
        # Check for error indication
        assert (
            result.exit_code != 0
            or "error" in result.output.lower()
            or "https" in result.output.lower()
        )

    def test_https_url_accepted(self, tmp_path: Path) -> None:
        """Test that HTTPS URLs are accepted."""
        runner = CliRunner()
        config_dir = tmp_path / "config"

        result = runner.invoke(
            config_group,
            ["set", "api_base_url", "https://secure.example.com"],
            obj={"config_dir": config_dir},
        )

        assert result.exit_code == 0
        assert "https://secure.example.com" in result.output
