"""Vault data models for encrypted credential storage."""

from datetime import UTC, datetime, timedelta
from typing import Any

from pydantic import BaseModel, Field, field_validator


class VaultCredentials(BaseModel):
    """Decrypted credentials for database connections.

    Attributes:
        office_id: Office identifier this credential belongs to
        password: Plaintext database password
    """

    office_id: str = Field(..., min_length=1, max_length=50, description="Office identifier")
    password: str = Field(..., min_length=1, description="Database password")

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
            "examples": [{"office_id": "main-office", "password": "secure_password_123"}]
        }
    }


class VaultMetadata(BaseModel):
    """Metadata for the encrypted vault.

    Attributes:
        created_at: Timestamp when vault was created
        modified_at: Timestamp when vault was last modified
        version: Vault format version
        password_hash: Argon2id hash of the master password
        failed_attempts: Count of failed authentication attempts
        locked_until: Optional timestamp when vault is locked until
        last_unlocked: Optional timestamp of last successful unlock
    """

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="Vault creation timestamp"
    )
    modified_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Last modification timestamp",
    )
    version: str = Field(default="1.0", description="Vault format version")
    password_hash: str = Field(..., min_length=1, description="Argon2id hash of master password")
    failed_attempts: int = Field(default=0, ge=0, description="Failed authentication attempt count")
    locked_until: datetime | None = Field(
        default=None, description="Timestamp when vault is locked until"
    )
    last_unlocked: datetime | None = Field(
        default=None, description="Last successful unlock timestamp"
    )

    def is_locked(self) -> bool:
        """Check if vault is currently locked due to failed attempts.

        Returns:
            True if vault is locked, False otherwise
        """
        if self.locked_until is None:
            return False
        return datetime.now(UTC) < self.locked_until

    def increment_failed_attempts(self) -> None:
        """Increment failed authentication attempt count."""
        self.failed_attempts += 1
        self.modified_at = datetime.now(UTC)

    def reset_failed_attempts(self) -> None:
        """Reset failed authentication attempts to zero."""
        self.failed_attempts = 0
        self.locked_until = None
        self.last_unlocked = datetime.now(UTC)
        self.modified_at = datetime.now(UTC)

    def lock_vault(self, duration_seconds: int) -> None:
        """Lock vault for specified duration.

        Args:
            duration_seconds: Number of seconds to lock vault
        """
        self.locked_until = datetime.now(UTC) + timedelta(seconds=duration_seconds)
        self.modified_at = datetime.now(UTC)

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "created_at": "2025-10-21T10:00:00Z",
                    "modified_at": "2025-10-21T10:30:00Z",
                    "version": "1.0",
                    "password_hash": "$argon2id$v=19$m=65536,t=3,p=4$...",
                    "failed_attempts": 0,
                    "locked_until": None,
                    "last_unlocked": "2025-10-21T10:30:00Z",
                }
            ]
        }
    }


class VaultOfficeEntry(BaseModel):
    """Stored credential entry for a single office."""

    customer_key: str = Field(..., min_length=1, description="OpenDental CustomerKey")
    added_at: datetime | None = Field(
        default=None, description="Timestamp when the credential was added"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"customer_key": "OD123456789", "added_at": "2025-10-21T10:30:00Z"},
            ]
        }
    }


class VaultData(BaseModel):
    """Structured representation of decrypted vault contents."""

    developer_key: str = Field(default="", description="Global OpenDental DeveloperKey")
    offices: dict[str, VaultOfficeEntry] = Field(
        default_factory=dict, description="Mapping of office_id to credential entries"
    )
    metadata: dict[str, Any] = Field(default_factory=dict, description="Vault metadata block")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "VaultData":
        """Create VaultData from raw decrypted dictionary structure."""
        offices_raw = data.get("offices", {})
        offices = {
            office_id: VaultOfficeEntry(**office_data)
            for office_id, office_data in offices_raw.items()
        }
        developer_key = data.get("developer_key", "")
        metadata = data.get("metadata", {})
        return cls(developer_key=developer_key, offices=offices, metadata=metadata)

    def to_dict(self) -> dict[str, Any]:
        """Convert VaultData back to a serializable dictionary."""
        return {
            "developer_key": self.developer_key,
            "offices": {
                office_id: entry.model_dump(mode="json") for office_id, entry in self.offices.items()
            },
            "metadata": self.metadata,
        }
