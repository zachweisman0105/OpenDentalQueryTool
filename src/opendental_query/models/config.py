"""Configuration data models."""

from pathlib import Path

from pydantic import BaseModel, Field, field_validator


class OfficeConfig(BaseModel):
    """Configuration for a single OpenDental office database.

    Attributes:
        office_id: Unique identifier for the office (alphanumeric, hyphens, underscores)
        host: MySQL server hostname or IP address
        port: MySQL server port (default: 3306)
        database: MySQL database name
        username: MySQL username for authentication
        description: Optional human-readable description of the office
    """

    office_id: str = Field(
        ..., min_length=1, max_length=50, description="Unique identifier for the office"
    )
    host: str = Field(..., min_length=1, description="MySQL server hostname or IP address")
    port: int = Field(default=3306, ge=1, le=65535, description="MySQL server port")
    database: str = Field(..., min_length=1, description="MySQL database name")
    username: str = Field(..., min_length=1, description="MySQL username for authentication")
    description: str | None = Field(default=None, description="Optional human-readable description")

    @field_validator("office_id")
    @classmethod
    def validate_office_id(cls, v: str) -> str:
        """Validate office_id matches allowed pattern."""
        import re

        from opendental_query.constants import OFFICE_ID_PATTERN

        if not re.match(OFFICE_ID_PATTERN, v):
            raise ValueError(
                "office_id must contain only alphanumeric characters, hyphens, and underscores"
            )
        return v

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "office_id": "main-office",
                    "host": "192.168.1.100",
                    "port": 3306,
                    "database": "opendental",
                    "username": "query_user",
                    "description": "Main office location",
                }
            ]
        }
    }


class AppConfig(BaseModel):
    """Application-wide configuration.

    Attributes:
        config_dir: Directory for configuration files
        api_base_url: OpenDental API base URL (HTTPS only)
        max_concurrent_requests: Maximum concurrent API requests
        vault_file: Filename for encrypted credentials vault
        log_file: Filename for application logs
        audit_file: Filename for audit logs (JSONL format)
        vault_auto_lock_seconds: Auto-lock vault timeout in seconds
        query_timeout_seconds: Default query timeout in seconds
        max_concurrent_queries: Maximum number of concurrent database queries
        offices: Dictionary of office configurations by office_id
    """

    config_dir: Path = Field(..., description="Directory for configuration files")
    api_base_url: str = Field(
        default="https://api.opendental.com", description="OpenDental API base URL (HTTPS required)"
    )
    max_concurrent_requests: int = Field(
        default=10, ge=1, le=50, description="Maximum concurrent API requests"
    )
    vault_file: str = Field(
        default="credentials.vault", description="Filename for encrypted credentials vault"
    )
    log_file: str = Field(default="app.log", description="Filename for application logs")
    audit_file: str = Field(default="audit.jsonl", description="Filename for audit logs")
    vault_auto_lock_seconds: int = Field(
        default=900, ge=60, description="Auto-lock vault timeout in seconds"
    )
    query_timeout_seconds: int = Field(
        default=300, ge=1, description="Default query timeout in seconds"
    )
    max_concurrent_queries: int = Field(
        default=10, ge=1, le=50, description="Maximum concurrent database queries"
    )
    offices: dict[str, OfficeConfig] = Field(
        default_factory=dict, description="Office configurations by office_id"
    )

    @property
    def vault_path(self) -> Path:
        """Get full path to vault file."""
        return self.config_dir / self.vault_file

    @property
    def log_path(self) -> Path:
        """Get full path to log file."""
        return self.config_dir / self.log_file

    @property
    def audit_path(self) -> Path:
        """Get full path to audit log file."""
        return self.config_dir / self.audit_file

    def get_office(self, office_id: str) -> OfficeConfig | None:
        """Get office configuration by ID.

        Args:
            office_id: Office identifier to look up

        Returns:
            OfficeConfig if found, None otherwise
        """
        return self.offices.get(office_id)

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "config_dir": "/home/user/.opendental-query",
                    "vault_file": "credentials.vault",
                    "log_file": "app.log",
                    "audit_file": "audit.jsonl",
                    "vault_auto_lock_seconds": 900,
                    "query_timeout_seconds": 300,
                    "max_concurrent_queries": 10,
                    "offices": {},
                }
            ]
        }
    }
