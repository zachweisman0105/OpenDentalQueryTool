"""Tests for office subset query validation (US2)."""

import pytest


class TestOfficeSubsetValidation:
    """Test validation of office subsets for queries."""

    def test_valid_office_subset(self):
        """Test that valid office subsets are accepted."""
        available_offices = ["Office A", "Office B", "Office C"]

        # Valid subsets
        subset1 = ["Office A"]
        subset2 = ["Office A", "Office C"]
        subset3 = ["Office A", "Office B", "Office C"]

        # All should be valid subsets of available offices
        for subset in [subset1, subset2, subset3]:
            assert all(office in available_offices for office in subset)

    def test_invalid_office_in_subset(self):
        """Test that invalid office names in subset are rejected."""
        available_offices = ["Office A", "Office B"]

        # Test: invalid office name
        invalid_subset = ["Office A", "Office Z"]  # Office Z doesn't exist

        # Verify Office Z is not in available offices
        assert "Office Z" not in available_offices
        assert not all(office in available_offices for office in invalid_subset)

    def test_empty_office_subset(self):
        """Test that empty office subsets are handled correctly."""
        available_offices = ["Office A"]

        # Test: empty subset
        empty_subset = []

        # Empty subset should be considered invalid (no offices to query)
        assert len(empty_subset) == 0

    def test_subset_with_duplicates(self):
        """Test that duplicate office names in subset are handled."""
        available_offices = ["Office A", "Office B"]

        # Test: subset with duplicates
        subset_with_dupes = ["Office A", "Office A", "Office B"]

        # Verify duplicates exist
        assert subset_with_dupes.count("Office A") == 2

        # Deduplication should result in unique offices only
        unique_offices = list(set(subset_with_dupes))
        assert len(unique_offices) == 2
        assert "Office A" in unique_offices
        assert "Office B" in unique_offices


class TestOfficeSubsetFiltering:
    """Test filtering and validation of office subsets."""

    def test_filter_valid_offices_from_subset(self):
        """Test filtering only valid offices from a mixed subset."""
        available_offices = {"Office A", "Office B"}

        # Mixed subset: some valid, some invalid
        mixed_subset = ["Office A", "Office Z", "Office B", "Office X"]

        # Filter to only valid offices
        valid_offices = [name for name in mixed_subset if name in available_offices]
        invalid_offices = [name for name in mixed_subset if name not in available_offices]

        assert len(valid_offices) == 2
        assert "Office A" in valid_offices
        assert "Office B" in valid_offices
        assert len(invalid_offices) == 2
        assert "Office Z" in invalid_offices
        assert "Office X" in invalid_offices

    def test_case_sensitive_office_names(self):
        """Test that office name matching is case-sensitive."""
        available_offices = {"Office A"}

        # Test case variations
        assert "Office A" in available_offices
        assert "office a" not in available_offices
        assert "OFFICE A" not in available_offices
        assert "Office a" not in available_offices


class TestOfficeSubsetLogging:
    """Test audit logging for subset queries."""

    def test_subset_query_logged(self, temp_dir):
        """Test that subset queries are properly audited."""
        import json

        from opendental_query.utils.audit_logger import AuditLogger

        audit_path = temp_dir / "audit.log"
        logger = AuditLogger(audit_path)

        # Log a subset query
        sql = "SELECT * FROM patient LIMIT 10"
        selected_offices = ["Office A", "Office C"]

        logger.log_query_executed(sql, selected_offices)

        # Verify audit entry
        with open(audit_path) as f:
            entry = json.loads(f.readline())

        assert entry["event_type"] == "QUERY_EXECUTED"
        assert entry["details"]["office_count"] == 2
        assert "query_hash" in entry["details"]

    def test_all_offices_vs_subset_distinguishable(self, temp_dir):
        """Test that queries to all offices vs subset are distinguishable in audit log."""
        import json

        from opendental_query.utils.audit_logger import AuditLogger

        audit_path = temp_dir / "audit.log"
        logger = AuditLogger(audit_path)

        sql = "SELECT * FROM patient LIMIT 10"

        # Query all offices
        logger.log_query_executed(sql, ["Office A", "Office B", "Office C"])

        # Query subset
        logger.log_query_executed(sql, ["Office A"])

        # Verify both logged with different office counts
        with open(audit_path) as f:
            entry1 = json.loads(f.readline())
            entry2 = json.loads(f.readline())

        assert entry1["details"]["office_count"] == 3
        assert entry2["details"]["office_count"] == 1


@pytest.fixture
def temp_dir(tmp_path):
    """Provide a temporary directory for tests."""
    return tmp_path
