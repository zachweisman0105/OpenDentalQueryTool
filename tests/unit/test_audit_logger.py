"""Unit tests for audit logging functionality."""

import json
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path

from opendental_query.utils.audit_logger import AuditLogger


class TestAuditLoggerJSONLFormat:
    """Test JSONL format compliance for all audit event types."""

    def test_app_start_event(self, tmp_path: Path) -> None:
        """Test APP_START event generates valid JSONL."""
        audit_file = tmp_path / "audit.jsonl"
        logger = AuditLogger(audit_file)
        logger.log("APP_START", success=True, details={"version": "1.0.0"})

        lines = audit_file.read_text().strip().split("\n")
        assert len(lines) == 1
        entry = json.loads(lines[0])
        assert entry["event_type"] == "APP_START"
        assert entry["success"] is True
        assert entry["details"]["version"] == "1.0.0"

    def test_vault_unlock_success(self, tmp_path: Path) -> None:
        """Test successful vault_unlock event."""
        audit_file = tmp_path / "audit.jsonl"
        logger = AuditLogger(audit_file)
        logger.log_vault_unlock(success=True)

        entry = json.loads(audit_file.read_text().strip())
        assert entry["event_type"] == "vault_unlock"
        assert entry["success"] is True

    def test_vault_unlock_failure(self, tmp_path: Path) -> None:
        """Test failed vault_unlock event with error."""
        audit_file = tmp_path / "audit.jsonl"
        logger = AuditLogger(audit_file)
        logger.log_vault_unlock(success=False, error="Invalid password")

        entry = json.loads(audit_file.read_text().strip())
        assert entry["event_type"] == "vault_unlock"
        assert entry["success"] is False
        assert entry["error"] == "Invalid password"

    def test_query_executed_event(self, tmp_path: Path) -> None:
        """Test QUERY_EXECUTED event with SHA256 hash."""
        audit_file = tmp_path / "audit.jsonl"
        logger = AuditLogger(audit_file)
        logger.log_query_executed(sql="SELECT * FROM patient", offices=["Office A"])

        entry = json.loads(audit_file.read_text().strip())
        assert entry["event_type"] == "QUERY_EXECUTED"
        assert entry["success"] is True
        assert "query_hash" in entry["details"]
        assert len(entry["details"]["query_hash"]) == 64  # SHA256
        assert entry["details"]["office_count"] == 1
        assert "office_tokens" in entry["details"]
        assert len(entry["details"]["office_tokens"]) == 1
        assert re.fullmatch(r"[0-9a-f]{64}", entry["details"]["office_tokens"][0])

    def test_csv_exported_event(self, tmp_path: Path) -> None:
        """Test EXPORT_CREATED event."""
        audit_file = tmp_path / "audit.jsonl"
        logger = AuditLogger(audit_file)
        export_path = tmp_path / "export.csv"
        logger.log_export_created(export_path=export_path, row_count=150)

        entry = json.loads(audit_file.read_text().strip())
        assert entry["event_type"] == "EXPORT_CREATED"
        assert entry["success"] is True
        details = entry["details"]
        assert details["row_count"] == 150
        assert "filepath" not in details
        assert details["filename"] == "export.csv"
        assert re.fullmatch(r"[0-9a-f]{64}", details["path_hash"])

    def test_network_error_event(self, tmp_path: Path) -> None:
        """Test NETWORK_ERROR event."""
        audit_file = tmp_path / "audit.jsonl"
        logger = AuditLogger(audit_file)
        logger.log_network_error(operation="query_execute", error="Timeout", office_id="Office A")

        entry = json.loads(audit_file.read_text().strip())
        assert entry["event_type"] == "NETWORK_ERROR"
        assert entry["success"] is False
        assert entry["error"] == "Timeout"
        assert re.fullmatch(r"[0-9a-f]{64}", entry["office_id"])

    def test_multiple_events_jsonl_format(self, tmp_path: Path) -> None:
        """Test multiple events create multiple JSONL lines."""
        audit_file = tmp_path / "audit.jsonl"
        logger = AuditLogger(audit_file)
        logger.log_vault_created()
        logger.log_vault_unlocked()
        logger.log_vault_locked()

        lines = audit_file.read_text().strip().split("\n")
        assert len(lines) == 3
        for line in lines:
            entry = json.loads(line)
            assert "event_type" in entry
            assert "timestamp" in entry


class TestAuditLoggerRetention:
    """Test 90-day retention policy."""

    def test_cleanup_removes_old_entries(self, tmp_path: Path) -> None:
        """Test cleanup removes entries older than 90 days."""
        audit_file = tmp_path / "audit.jsonl"
        old_entry = {
            "timestamp": (datetime.now(UTC) - timedelta(days=91)).isoformat(),
            "event_type": "OLD_EVENT",
            "user": "test",
            "success": True,
        }
        recent_entry = {
            "timestamp": (datetime.now(UTC) - timedelta(days=30)).isoformat(),
            "event_type": "RECENT_EVENT",
            "user": "test",
            "success": True,
        }
        audit_file.write_text(f"{json.dumps(old_entry)}\n{json.dumps(recent_entry)}\n")

        logger = AuditLogger(audit_file)
        logger.cleanup_old_entries()

        lines = audit_file.read_text().strip().split("\n")
        assert len(lines) == 1
        entry = json.loads(lines[0])
        assert entry["event_type"] == "RECENT_EVENT"

    def test_cleanup_keeps_entries_within_retention(self, tmp_path: Path) -> None:
        """Test cleanup keeps entries within 90-day retention."""
        audit_file = tmp_path / "audit.jsonl"
        entries = []
        for days_ago in [1, 30, 60, 89]:
            entry = {
                "timestamp": (datetime.now(UTC) - timedelta(days=days_ago)).isoformat(),
                "event_type": f"EVENT_{days_ago}",
                "user": "test",
                "success": True,
            }
            entries.append(json.dumps(entry))
        audit_file.write_text("\n".join(entries) + "\n")

        logger = AuditLogger(audit_file)
        logger.cleanup_old_entries()

        lines = audit_file.read_text().strip().split("\n")
        assert len(lines) == 4


class TestAuditLoggerThreadSafety:
    """Test thread-safe file writes."""

    def test_concurrent_writes(self, tmp_path: Path) -> None:
        """Test multiple threads can write without corruption."""
        import threading

        audit_file = tmp_path / "audit.jsonl"
        logger = AuditLogger(audit_file)

        def write_events() -> None:
            for i in range(10):
                logger.log("TEST_EVENT", success=True, details={"iteration": i})

        threads = [threading.Thread(target=write_events) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        lines = audit_file.read_text().strip().split("\n")
        assert len(lines) == 50
