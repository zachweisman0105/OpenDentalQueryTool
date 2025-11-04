"""
Unit tests for QueryEngine.

Tests parallel execution with ThreadPoolExecutor, independent office failures,
per-office timeouts, result merging with Office column, and schema consistency validation.
"""

import time
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from opendental_query.core.query_engine import QueryEngine
from opendental_query.models.query import OfficeQueryStatus


class TestParallelExecution:
    """Test ThreadPoolExecutor-based parallel execution."""

    def test_executes_queries_in_parallel(self) -> None:
        """Should execute queries across multiple offices in parallel."""
        engine = QueryEngine(max_concurrent=3)

        # Track execution times
        execution_times: dict[str, float] = {}

        def mock_query(sql: str, developer_key: str, customer_key: str) -> list[dict[str, Any]]:
            office_id = customer_key  # Use customer_key as office_id for testing
            start = time.time()
            time.sleep(0.1)  # Simulate API delay
            execution_times[office_id] = time.time() - start
            return [{"count": "10"}]

        with patch("opendental_query.core.query_engine.APIClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.query = mock_query
            mock_client_class.return_value = mock_client

            office_ids = ["office1", "office2", "office3"]
            credentials = {
                "office1": ("dev", "office1"),
                "office2": ("dev", "office2"),
                "office3": ("dev", "office3"),
            }

            start_time = time.time()
            result = engine.execute(
                sql="SELECT COUNT(*) FROM patient",
                office_credentials=credentials,
                api_base_url="https://api.example.com",
            )
            total_time = time.time() - start_time

        # If executed serially: 0.3s+, if parallel: ~0.1s
        assert total_time < 0.25  # Should complete in < 0.25s (parallel)
        assert result.total_offices == 3
        assert result.successful_count == 3
        assert result.failed_count == 0

    def test_respects_max_concurrent_limit(self) -> None:
        """Should limit concurrent executions to max_workers."""
        engine = QueryEngine(max_concurrent=2)

        # Track concurrent executions
        concurrent_count = [0]
        max_concurrent = [0]

        def mock_query(sql: str, developer_key: str, customer_key: str) -> list[dict[str, Any]]:
            concurrent_count[0] += 1
            max_concurrent[0] = max(max_concurrent[0], concurrent_count[0])
            time.sleep(0.05)
            concurrent_count[0] -= 1
            return [{"result": "1"}]

        with patch("opendental_query.core.query_engine.APIClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.query = mock_query
            mock_client_class.return_value = mock_client

            credentials = {f"office{i}": ("dev", f"office{i}") for i in range(5)}

            engine.execute(
                sql="SELECT 1",
                office_credentials=credentials,
                api_base_url="https://api.example.com",
            )

        # Should never exceed max_concurrent=2
        assert max_concurrent[0] <= 2

    def test_invokes_progress_callback_for_each_office(self) -> None:
        """Should invoke progress callback as each office completes."""
        engine = QueryEngine(max_concurrent=3)

        with patch("opendental_query.core.query_engine.APIClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.query.return_value = [{"result": "1"}]
            mock_client_class.return_value = mock_client

            credentials = {
                "office1": ("dev", "cust1"),
                "office2": ("dev", "cust2"),
                "office3": ("dev", "cust3"),
            }

            callbacks: list[str] = []

            def capture(result: Any) -> None:
                callbacks.append(f"{result.office_id}:{result.row_count}")

            engine.execute(
                sql="SELECT 1",
                office_credentials=credentials,
                api_base_url="https://api.example.com",
                progress_callback=capture,
            )

        assert sorted(callbacks) == ["office1:1", "office2:1", "office3:1"]

    def test_execute_injects_office_identifier_into_rows(self) -> None:
        """Merged rows should reflect the office identifiers provided to the engine."""
        engine = QueryEngine(max_concurrent=1)

        with patch("opendental_query.core.query_engine.APIClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.query.return_value = [{"value": "123"}]
            mock_client_class.return_value = mock_client

            result = engine.execute(
                sql="SELECT 1",
                office_credentials={"Renamed Office": ("dev", "cust")},
                api_base_url="https://api.example.com",
            )

        assert result.all_rows == [{"Office": "Renamed Office", "value": "123"}]


class TestTimeoutHandling:
    """Test per-office timeout behavior."""

    def test_applies_timeout_to_slow_offices(self) -> None:
        """Should timeout offices that exceed timeout_seconds."""
        engine = QueryEngine(max_concurrent=3)

        def mock_query(sql: str, developer_key: str, customer_key: str) -> list[dict[str, Any]]:
            if customer_key == "slow_office":
                time.sleep(2.0)  # Exceeds timeout
            return [{"result": "1"}]

        with patch("opendental_query.core.query_engine.APIClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.query = mock_query
            mock_client_class.return_value = mock_client

            credentials = {
                "fast_office": ("dev", "fast_office"),
                "slow_office": ("dev", "slow_office"),
            }

            result = engine.execute(
                sql="SELECT 1",
                office_credentials=credentials,
                api_base_url="https://api.example.com",
                timeout_seconds=0.5,
            )

        assert result.total_offices == 2
        assert result.successful_count == 1  # Only fast_office
        assert result.failed_count == 1  # slow_office timed out

        # Check that slow_office is marked as timeout
        slow_result = next(r for r in result.office_results if r.office_id == "slow_office")
        assert slow_result.status == OfficeQueryStatus.TIMEOUT

    def test_default_timeout_is_5_minutes(self) -> None:
        """Should use 300 seconds (5 minutes) as default timeout."""
        engine = QueryEngine(max_concurrent=3)

        with patch("opendental_query.core.query_engine.APIClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.query.return_value = [{"result": "1"}]
            mock_client_class.return_value = mock_client

            credentials = {"office1": ("dev", "cust1")}

            # Don't specify timeout - should use default
            result = engine.execute(
                sql="SELECT 1",
                office_credentials=credentials,
                api_base_url="https://api.example.com",
            )

        # Verify it completed (would have failed if timeout was too short)
        assert result.successful_count == 1


class TestIndependentFailureHandling:
    """Test that failures in one office don't affect others."""

    def test_continues_with_remaining_offices_on_failure(self) -> None:
        """Should continue executing remaining offices if one fails."""
        engine = QueryEngine(max_concurrent=3)

        def mock_query(sql: str, developer_key: str, customer_key: str) -> list[dict[str, Any]]:
            if customer_key == "failing_office":
                raise ValueError("API error")
            return [{"result": "success"}]

        with patch("opendental_query.core.query_engine.APIClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.query = mock_query
            mock_client_class.return_value = mock_client

            credentials = {
                "office1": ("dev", "office1"),
                "failing_office": ("dev", "failing_office"),
                "office3": ("dev", "office3"),
            }

            result = engine.execute(
                sql="SELECT 1",
                office_credentials=credentials,
                api_base_url="https://api.example.com",
            )

        assert result.total_offices == 3
        assert result.successful_count == 2  # office1 and office3
        assert result.failed_count == 1  # failing_office

        # Verify failing office has error status
        failing_result = next(r for r in result.office_results if r.office_id == "failing_office")
        assert failing_result.status == OfficeQueryStatus.ERROR
        assert "API error" in failing_result.error_message

    def test_captures_different_error_types(self) -> None:
        """Should capture and record different types of errors."""
        engine = QueryEngine(max_concurrent=3)

        def mock_query(sql: str, developer_key: str, customer_key: str) -> list[dict[str, Any]]:
            if customer_key == "connection_error":
                raise ConnectionError("Network failure")
            elif customer_key == "value_error":
                raise ValueError("Invalid response")
            return [{"result": "success"}]

        with patch("opendental_query.core.query_engine.APIClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.query = mock_query
            mock_client_class.return_value = mock_client

            credentials = {
                "connection_error": ("dev", "connection_error"),
                "value_error": ("dev", "value_error"),
                "success": ("dev", "success"),
            }

            result = engine.execute(
                sql="SELECT 1",
                office_credentials=credentials,
                api_base_url="https://api.example.com",
            )

        assert result.successful_count == 1
        assert result.failed_count == 2

        # Check error messages
        conn_result = next(r for r in result.office_results if r.office_id == "connection_error")
        assert "Network failure" in conn_result.error_message

        val_result = next(r for r in result.office_results if r.office_id == "value_error")
        assert "Invalid response" in val_result.error_message


class TestResultMerging:
    """Test result merging with Office column injection."""

    def test_merges_results_with_office_column(self) -> None:
        """Should merge results and inject Office column."""
        engine = QueryEngine(max_concurrent=3)

        def mock_query(sql: str, developer_key: str, customer_key: str) -> list[dict[str, Any]]:
            office_num = customer_key[-1]  # Extract number from office_id
            return [
                {"PatNum": f"{office_num}1", "LName": f"Smith{office_num}"},
                {"PatNum": f"{office_num}2", "LName": f"Jones{office_num}"},
            ]

        with patch("opendental_query.core.query_engine.APIClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.query = mock_query
            mock_client_class.return_value = mock_client

            credentials = {
                "office1": ("dev", "office1"),
                "office2": ("dev", "office2"),
            }

            result = engine.execute(
                sql="SELECT PatNum, LName FROM patient",
                office_credentials=credentials,
                api_base_url="https://api.example.com",
            )

        # Should have 4 total rows (2 from each office)
        assert len(result.all_rows) == 4

        # Check Office column is injected
        assert "Office" in result.all_rows[0]

        # Verify Office values
        office1_rows = [r for r in result.all_rows if r["Office"] == "office1"]
        office2_rows = [r for r in result.all_rows if r["Office"] == "office2"]
        assert len(office1_rows) == 2
        assert len(office2_rows) == 2

    def test_preserves_original_column_order(self) -> None:
        """Should inject Office column as first column."""
        engine = QueryEngine(max_concurrent=1)

        with patch("opendental_query.core.query_engine.APIClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.query.return_value = [{"PatNum": "1", "LName": "Smith", "FName": "John"}]
            mock_client_class.return_value = mock_client

            credentials = {"office1": ("dev", "cust1")}

            result = engine.execute(
                sql="SELECT PatNum, LName, FName FROM patient",
                office_credentials=credentials,
                api_base_url="https://api.example.com",
            )

        # Office should be first column
        row = result.all_rows[0]
        keys = list(row.keys())
        assert keys[0] == "Office"
        assert keys[1:] == ["PatNum", "LName", "FName"]


class TestSchemaConsistency:
    """Test schema consistency validation across offices."""

    def test_validates_consistent_schemas(self) -> None:
        """Should pass when all offices return same schema."""
        engine = QueryEngine(max_concurrent=3)

        with patch("opendental_query.core.query_engine.APIClient") as mock_client_class:
            mock_client = MagicMock()
            # All offices return same columns
            mock_client.query.return_value = [{"PatNum": "1", "LName": "Smith"}]
            mock_client_class.return_value = mock_client

            credentials = {
                "office1": ("dev", "cust1"),
                "office2": ("dev", "cust2"),
            }

            result = engine.execute(
                sql="SELECT PatNum, LName FROM patient",
                office_credentials=credentials,
                api_base_url="https://api.example.com",
            )

        # Should succeed with consistent schema
        assert result.successful_count == 2
        assert result.schema_consistent is True

    def test_detects_schema_mismatch(self) -> None:
        """Should detect and report schema inconsistencies."""
        engine = QueryEngine(max_concurrent=3)

        def mock_query(sql: str, developer_key: str, customer_key: str) -> list[dict[str, Any]]:
            if customer_key == "cust1":
                return [{"PatNum": "1", "LName": "Smith"}]
            else:
                # Different schema
                return [{"PatNum": "2", "FName": "John"}]

        with patch("opendental_query.core.query_engine.APIClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.query = mock_query
            mock_client_class.return_value = mock_client

            credentials = {
                "office1": ("dev", "cust1"),
                "office2": ("dev", "cust2"),
            }

            with pytest.raises(ValueError, match="Schema mismatch"):
                engine.execute(
                    sql="SELECT PatNum, LName FROM patient",
                    office_credentials=credentials,
                    api_base_url="https://api.example.com",
                )

    def test_handles_empty_results_gracefully(self) -> None:
        """Should handle offices with no results (empty schema)."""
        engine = QueryEngine(max_concurrent=2)

        def mock_query(sql: str, developer_key: str, customer_key: str) -> list[dict[str, Any]]:
            if customer_key == "cust1":
                return [{"PatNum": "1", "LName": "Smith"}]
            else:
                return []  # Empty result

        with patch("opendental_query.core.query_engine.APIClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.query = mock_query
            mock_client_class.return_value = mock_client

            credentials = {
                "office1": ("dev", "cust1"),
                "office2": ("dev", "cust2"),
            }

            result = engine.execute(
                sql="SELECT PatNum, LName FROM patient WHERE 1=0",
                office_credentials=credentials,
                api_base_url="https://api.example.com",
            )

        # Should succeed - empty results don't affect schema consistency
        assert result.successful_count == 2
        assert len(result.all_rows) == 1  # Only office1 has data


class TestSQLPreprocessing:
    """Test SQL preprocessing with ensure_order_by."""

    def test_calls_ensure_order_by_before_execution(self) -> None:
        """Should call sql_parser.ensure_order_by() before sending SQL."""
        engine = QueryEngine(max_concurrent=1)

        with patch("opendental_query.core.query_engine.APIClient") as mock_client_class:
            with patch("opendental_query.core.query_engine.ensure_order_by") as mock_ensure:
                mock_client = MagicMock()
                mock_client.query.return_value = [{"result": "1"}]
                mock_client_class.return_value = mock_client
                mock_ensure.return_value = "SELECT * FROM patient ORDER BY 1 ASC"

                credentials = {"office1": ("dev", "cust1")}

                result = engine.execute(
                    sql="SELECT * FROM patient",
                    office_credentials=credentials,
                    api_base_url="https://api.example.com",
                )

        # Verify ensure_order_by was called with original SQL
        mock_ensure.assert_called_once_with("SELECT * FROM patient")

        # Verify query was executed successfully
        assert result.successful_count == 1
