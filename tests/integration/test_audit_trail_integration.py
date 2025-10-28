"""Integration test for complete audit trail from vault creation to query execution."""

import hashlib
import json
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from opendental_query.utils.audit_logger import AuditLogger


class TestCompleteAuditTrail:
    """Test complete audit trail across multiple operations."""

    def test_full_workflow_audit_trail(self, temp_dir):
        """Test that a complete workflow generates proper audit trail."""
        log_path = temp_dir / "audit.log"
        logger = AuditLogger(log_path)

        # Simulate complete workflow
        # 1. Create vault
        logger.log_vault_created()

        # 2. Add offices
        logger.log_office_added("Main Office")
        logger.log_office_added("Branch Office")

        # 3. Unlock vault
        logger.log_vault_unlocked()

        # 4. Execute query
        sql = "SELECT PatNum, LName, FName FROM patient WHERE LName LIKE 'Smith%'"
        logger.log_query_executed(sql, ["Main Office", "Branch Office"])

        # 5. Export results
        export_path = Path("C:/Users/Test/Downloads/patient_results.xlsx")
        logger.log_export_created(export_path, 42)

        # 6. Lock vault
        logger.log_vault_locked()

        # Verify audit log contains all events in order
        with open(log_path) as f:
            entries = [json.loads(line) for line in f]

        # Should have at least 6 events (may have 7 if lock creates additional entry)
        assert len(entries) >= 6

        # Verify event sequence (check first 6 minimum)
        assert entries[0]["event_type"] == "VAULT_CREATED"
        assert entries[1]["event_type"] == "OFFICE_ADDED"
        assert re.fullmatch(r"[0-9a-f]{64}", entries[1]["details"]["office_token"])
        assert entries[2]["event_type"] == "OFFICE_ADDED"
        assert re.fullmatch(r"[0-9a-f]{64}", entries[2]["details"]["office_token"])
        assert entries[3]["event_type"] == "VAULT_UNLOCKED"
        assert entries[4]["event_type"] == "QUERY_EXECUTED"
        assert entries[4]["details"]["office_count"] == 2
        assert entries[5]["event_type"] == "EXPORT_CREATED"

        # Verify all entries have required fields
        for entry in entries:
            assert "timestamp" in entry
            assert "event_type" in entry
            assert "user" in entry
            assert "success" in entry
            assert entry["user"] == logger.current_user

            # Verify timestamps are in order (each entry occurs after previous)
            if entries.index(entry) > 0:
                prev_entry = entries[entries.index(entry) - 1]
                prev_time = datetime.fromisoformat(prev_entry["timestamp"])
                curr_time = datetime.fromisoformat(entry["timestamp"])
                # Make timezone-aware if needed
                if prev_time.tzinfo is None:
                    prev_time = prev_time.replace(tzinfo=UTC)
                if curr_time.tzinfo is None:
                    curr_time = curr_time.replace(tzinfo=UTC)
                assert curr_time >= prev_time

    def test_security_event_audit_trail(self, temp_dir):
        """Test audit trail for security events (failures, lockouts)."""
        log_path = temp_dir / "audit.log"
        logger = AuditLogger(log_path)

        # Simulate failed authentication attempts leading to lockout
        logger.log_authentication_failed("Incorrect password")
        logger.log_authentication_failed("Incorrect password")
        logger.log_authentication_failed("Incorrect password")
        logger.log_vault_lockout()

        # Verify all security events logged
        with open(log_path) as f:
            entries = [json.loads(line) for line in f]

        assert len(entries) == 4
        assert all(e["event_type"] in ["AUTHENTICATION_FAILED", "VAULT_LOCKOUT"] for e in entries)

        # Verify failures marked as unsuccessful
        for entry in entries[:3]:
            assert entry["success"] is False
            assert entry["details"]["reason"] == "Incorrect password"

        # Lockout event is successful (lockout activated successfully)
        assert entries[3]["success"] is True

    def test_office_management_audit_trail(self, temp_dir):
        """Test audit trail for office add/remove operations."""
        log_path = temp_dir / "audit.log"
        logger = AuditLogger(log_path)

        # Add and remove offices
        logger.log_office_added("Office A")
        logger.log_office_added("Office B")
        logger.log_office_added("Office C")
        logger.log_office_removed("Office B")

        # Verify operations logged
        with open(log_path) as f:
            entries = [json.loads(line) for line in f]

        assert len(entries) == 4
        assert entries[0]["event_type"] == "OFFICE_ADDED"
        assert entries[1]["event_type"] == "OFFICE_ADDED"
        assert entries[2]["event_type"] == "OFFICE_ADDED"
        assert entries[3]["event_type"] == "OFFICE_REMOVED"
        assert re.fullmatch(r"[0-9a-f]{64}", entries[3]["details"]["office_token"])

    def test_query_history_with_hashing(self, temp_dir):
        """Test that query history maintains hashed queries for privacy."""
        log_path = temp_dir / "audit.log"
        logger = AuditLogger(log_path)

        queries = [
            "SELECT * FROM patient WHERE PatNum = 123",
            "SELECT * FROM appointment WHERE AptDateTime > '2024-01-01'",
            "SELECT * FROM procedurelog WHERE ProcFee > 500.00",
        ]

        # Execute multiple queries
        for sql in queries:
            logger.log_query_executed(sql, ["Office1"])

        # Verify all queries logged with hashes
        with open(log_path) as f:
            log_content = f.read()
            entries = [json.loads(line) for line in log_content.strip().split("\n")]

        assert len(entries) == 3

        # Verify no query text appears in log (only hashes)
        for sql in queries:
            assert sql not in log_content

        # Verify hashes are present and correct
        for i, entry in enumerate(entries):
            expected_hash = hashlib.sha256(queries[i].encode()).hexdigest()
            assert entry["details"]["query_hash"] == expected_hash

    def test_export_tracking_with_hashed_paths(self, temp_dir):
        """Test that exports are tracked with hashed path metadata for audit compliance."""
        log_path = temp_dir / "audit.log"
        logger = AuditLogger(log_path)

        # Create multiple exports
        exports = [
            (Path("C:/Users/Alice/Downloads/report1.xlsx"), 100),
            (Path("C:/Users/Alice/Downloads/report2.xlsx"), 50),
            (Path("C:/Users/Alice/Downloads/report3.xlsx"), 75),
        ]

        for export_path, row_count in exports:
            logger.log_export_created(export_path, row_count)

        # Verify exports logged
        with open(log_path) as f:
            entries = [json.loads(line) for line in f]

        assert len(entries) == 3

        for i, entry in enumerate(entries):
            assert entry["event_type"] == "EXPORT_CREATED"
            details = entry["details"]
            assert details["row_count"] == exports[i][1]
            assert "file_path" not in details
            assert details["filename"] == exports[i][0].name
            assert re.fullmatch(r"[0-9a-f]{64}", details["path_hash"])

    def test_log_retention_cleanup_integration(self, temp_dir):
        """Test that log retention cleanup works with real audit entries."""
        log_path = temp_dir / "audit.log"
        logger = AuditLogger(log_path)

        # Create some recent entries
        logger.log_vault_created()
        logger.log_office_added("Current Office")

        # Manually add old entry (simulate 95-day-old entry)
        old_timestamp = (datetime.now(UTC) - timedelta(days=95)).isoformat()
        old_entry = {
            "timestamp": old_timestamp,
            "event_type": "VAULT_CREATED",
            "user": logger.current_user,
            "success": True,
            "details": {},
        }

        # Insert old entry at the beginning
        with open(log_path) as f:
            current_content = f.read()

        with open(log_path, "w") as f:
            f.write(json.dumps(old_entry) + "\n")
            f.write(current_content)

        # Verify we have 3 entries total
        with open(log_path) as f:
            entries_before = [json.loads(line) for line in f]
        assert len(entries_before) == 3

        # Trigger cleanup
        logger.cleanup_old_entries()

        # Verify old entry removed, recent entries preserved
        with open(log_path) as f:
            entries_after = [json.loads(line) for line in f]

        assert len(entries_after) == 2  # Old entry should be removed
        assert all(
            e["event_type"] != "VAULT_CREATED"
            or datetime.fromisoformat(e["timestamp"]).replace(tzinfo=UTC)
            > (datetime.now(UTC) - timedelta(days=90))
            for e in entries_after
        )


@pytest.fixture
def temp_dir(tmp_path):
    """Provide a temporary directory for tests."""
    return tmp_path
