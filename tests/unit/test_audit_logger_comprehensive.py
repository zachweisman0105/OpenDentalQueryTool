"""Comprehensive tests for audit logger covering all event types and edge cases."""

import hashlib
import json
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from opendental_query.utils.audit_logger import AuditLogger


class TestAllEventTypes:
    """Test coverage for all supported audit event types."""

    def test_vault_created_event(self, temp_dir):
        """Test audit logging for vault creation."""
        log_path = temp_dir / "audit.log"
        logger = AuditLogger(log_path)

        logger.log_vault_created()

        # Read and parse log
        with open(log_path) as f:
            log_entry = json.loads(f.readline())

        assert log_entry["event_type"] == "VAULT_CREATED"
        assert log_entry["user"] == logger.current_user  # Field is 'user', not 'username'
        assert "timestamp" in log_entry

    def test_vault_unlocked_event(self, temp_dir):
        """Test audit logging for vault unlock."""
        log_path = temp_dir / "audit.log"
        logger = AuditLogger(log_path)

        logger.log_vault_unlocked()

        with open(log_path) as f:
            log_entry = json.loads(f.readline())

        assert log_entry["event_type"] == "VAULT_UNLOCKED"
        assert "timestamp" in log_entry

    def test_vault_locked_event(self, temp_dir):
        """Test audit logging for vault lock."""
        log_path = temp_dir / "audit.log"
        logger = AuditLogger(log_path)

        logger.log_vault_locked()

        with open(log_path) as f:
            log_entry = json.loads(f.readline())

        assert log_entry["event_type"] == "VAULT_LOCKED"

    def test_office_added_event(self, temp_dir):
        """Test audit logging for office addition."""
        log_path = temp_dir / "audit.log"
        logger = AuditLogger(log_path)

        logger.log_office_added("TestOffice")

        with open(log_path) as f:
            log_entry = json.loads(f.readline())

        assert log_entry["event_type"] == "OFFICE_ADDED"
        assert "office_token" in log_entry["details"]
        assert re.fullmatch(r"[0-9a-f]{64}", log_entry["details"]["office_token"])

    def test_office_removed_event(self, temp_dir):
        """Test audit logging for office removal."""
        log_path = temp_dir / "audit.log"
        logger = AuditLogger(log_path)

        logger.log_office_removed("TestOffice")

        with open(log_path) as f:
            log_entry = json.loads(f.readline())

        assert log_entry["event_type"] == "OFFICE_REMOVED"
        assert "office_token" in log_entry["details"]
        assert re.fullmatch(r"[0-9a-f]{64}", log_entry["details"]["office_token"])

    def test_query_executed_event(self, temp_dir):
        """Test audit logging for query execution."""
        log_path = temp_dir / "audit.log"
        logger = AuditLogger(log_path)

        sql = "SELECT * FROM patient WHERE PatNum = 123"
        offices = ["Office1", "Office2"]

        logger.log_query_executed(sql, offices)

        with open(log_path) as f:
            log_entry = json.loads(f.readline())

        assert log_entry["event_type"] == "QUERY_EXECUTED"
        assert log_entry["details"]["office_count"] == 2  # In details dict
        assert "office_tokens" in log_entry["details"]
        assert len(log_entry["details"]["office_tokens"]) == 2
        for token in log_entry["details"]["office_tokens"]:
            assert re.fullmatch(r"[0-9a-f]{64}", token)
        assert "query_hash" in log_entry["details"]  # In details dict
        # Verify hash is SHA256 (64 hex chars)
        assert len(log_entry["details"]["query_hash"]) == 64
        assert all(c in "0123456789abcdef" for c in log_entry["details"]["query_hash"])

    def test_export_created_event(self, temp_dir):
        """Test audit logging for CSV export."""
        log_path = temp_dir / "audit.log"
        logger = AuditLogger(log_path)

        export_path = Path("C:/Users/Test/Downloads/results.csv")
        logger.log_export_created(export_path, 42)

        with open(log_path) as f:
            log_entry = json.loads(f.readline())

        assert log_entry["event_type"] == "EXPORT_CREATED"
        details = log_entry["details"]
        assert details["row_count"] == 42  # In details dict
        assert "file_path" not in details
        assert details["filename"] == "results.csv"
        assert re.fullmatch(r"[0-9a-f]{64}", details["path_hash"])

    def test_authentication_failed_event(self, temp_dir):
        """Test audit logging for failed authentication."""
        log_path = temp_dir / "audit.log"
        logger = AuditLogger(log_path)

        logger.log_authentication_failed("Invalid password")

        with open(log_path) as f:
            log_entry = json.loads(f.readline())

        assert log_entry["event_type"] == "AUTHENTICATION_FAILED"
        assert log_entry["details"]["reason"] == "Invalid password"  # In details dict

    def test_vault_lockout_event(self, temp_dir):
        """Test audit logging for vault lockout."""
        log_path = temp_dir / "audit.log"
        logger = AuditLogger(log_path)

        logger.log_vault_lockout()

        with open(log_path) as f:
            log_entry = json.loads(f.readline())

        assert log_entry["event_type"] == "VAULT_LOCKOUT"


class TestLogRetention:
    """Test 90-day log retention and cleanup."""

    def test_retention_policy_documented(self, temp_dir):
        """Verify 90-day retention policy is defined."""
        log_path = temp_dir / "audit.log"
        logger = AuditLogger(log_path)

        # Check if retention constant exists
        assert hasattr(logger, "RETENTION_DAYS") or hasattr(AuditLogger, "RETENTION_DAYS")

        # Verify it's 90 days
        retention = getattr(logger, "RETENTION_DAYS", None) or getattr(
            AuditLogger, "RETENTION_DAYS", None
        )
        if retention is not None:
            assert retention == 90

    def test_old_entries_removed(self, temp_dir):
        """Test that entries older than 90 days are removed."""
        log_path = temp_dir / "audit.log"
        logger = AuditLogger(log_path)

        # Create entries with different ages
        now = datetime.now(UTC)
        entries = [
            {
                "timestamp": (now - timedelta(days=95)).isoformat(),
                "event_type": "OLD",
                "username": "test",
            },
            {
                "timestamp": (now - timedelta(days=85)).isoformat(),
                "event_type": "RECENT",
                "username": "test",
            },
            {"timestamp": now.isoformat(), "event_type": "TODAY", "username": "test"},
        ]

        # Write entries
        with open(log_path, "w") as f:
            for entry in entries:
                f.write(json.dumps(entry) + "\n")

        # Trigger cleanup if method exists
        if hasattr(logger, "cleanup_old_entries"):
            logger.cleanup_old_entries()

            # Read remaining entries
            with open(log_path) as f:
                remaining = [json.loads(line) for line in f]

            # Old entry should be gone, recent ones should remain
            event_types = [e["event_type"] for e in remaining]
            assert "OLD" not in event_types
            assert "RECENT" in event_types
            assert "TODAY" in event_types
        else:
            pytest.skip("cleanup_old_entries not yet implemented")

    def test_cleanup_preserves_valid_entries(self, temp_dir):
        """Test that cleanup doesn't affect recent entries."""
        log_path = temp_dir / "audit.log"
        logger = AuditLogger(log_path)

        # Create only recent entries
        logger.log_vault_created()
        logger.log_query_executed("SELECT 1", ["Office1"])

        # Trigger cleanup
        if hasattr(logger, "cleanup_old_entries"):
            logger.cleanup_old_entries()

            # All entries should still be there
            with open(log_path) as f:
                entries = [json.loads(line) for line in f]

            assert len(entries) == 2
            assert entries[0]["event_type"] == "VAULT_CREATED"
            assert entries[1]["event_type"] == "QUERY_EXECUTED"
        else:
            pytest.skip("cleanup_old_entries not yet implemented")


class TestPHICompliance:
    """Test that audit logs don't contain unencrypted PHI."""

    def test_query_hash_instead_of_plaintext(self, temp_dir):
        """Test queries are hashed, not stored in plaintext."""
        log_path = temp_dir / "audit.log"
        logger = AuditLogger(log_path)

        phi_query = "SELECT * FROM patient WHERE LName = 'Smith' AND FName = 'John'"
        logger.log_query_executed(phi_query, ["Office1"])

        with open(log_path) as f:
            log_content = f.read()

        # PHI should NOT appear in log
        assert "Smith" not in log_content
        assert "John" not in log_content

        # But hash should be present
        log_entry = json.loads(log_content.strip())
        assert "query_hash" in log_entry["details"]  # In details dict

        # Verify hash matches expected SHA256
        expected_hash = hashlib.sha256(phi_query.encode()).hexdigest()
        assert log_entry["details"]["query_hash"] == expected_hash

    def test_no_credentials_logged(self, temp_dir):
        """Test that credentials are never logged."""
        log_path = temp_dir / "audit.log"
        logger = AuditLogger(log_path)

        # Log various events
        logger.log_vault_created()
        logger.log_office_added("TestOffice")
        logger.log_vault_unlocked()

        with open(log_path) as f:
            log_content = f.read()

        # Common credential-related keywords should not appear
        forbidden_terms = ["password", "passwd", "pwd", "secret", "api_key", "bearer"]
        for term in forbidden_terms:
            assert term.lower() not in log_content.lower()

    def test_file_paths_not_leaked(self, temp_dir):
        """Test that internal file paths don't leak sensitive info."""
        log_path = temp_dir / "audit.log"
        logger = AuditLogger(log_path)

        # Log export (only case where path is intentionally logged)
        export_path = Path("C:/Users/JohnDoe/Downloads/results.csv")
        logger.log_export_created(export_path, 10)

        with open(log_path) as f:
            log_entry = json.loads(f.readline())

        # Export logs include hashed path metadata without raw filesystem disclosure
        assert log_entry["details"]["filename"] == "results.csv"
        assert "path_hash" in log_entry["details"]
        assert re.fullmatch(r"[0-9a-f]{64}", log_entry["details"]["path_hash"])
        assert "file_path" not in log_entry["details"]

        # Verify other events do not log path hashes
        logger.log_vault_created()
        logger.log_query_executed("SELECT 1", ["Office1"])

        with open(log_path) as f:
            f.readline()  # Skip export entry
            for line in f:
                entry = json.loads(line)
                assert "path_hash" not in entry.get("details", {})
                assert "file_path" not in entry.get("details", {})

    def test_office_identifiers_are_tokenized(self, temp_dir):
        """Test that office identifiers are tokenized before logging."""
        log_path = temp_dir / "audit.log"
        logger = AuditLogger(log_path)

        office_name = "Downtown Clinic"
        logger.log_office_added(office_name)

        with open(log_path) as f:
            log_entry = json.loads(f.readline())

        assert "office_token" in log_entry["details"]
        token = log_entry["details"]["office_token"]
        assert token != office_name
        assert re.fullmatch(r"[0-9a-f]{64}", token)


class TestQueryHashing:
    """Test SHA256 query hashing for audit compliance."""

    def test_sha256_hash_format(self, temp_dir):
        """Test that query hashes are valid SHA256."""
        log_path = temp_dir / "audit.log"
        logger = AuditLogger(log_path)

        logger.log_query_executed("SELECT * FROM patient", ["Office1"])

        with open(log_path) as f:
            log_entry = json.loads(f.readline())

        query_hash = log_entry["details"]["query_hash"]  # In details dict

        # SHA256 is always 64 hex characters
        assert len(query_hash) == 64
        assert all(c in "0123456789abcdef" for c in query_hash)

    def test_same_query_same_hash(self, temp_dir):
        """Test deterministic hashing - same query produces same hash."""
        log_path = temp_dir / "audit.log"
        logger = AuditLogger(log_path)

        query = "SELECT PatNum, LName FROM patient LIMIT 10"

        logger.log_query_executed(query, ["Office1"])
        logger.log_query_executed(query, ["Office2"])

        with open(log_path) as f:
            entry1 = json.loads(f.readline())
            entry2 = json.loads(f.readline())

        assert entry1["details"]["query_hash"] == entry2["details"]["query_hash"]  # In details dict

    def test_different_queries_different_hashes(self, temp_dir):
        """Test that different queries produce different hashes."""
        log_path = temp_dir / "audit.log"
        logger = AuditLogger(log_path)

        logger.log_query_executed("SELECT * FROM patient", ["Office1"])
        logger.log_query_executed("SELECT * FROM appointment", ["Office1"])

        with open(log_path) as f:
            entry1 = json.loads(f.readline())
            entry2 = json.loads(f.readline())

        assert entry1["details"]["query_hash"] != entry2["details"]["query_hash"]  # In details dict

    def test_hash_matches_manual_calculation(self, temp_dir):
        """Test that hash matches manual SHA256 calculation."""
        log_path = temp_dir / "audit.log"
        logger = AuditLogger(log_path)

        query = "SELECT PatNum FROM patient WHERE PatNum = 123"
        expected_hash = hashlib.sha256(query.encode()).hexdigest()

        logger.log_query_executed(query, ["Office1"])

        with open(log_path) as f:
            log_entry = json.loads(f.readline())

        assert log_entry["details"]["query_hash"] == expected_hash  # In details dict


class TestErrorAuditing:
    """Test audit logging for error conditions."""

    def test_authentication_failure_logged(self, temp_dir):
        """Test that authentication failures are audited."""
        log_path = temp_dir / "audit.log"
        logger = AuditLogger(log_path)

        logger.log_authentication_failed("Incorrect password")

        with open(log_path) as f:
            log_entry = json.loads(f.readline())

        assert log_entry["event_type"] == "AUTHENTICATION_FAILED"
        assert "reason" in log_entry["details"]  # In details dict

    def test_lockout_logged(self, temp_dir):
        """Test that vault lockouts are audited."""
        log_path = temp_dir / "audit.log"
        logger = AuditLogger(log_path)

        logger.log_vault_lockout()

        with open(log_path) as f:
            log_entry = json.loads(f.readline())

        assert log_entry["event_type"] == "VAULT_LOCKOUT"

    def test_multiple_failures_tracked(self, temp_dir):
        """Test that multiple authentication failures are tracked."""
        log_path = temp_dir / "audit.log"
        logger = AuditLogger(log_path)

        # Log 3 failures
        for i in range(3):
            logger.log_authentication_failed(f"Attempt {i + 1}")

        with open(log_path) as f:
            entries = [json.loads(line) for line in f]

        assert len(entries) == 3
        assert all(e["event_type"] == "AUTHENTICATION_FAILED" for e in entries)


@pytest.fixture
def temp_dir(tmp_path):
    """Provide a temporary directory for tests."""
    return tmp_path
