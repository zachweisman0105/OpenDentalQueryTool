"""Unit tests for Pydantic data models."""

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from pydantic import ValidationError

from opendental_query.models.audit import AuditEntry
from opendental_query.models.config import AppConfig, OfficeConfig
from opendental_query.models.query import QueryRequest, QueryResult
from opendental_query.models.vault import VaultCredentials, VaultMetadata


class TestOfficeConfig:
    """Tests for OfficeConfig model."""

    def test_valid_office_config(self, sample_office_config: OfficeConfig) -> None:
        """Test creation of valid office configuration."""
        assert sample_office_config.office_id == "test-office"
        assert sample_office_config.host == "localhost"
        assert sample_office_config.port == 3306
        assert sample_office_config.database == "test_opendental"
        assert sample_office_config.username == "test_user"

    def test_office_id_validation(self) -> None:
        """Test office_id validation rejects invalid characters."""
        with pytest.raises(ValidationError):
            OfficeConfig(
                office_id="invalid@office!",  # Invalid characters
                host="localhost",
                database="test",
                username="user",
            )

    def test_default_port(self) -> None:
        """Test default MySQL port is 3306."""
        config = OfficeConfig(office_id="test", host="localhost", database="test", username="user")
        assert config.port == 3306

    def test_port_validation(self) -> None:
        """Test port validation rejects invalid values."""
        with pytest.raises(ValidationError):
            OfficeConfig(
                office_id="test",
                host="localhost",
                port=70000,  # Invalid port number
                database="test",
                username="user",
            )

    def test_serialization(self, sample_office_config: OfficeConfig) -> None:
        """Test JSON serialization."""
        data = sample_office_config.model_dump()
        assert data["office_id"] == "test-office"

        # Test round-trip
        reconstructed = OfficeConfig(**data)
        assert reconstructed == sample_office_config


class TestAppConfig:
    """Tests for AppConfig model."""

    def test_valid_app_config(self, sample_app_config: AppConfig) -> None:
        """Test creation of valid application configuration."""
        assert sample_app_config.vault_file == "test.vault"
        assert sample_app_config.log_file == "test.log"
        assert sample_app_config.query_timeout_seconds == 60

    def test_path_properties(self, sample_app_config: AppConfig) -> None:
        """Test path property accessors."""
        assert sample_app_config.vault_path == sample_app_config.config_dir / "test.vault"
        assert sample_app_config.log_path == sample_app_config.config_dir / "test.log"
        assert sample_app_config.audit_path == sample_app_config.config_dir / "test_audit.jsonl"

    def test_get_office(
        self, sample_app_config: AppConfig, sample_office_config: OfficeConfig
    ) -> None:
        """Test get_office method."""
        sample_app_config.offices["test-office"] = sample_office_config

        assert sample_app_config.get_office("test-office") == sample_office_config
        assert sample_app_config.get_office("nonexistent") is None

    def test_defaults(self, tmp_config_dir: Path) -> None:
        """Test default values."""
        config = AppConfig(config_dir=tmp_config_dir)

        assert config.vault_file == "credentials.vault"
        assert config.log_file == "app.log"
        assert config.audit_file == "audit.jsonl"
        assert config.vault_auto_lock_seconds == 900
        assert config.query_timeout_seconds == 300
        assert config.max_concurrent_queries == 10


class TestVaultCredentials:
    """Tests for VaultCredentials model."""

    def test_valid_credentials(self) -> None:
        """Test creation of valid credentials."""
        creds = VaultCredentials(office_id="test-office", password="secure_password_123")
        assert creds.office_id == "test-office"
        assert creds.password == "secure_password_123"

    def test_office_id_validation(self) -> None:
        """Test office_id validation."""
        with pytest.raises(ValidationError):
            VaultCredentials(office_id="invalid!@#", password="password")


class TestVaultMetadata:
    """Tests for VaultMetadata model."""

    def test_default_creation(self) -> None:
        """Test creation with defaults."""
        metadata = VaultMetadata(password_hash="$argon2id$test")

        assert metadata.version == "1.0"
        assert metadata.failed_attempts == 0
        assert metadata.locked_until is None
        assert metadata.last_unlocked is None

    def test_is_locked(self) -> None:
        """Test is_locked method."""
        metadata = VaultMetadata(password_hash="test")

        # Not locked initially
        assert not metadata.is_locked()

        # Lock for 1 hour
        metadata.locked_until = datetime.now(UTC) + timedelta(hours=1)
        assert metadata.is_locked()

        # Expired lock
        metadata.locked_until = datetime.now(UTC) - timedelta(hours=1)
        assert not metadata.is_locked()

    def test_increment_failed_attempts(self) -> None:
        """Test incrementing failed attempts."""
        metadata = VaultMetadata(password_hash="test")

        assert metadata.failed_attempts == 0
        metadata.increment_failed_attempts()
        assert metadata.failed_attempts == 1
        metadata.increment_failed_attempts()
        assert metadata.failed_attempts == 2

    def test_reset_failed_attempts(self) -> None:
        """Test resetting failed attempts."""
        metadata = VaultMetadata(password_hash="test")
        metadata.failed_attempts = 5
        metadata.locked_until = datetime.now(UTC) + timedelta(hours=1)

        metadata.reset_failed_attempts()

        assert metadata.failed_attempts == 0
        assert metadata.locked_until is None
        assert metadata.last_unlocked is not None

    def test_lock_vault(self) -> None:
        """Test locking vault."""
        metadata = VaultMetadata(password_hash="test")

        metadata.lock_vault(3600)  # 1 hour

        assert metadata.locked_until is not None
        assert metadata.is_locked()


class TestQueryRequest:
    """Tests for QueryRequest model."""

    def test_valid_request(self) -> None:
        """Test creation of valid query request."""
        request = QueryRequest(
            query="SELECT * FROM patient LIMIT 10",
            office_ids=["office1", "office2"],
            timeout_seconds=60,
            add_order_by=True,
        )

        assert request.query == "SELECT * FROM patient LIMIT 10"
        assert len(request.office_ids) == 2
        assert request.timeout_seconds == 60
        assert request.add_order_by is True

    def test_defaults(self) -> None:
        """Test default values."""
        request = QueryRequest(query="SELECT 1")

        assert request.office_ids == []
        assert request.timeout_seconds is None
        assert request.add_order_by is True


class TestQueryResult:
    """Tests for QueryResult model."""

    def test_successful_result(self) -> None:
        """Test successful query result."""
        result = QueryResult(
            office_id="test-office",
            success=True,
            rows=[{"id": 1, "name": "Test"}],
            row_count=1,
            columns=["id", "name"],
            execution_time_ms=23.5,
        )

        assert result.success
        assert result.has_data()
        assert result.error is None
        assert "test-office: 1 rows" in result.get_summary()

    def test_failed_result(self) -> None:
        """Test failed query result."""
        result = QueryResult(office_id="test-office", success=False, error="Connection refused")

        assert not result.success
        assert not result.has_data()
        assert "ERROR" in result.get_summary()


class TestAuditEntry:
    """Tests for AuditEntry model."""

    def test_valid_entry(self) -> None:
        """Test creation of valid audit entry."""
        entry = AuditEntry(
            event_type="query_execute",
            user="testuser",
            office_id="test-office",
            success=True,
            details={"query": "SELECT 1"},
        )

        assert entry.event_type == "query_execute"
        assert entry.user == "testuser"
        assert entry.success

    def test_to_jsonl(self) -> None:
        """Test JSONL serialization."""
        entry = AuditEntry(event_type="test", user="testuser", success=True)

        jsonl = entry.to_jsonl()

        # Should be valid JSON with newline
        assert jsonl.endswith("\n")
        data = json.loads(jsonl.strip())
        assert data["event_type"] == "test"
        assert data["user"] == "testuser"

    def test_from_jsonl(self) -> None:
        """Test JSONL deserialization."""
        entry = AuditEntry(event_type="test", user="testuser", success=True)

        jsonl = entry.to_jsonl()
        reconstructed = AuditEntry.from_jsonl(jsonl)

        assert reconstructed.event_type == entry.event_type
        assert reconstructed.user == entry.user
        assert reconstructed.success == entry.success
