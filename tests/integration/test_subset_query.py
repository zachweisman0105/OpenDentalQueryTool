"""Integration tests for subset query execution.

Tests querying a subset of offices and verifying API call counts.
"""

import respx
from httpx import Response

from opendental_query.core.query_engine import QueryEngine


class TestSubsetQueryExecution:
    """Test querying subset of offices."""

    @respx.mock
    def test_subset_query_only_selected_offices(self) -> None:
        """Test that only selected offices are queried (not all configured)."""
        # Configure 8 offices but select only 3
        office_credentials = {
            f"office{i}": ("dev_key", f"customer_key_{i}")
            for i in [1, 3, 5]  # Only 3 offices selected
        }

        base_url = "https://api.test.com"

        # Mock API responses - will be called 3 times (one per office)
        respx.put(f"{base_url}/queries/ShortQuery").mock(
            side_effect=[
                Response(200, json={"data": [{"id": 1, "name": "Test from office1"}]}),
                Response(200, json={"data": [{"id": 1, "name": "Test from office3"}]}),
                Response(200, json={"data": [{"id": 1, "name": "Test from office5"}]}),
            ]
        )

        engine = QueryEngine(max_concurrent=10)

        result = engine.execute(
            sql="SELECT id, name FROM test",
            office_credentials=office_credentials,
            api_base_url=base_url,
            timeout_seconds=30.0,
        )

        # Verify only 3 API calls were made (for selected offices)
        assert result.total_offices == 3
        assert result.successful_count == 3
        assert len(result.all_rows) == 3  # 1 row from each office

        # Verify respx captured exactly 3 calls
        assert len(respx.calls) == 3

    @respx.mock
    def test_subset_query_concurrent_execution(self) -> None:
        """Test that subset queries execute concurrently."""
        import time

        # Select 5 offices from larger pool
        office_credentials = {
            f"office{i}": ("dev_key", f"customer_key_{i}")
            for i in range(1, 6)  # office1 through office5
        }

        base_url = "https://api.test.com"

        # Mock API responses - will be called 5 times
        respx.put(f"{base_url}/queries/ShortQuery").mock(
            side_effect=[
                Response(200, json={"data": [{"office": f"office{i}", "value": i}]})
                for i in range(1, 6)
            ]
        )

        engine = QueryEngine(max_concurrent=10)

        start_time = time.time()
        result = engine.execute(
            sql="SELECT office, value FROM data",
            office_credentials=office_credentials,
            api_base_url=base_url,
            timeout_seconds=30.0,
        )
        elapsed = time.time() - start_time

        # Verify all 5 completed
        assert result.total_offices == 5
        assert result.successful_count == 5

        # With concurrent execution, should complete quickly (< 2 seconds)
        # If sequential, would take much longer
        assert elapsed < 2.0, f"Took {elapsed}s - should be concurrent"

    @respx.mock
    def test_single_office_subset(self) -> None:
        """Test subset query with just one office selected."""
        office_credentials = {"office_main": ("dev_key", "customer_key_main")}

        base_url = "https://api.test.com"

        respx.put(f"{base_url}/queries/ShortQuery").mock(
            return_value=Response(200, json={"data": [{"count": 42}]})
        )

        engine = QueryEngine(max_concurrent=1)

        result = engine.execute(
            sql="SELECT COUNT(*) as count FROM patients",
            office_credentials=office_credentials,
            api_base_url=base_url,
            timeout_seconds=30.0,
        )

        assert result.total_offices == 1
        assert result.successful_count == 1
        assert len(result.all_rows) == 1
        assert result.all_rows[0]["count"] == 42

    @respx.mock
    def test_subset_with_mixed_success_failure(self) -> None:
        """Test subset query where some offices succeed and some fail."""
        office_credentials = {
            "office_good1": ("dev_key", "key1"),
            "office_bad": ("dev_key", "key_bad"),
            "office_good2": ("dev_key", "key2"),
        }

        base_url = "https://api.test.com"

        # Mock responses: 2 successes and 1 failure
        respx.put(f"{base_url}/queries/ShortQuery").mock(
            side_effect=[
                Response(200, json={"data": [{"data": "good1"}]}),
                Response(500, json={"error": "Internal Server Error"}),
                Response(200, json={"data": [{"data": "good2"}]}),
            ]
        )

        engine = QueryEngine(max_concurrent=10)

        result = engine.execute(
            sql="SELECT data FROM test",
            office_credentials=office_credentials,
            api_base_url=base_url,
            timeout_seconds=30.0,
        )

        # Verify counts
        assert result.total_offices == 3
        assert result.successful_count == 2
        assert result.failed_count == 1
        assert len(result.all_rows) == 2  # Only successful offices

    def test_empty_subset_returns_empty_result(self) -> None:
        """Test that empty office credentials returns empty result."""
        engine = QueryEngine(max_concurrent=10)

        result = engine.execute(
            sql="SELECT 1",
            office_credentials={},  # Empty
            api_base_url="https://api.test.com",
            timeout_seconds=30.0,
        )

        # Empty credentials should result in zero offices processed
        assert result.total_offices == 0
        assert result.successful_count == 0
        assert len(result.all_rows) == 0


class TestSubsetQueryResultMerging:
    """Test result merging for subset queries."""

    @respx.mock
    def test_subset_results_include_office_column(self) -> None:
        """Test that merged results include office identifier."""
        office_credentials = {
            "office_alpha": ("dev_key", "key_alpha"),
            "office_beta": ("dev_key", "key_beta"),
        }

        base_url = "https://api.test.com"

        respx.put(f"{base_url}/queries/ShortQuery").mock(
            side_effect=[
                Response(200, json={"data": [{"patient_id": 1, "name": "Alice"}]}),
                Response(200, json={"data": [{"patient_id": 2, "name": "Bob"}]}),
            ]
        )

        engine = QueryEngine(max_concurrent=10)

        result = engine.execute(
            sql="SELECT patient_id, name FROM patients",
            office_credentials=office_credentials,
            api_base_url=base_url,
            timeout_seconds=30.0,
        )

        # Verify office column exists and contains correct values
        assert len(result.all_rows) == 2
        office_values = {row.get("Office") for row in result.all_rows}
        assert office_values == {"office_alpha", "office_beta"}

    @respx.mock
    def test_subset_preserves_row_order(self) -> None:
        """Test that rows maintain order within each office."""
        office_credentials = {
            "office1": ("dev_key", "key1"),
        }

        base_url = "https://api.test.com"

        respx.put(f"{base_url}/queries/ShortQuery").mock(
            return_value=Response(
                200,
                json={
                    "data": [
                        {"seq": 1, "data": "first"},
                        {"seq": 2, "data": "second"},
                        {"seq": 3, "data": "third"},
                    ]
                },
            )
        )

        engine = QueryEngine(max_concurrent=1)

        result = engine.execute(
            sql="SELECT seq, data FROM test ORDER BY seq",
            office_credentials=office_credentials,
            api_base_url=base_url,
            timeout_seconds=30.0,
        )

        # Verify order preserved
        assert len(result.all_rows) == 3
        assert result.all_rows[0]["seq"] == 1
        assert result.all_rows[1]["seq"] == 2
        assert result.all_rows[2]["seq"] == 3
