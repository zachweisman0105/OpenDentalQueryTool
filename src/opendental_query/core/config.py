"""
Configuration manager for loading and saving application settings.

Handles config file I/O, HTTPS validation, and default config creation.
"""

import json
from pathlib import Path
from typing import Any

from opendental_query.models.config import AppConfig


class ConfigManager:
    """Manages application configuration file."""

    def __init__(self, config_path: Path) -> None:
        """
        Initialize ConfigManager.

        Args:
            config_path: Path to config.json file or a directory containing it
        """
        # Accept either a directory (will use config.json) or a file path
        # Check if path looks like a directory (no .json extension) or doesn't exist yet
        if config_path.suffix != ".json":
            self.config_path = config_path / "config.json"
        else:
            self.config_path = config_path
        self._config: AppConfig | None = None
        self._extras: dict[str, Any] = {}

    def load(self) -> AppConfig:
        """
        Load configuration from file, creating default if missing.

        Returns:
            AppConfig: Validated configuration object

        Raises:
            ValueError: If config file contains invalid JSON or HTTP URL
        """
        if not self.config_path.exists():
            return self._create_default_config()

        try:
            config_data = json.loads(self.config_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in config file: {e}") from e

        # Add config_dir if not present (derived from config file path)
        if "config_dir" not in config_data:
            config_data["config_dir"] = str(self.config_path.parent)

        # Validate HTTPS
        api_url = config_data.get("api_base_url", "")
        if api_url.startswith("http://"):
            raise ValueError(f"HTTPS required for API base URL. Found insecure HTTP: {api_url}")
        if not api_url.startswith("https://"):
            raise ValueError(f"Invalid API base URL scheme. Must start with https://: {api_url}")

        try:
            # Separate extras (unknown keys) for persistence
            known_fields = set(AppConfig.model_fields.keys())
            self._extras = {k: v for k, v in config_data.items() if k not in known_fields}
            app_config = AppConfig(**{k: v for k, v in config_data.items() if k in known_fields})
            self._config = app_config
            return app_config
        except Exception as e:
            raise ValueError(f"Invalid configuration: {e}") from e

    def save(self, config: AppConfig | None = None) -> None:
        """
        Save configuration to file.

        Args:
            config: Configuration object to save (uses last loaded if None)
        """
        if config is None:
            if self._config is None:
                # Ensure we have something to save
                self._config = self.load()
            config = self._config
        # Create parent directories if they don't exist
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        # Write config as JSON (exclude config_dir as it's derived from file path)
        config_dict = config.model_dump()
        config_dict.pop("config_dir", None)  # Don't save config_dir
        # Merge extras back for persistence
        merged = {**config_dict, **self._extras}
        self.config_path.write_text(json.dumps(merged, indent=2), encoding="utf-8")

    def _create_default_config(self) -> AppConfig:
        """
        Create default configuration file.

        Returns:
            AppConfig: Default configuration object
        """
        default_config = AppConfig(
            config_dir=self.config_path.parent,
            api_base_url="https://api.opendental.com/api/v1",
            max_concurrent_requests=10,
            query_timeout_seconds=300,
        )

        self.save(default_config)
        return default_config

    # Convenience key-value API expected by tests
    def set(self, dotted_key: str, value: Any) -> None:
        """Set a configuration value using dotted key notation.

        Supported keys:
        - api_base_url (str): API base URL (must be HTTPS)
        - max_concurrent_requests (int): Max concurrent API requests
        - query_timeout_seconds (int): Query timeout in seconds
        - vault_auto_lock_seconds (int): Vault auto-lock timeout
        - vault.auto_lock_minutes (int): converted to vault_auto_lock_seconds
        - query.timeout_seconds (int): maps to query_timeout_seconds
        - export.include_office_column (bool): stored as extra for renderer layer
        """
        # Ensure config loaded
        if self._config is None:
            self._config = self.load()

        # Handle direct field names (from CLI)
        if dotted_key == "api_base_url":
            # Validate HTTPS
            if not isinstance(value, str) or not value.startswith("https://"):
                raise ValueError(f"API base URL must use HTTPS: {value}")
            self._config.api_base_url = value
        elif dotted_key == "max_concurrent_requests":
            self._config.max_concurrent_requests = int(value)
        elif dotted_key == "query_timeout_seconds":
            self._config.query_timeout_seconds = int(value)
        elif dotted_key == "vault_auto_lock_seconds":
            self._config.vault_auto_lock_seconds = int(value)
        # Handle dotted notation for convenience
        elif dotted_key == "vault.auto_lock_minutes":
            # Convert minutes to seconds
            minutes = int(value)
            self._config.vault_auto_lock_seconds = max(60, minutes * 60)
        elif dotted_key == "query.timeout_seconds":
            self._config.query_timeout_seconds = int(value)
        elif dotted_key == "export.include_office_column":
            self._extras[dotted_key] = bool(value)
        else:
            # Store unknown keys in extras
            self._extras[dotted_key] = value

    def get(self, dotted_key: str) -> Any:
        """Get a configuration value by dotted key notation."""
        if self._config is None:
            self._config = self.load()

        # Handle direct field names (from CLI)
        if dotted_key == "api_base_url":
            return self._config.api_base_url
        elif dotted_key == "max_concurrent_requests":
            return self._config.max_concurrent_requests
        elif dotted_key == "query_timeout_seconds":
            return self._config.query_timeout_seconds
        elif dotted_key == "vault_auto_lock_seconds":
            return self._config.vault_auto_lock_seconds
        # Handle dotted notation for convenience
        elif dotted_key == "vault.auto_lock_minutes":
            secs = self._config.vault_auto_lock_seconds
            return int(secs // 60)
        elif dotted_key == "query.timeout_seconds":
            return self._config.query_timeout_seconds
        elif dotted_key == "export.include_office_column":
            return self._extras.get(dotted_key, False)
        else:
            return self._extras.get(dotted_key)

    def to_dict(self) -> dict[str, Any]:
        """Get all configuration as a dictionary."""
        if self._config is None:
            self._config = self.load()

        result = self._config.model_dump()
        result.pop("config_dir", None)  # Don't include config_dir
        result.update(self._extras)
        return result

    def reset_to_defaults(self) -> None:
        """Reset configuration to default values."""
        self._config = AppConfig(
            config_dir=self.config_path.parent,
            api_base_url="https://api.opendental.com/api/v1",
            max_concurrent_requests=10,
            query_timeout_seconds=300,
        )
        self._extras.clear()

    def reset_key(self, key: str) -> None:
        """Reset a specific key to its default value."""
        if self._config is None:
            self._config = self.load()

        defaults = {
            "api_base_url": "https://api.opendental.com/api/v1",
            "max_concurrent_requests": 10,
            "query_timeout_seconds": 300,
            "vault_auto_lock_seconds": 1800,  # 30 minutes
        }

        if key in defaults:
            setattr(self._config, key, defaults[key])
        elif key in self._extras:
            del self._extras[key]
