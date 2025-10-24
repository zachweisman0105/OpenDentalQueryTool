"""Unit tests for audit logger."""

import hashlib
import json
import re
from pathlib import Path

from opendental_query.utils.audit_logger import AuditLogger


class TestAuditLoggerInit:
    """Tests for AuditLogger initialization."""

    def test_create_with_existing_file(self, sample_audit_file: Path) -> None:
        """Test creating logger with existing audit file."""
        logger = AuditLogger(sample_audit_file)

        assert logger.audit_file == sample_audit_file
        assert sample_audit_file.exists()

    def test_create_with_new_file(self, tmp_config_dir: Path) -> None:
        """Test creating logger creates new audit file."""
        audit_file = tmp_config_dir / "new_audit.jsonl"

        assert not audit_file.exists()

        logger = AuditLogger(audit_file)

        assert audit_file.exists()
        assert logger.audit_file == audit_file

    def test_create_with_nested_path(self, tmp_config_dir: Path) -> None:
        """Test creating logger creates parent directories."""
        audit_file = tmp_config_dir / "logs" / "subdir" / "audit.jsonl"

        assert not audit_file.parent.exists()

        logger = AuditLogger(audit_file)

        assert audit_file.exists()
        assert audit_file.parent.exists()


class TestAuditLoggerLog:
    """Tests for AuditLogger.log method."""

    def test_log_basic_event(self, sample_audit_file: Path) -> None:
        """Test logging a basic event."""
        logger = AuditLogger(sample_audit_file)

        logger.log("test_event", success=True)

        # Read and verify
        lines = sample_audit_file.read_text().strip().split("\n")
        assert len(lines) == 1

        entry = json.loads(lines[0])
        assert entry["event_type"] == "test_event"
        assert entry["success"] is True
        assert "ip_address" in entry
        assert entry["hostname"]
        assert entry["session_id"]

    def test_log_with_office_id(self, sample_audit_file: Path) -> None:
        """Test logging event with office_id."""
        logger = AuditLogger(sample_audit_file)

        logger.log("test_event", success=True, office_id="test-office")

        lines = sample_audit_file.read_text().strip().split("\n")
        entry = json.loads(lines[0])
        token = entry["office_id"]
        assert token != "test-office"
        assert re.fullmatch(r"[0-9a-f]{64}", token)

    def test_log_with_details(self, sample_audit_file: Path) -> None:
        """Test logging event with details."""
        logger = AuditLogger(sample_audit_file)

        details = {"query": "SELECT 1", "row_count": 1}
        logger.log("test_event", success=True, details=details)

        lines = sample_audit_file.read_text().strip().split("\n")
        entry = json.loads(lines[0])
        assert entry["details"] == details

    def test_log_with_error(self, sample_audit_file: Path) -> None:
        """Test logging failed event with error."""
        logger = AuditLogger(sample_audit_file)

        logger.log("test_event", success=False, error="Connection refused")

        lines = sample_audit_file.read_text().strip().split("\n")
        entry = json.loads(lines[0])
        assert entry["success"] is False
        assert entry["error"] == "Connection refused"

    def test_log_multiple_events(self, sample_audit_file: Path) -> None:
        """Test logging multiple events."""
        logger = AuditLogger(sample_audit_file)

        logger.log("event1", success=True)
        logger.log("event2", success=True)
        logger.log("event3", success=False, error="Test error")

        lines = sample_audit_file.read_text().strip().split("\n")
        assert len(lines) == 3

        # Verify each line is valid JSON
        for line in lines:
            entry = json.loads(line)
            assert "event_type" in entry
            assert "success" in entry


class TestAuditLoggerVaultMethods:
    """Tests for vault-specific audit methods."""

    def test_log_vault_unlock_success(self, sample_audit_file: Path) -> None:
        """Test logging successful vault unlock."""
        logger = AuditLogger(sample_audit_file)

        logger.log_vault_unlock(success=True)

        lines = sample_audit_file.read_text().strip().split("\n")
        entry = json.loads(lines[0])

        assert entry["event_type"] == "vault_unlock"
        assert entry["success"] is True
        assert entry["error"] is None

    def test_log_vault_unlock_failure(self, sample_audit_file: Path) -> None:
        """Test logging failed vault unlock."""
        logger = AuditLogger(sample_audit_file)

        logger.log_vault_unlock(success=False, error="Invalid password")

        lines = sample_audit_file.read_text().strip().split("\n")
        entry = json.loads(lines[0])

        assert entry["event_type"] == "vault_unlock"
        assert entry["success"] is False
        assert entry["error"] == "Invalid password"

    def test_log_vault_lock(self, sample_audit_file: Path) -> None:
        """Test logging vault lock."""
        logger = AuditLogger(sample_audit_file)

        logger.log_vault_lock()

        lines = sample_audit_file.read_text().strip().split("\n")
        entry = json.loads(lines[0])

        assert entry["event_type"] == "vault_lock"
        assert entry["success"] is True


class TestAuditLoggerQueryMethods:
    """Tests for query-specific audit methods."""

    def test_log_query_execute_success(self, sample_audit_file: Path) -> None:
        """Test logging successful query execution."""
        logger = AuditLogger(sample_audit_file)

        query = "SELECT * FROM patient LIMIT 10"

        logger.log_query_execute(
            office_id="test-office",
            query=query,
            success=True,
            row_count=10,
            execution_time_ms=45.3,
        )

        lines = sample_audit_file.read_text().strip().split("\n")
        entry = json.loads(lines[0])

        assert entry["event_type"] == "query_execute"
        assert entry["office_id"] != "test-office"
        assert re.fullmatch(r"[0-9a-f]{64}", entry["office_id"])
        assert entry["success"] is True
        assert entry["details"]["query_hash"] == hashlib.sha256(query.encode("utf-8")).hexdigest()
        assert entry["details"]["row_count"] == 10
        assert entry["details"]["execution_time_ms"] == 45.3

    def test_log_query_execute_failure(self, sample_audit_file: Path) -> None:
        """Test logging failed query execution."""
        logger = AuditLogger(sample_audit_file)

        query = "SELECT * FROM invalid_table"

        logger.log_query_execute(
            office_id="test-office",
            query=query,
            success=False,
            error="Table 'invalid_table' doesn't exist",
        )

        lines = sample_audit_file.read_text().strip().split("\n")
        entry = json.loads(lines[0])

        assert entry["event_type"] == "query_execute"
        assert entry["success"] is False
        assert entry["office_id"] != "test-office"
        assert re.fullmatch(r"[0-9a-f]{64}", entry["office_id"])
        assert entry["error"] == "Table 'invalid_table' doesn't exist"
        assert (
            entry["details"]["query_hash"] == hashlib.sha256(query.encode("utf-8")).hexdigest()
        )


class TestAuditLoggerConfigMethods:
    """Tests for config-specific audit methods."""

    def test_log_config_change(self, sample_audit_file: Path) -> None:
        """Test logging configuration change."""
        logger = AuditLogger(sample_audit_file)

        logger.log_config_change(
            action="add_office", details={"office_id": "new-office", "host": "192.168.1.100"}
        )

        lines = sample_audit_file.read_text().strip().split("\n")
        entry = json.loads(lines[0])

        assert entry["event_type"] == "config_change"
        assert entry["success"] is True
        assert entry["details"]["action"] == "add_office"
        assert entry["details"]["host"] == "192.168.1.100"
        assert "office_token" in entry["details"]
        assert re.fullmatch(r"[0-9a-f]{64}", entry["details"]["office_token"])


class TestAuditLoggerThreadSafety:
    """Tests for thread-safe operations."""

    def test_concurrent_writes(self, sample_audit_file: Path) -> None:
        """Test that concurrent writes are thread-safe."""
        import threading

        logger = AuditLogger(sample_audit_file)

        def write_event(event_id: int) -> None:
            logger.log(f"event_{event_id}", success=True)

        # Create multiple threads writing simultaneously
        threads = [threading.Thread(target=write_event, args=(i,)) for i in range(10)]

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        # Verify all events were written
        lines = sample_audit_file.read_text().strip().split("\n")
        assert len(lines) == 10

        # Verify each line is valid JSON
        for line in lines:
            entry = json.loads(line)
            assert entry["event_type"].startswith("event_")


class TestAuditLoggerAdditionalMethods:
    """Tests for additional audit logger convenience methods."""

    def test_log_query_execution(self, sample_audit_file: Path) -> None:
        """Test logging multi-office query execution."""
        logger = AuditLogger(sample_audit_file)

        query = "SELECT * FROM patient"

        logger.log_query_execution(
            query=query,
            office_ids=["main", "branch"],
            success_count=2,
            failed_count=0,
            row_count=150,
        )

        lines = sample_audit_file.read_text().strip().split("\n")
        entry = json.loads(lines[0])

        assert entry["event_type"] == "query_execution"
        assert entry["success"] is True
        assert entry["details"]["success_count"] == 2
        assert entry["details"]["failed_count"] == 0
        assert entry["details"]["row_count"] == 150
        assert entry["details"]["query_hash"] == hashlib.sha256(query.encode("utf-8")).hexdigest()
        assert "office_tokens" in entry["details"]
        assert len(entry["details"]["office_tokens"]) == 2
        for token in entry["details"]["office_tokens"]:
            assert re.fullmatch(r"[0-9a-f]{64}", token)
        assert "query" not in entry["details"]

    def test_log_csv_export(self, sample_audit_file: Path) -> None:
        """Test logging CSV export with file hash."""
        logger = AuditLogger(sample_audit_file)

        # Create a test CSV file
        csv_file = sample_audit_file.parent / "test.csv"
        csv_file.write_text("id,name\n1,test\n")

        logger.log_csv_export(
            filepath=str(csv_file),
            row_count=1,
            office_count=1,
        )

        lines = sample_audit_file.read_text().strip().split("\n")
        entry = json.loads(lines[0])

        assert entry["event_type"] == "csv_export"
        assert entry["success"] is True
        details = entry["details"]
        assert details["row_count"] == 1
        assert details["office_count"] == 1
        assert "sha256" in details
        assert details["sha256"] != "unknown"
        assert "filepath" not in details
        assert details["filename"] == "test.csv"
        assert re.fullmatch(r"[0-9a-f]{64}", details["path_hash"])

    def test_log_csv_export_missing_file(self, sample_audit_file: Path) -> None:
        """Test CSV export logging handles missing file gracefully."""
        logger = AuditLogger(sample_audit_file)

        logger.log_csv_export(
            filepath="/nonexistent/file.csv",
            row_count=0,
            office_count=0,
        )

        lines = sample_audit_file.read_text().strip().split("\n")
        entry = json.loads(lines[0])

        assert entry["event_type"] == "csv_export"
        details = entry["details"]
        assert details["sha256"] == "unknown"
        assert "filepath" not in details
        assert details["filename"] == "file.csv"
        assert re.fullmatch(r"[0-9a-f]{64}", details["path_hash"])

    def test_log_update_checked_success(self, sample_audit_file: Path) -> None:
        """Test logging successful update check."""
        logger = AuditLogger(sample_audit_file)

        logger.log_update_checked(
            current_version="1.0.0",
            latest_version="1.1.0",
            update_available=True,
            error=None,
        )

        lines = sample_audit_file.read_text().strip().split("\n")
        entry = json.loads(lines[0])

        assert entry["event_type"] == "UPDATE_CHECKED"
        assert entry["success"] is True
        assert entry["details"]["current_version"] == "1.0.0"
        assert entry["details"]["latest_version"] == "1.1.0"
        assert entry["details"]["update_available"] is True

    def test_log_update_checked_failure(self, sample_audit_file: Path) -> None:
        """Test logging failed update check."""
        logger = AuditLogger(sample_audit_file)

        logger.log_update_checked(
            current_version="1.0.0",
            latest_version=None,
            update_available=False,
            error="Network timeout",
        )

        lines = sample_audit_file.read_text().strip().split("\n")
        entry = json.loads(lines[0])

        assert entry["event_type"] == "UPDATE_CHECKED"
        assert entry["success"] is False
        assert entry["error"] == "Network timeout"
