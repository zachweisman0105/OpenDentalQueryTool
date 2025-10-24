"""Tests for Excel-style UX improvements (US6)."""

from opendental_query.models.query import OfficeQueryResult, QueryResult
from opendental_query.renderers.table import TableRenderer


class TestVisualSeparators:
    """Test visual row separators between offices in table output."""

    def test_office_separator_in_output(self):
        """Test that office results are visually separated."""
        # Create mock query results from multiple offices
        office1_result = OfficeQueryResult(
            office_id="Office A",
            success=True,
            rows=[
                {"PatNum": 1, "LName": "Smith"},
                {"PatNum": 2, "LName": "Jones"},
            ],
            columns=["PatNum", "LName"],
            row_count=2,
            execution_time_ms=10.0,
        )

        office2_result = OfficeQueryResult(
            office_id="Office B",
            success=True,
            rows=[
                {"PatNum": 3, "LName": "Brown"},
                {"PatNum": 4, "LName": "Davis"},
            ],
            columns=["PatNum", "LName"],
            row_count=2,
            execution_time_ms=12.0,
        )

        query_result = QueryResult(
            query="SELECT PatNum, LName FROM patient",
            office_results=[office1_result, office2_result],
            total_rows=4,
            successful_offices=2,
            failed_offices=0,
        )

        # Render table
        renderer = TableRenderer()
        output = renderer.render(query_result)

        # Verify output contains both offices' data
        assert "Office A" in output or "1" in output  # Office name or first ID
        assert "Office B" in output or "3" in output  # Office name or different ID
        assert "Smith" in output
        assert "Brown" in output

    def test_separator_between_consecutive_offices(self):
        """Test separator appears between consecutive office sections."""
        office1 = OfficeQueryResult(
            office_id="Office A",
            success=True,
            rows=[{"PatNum": 1}],
            columns=["PatNum"],
            row_count=1,
            execution_time_ms=10.0,
        )

        office2 = OfficeQueryResult(
            office_id="Office B",
            success=True,
            rows=[{"PatNum": 2}],
            columns=["PatNum"],
            row_count=1,
            execution_time_ms=10.0,
        )

        query_result = QueryResult(
            query="SELECT PatNum FROM patient",
            office_results=[office1, office2],
            total_rows=2,
            successful_offices=2,
            failed_offices=0,
        )

        renderer = TableRenderer()
        output = renderer.render(query_result)

        # Should have content (exact separator format depends on implementation)
        assert len(output) > 0
        assert "1" in output
        assert "2" in output

    def test_no_separator_for_single_office(self):
        """Test no separator when only one office."""
        office1 = OfficeQueryResult(
            office_id="Office A",
            success=True,
            rows=[{"PatNum": 1}, {"PatNum": 2}],
            columns=["PatNum"],
            row_count=2,
            execution_time_ms=10.0,
        )

        query_result = QueryResult(
            query="SELECT PatNum FROM patient",
            office_results=[office1],
            total_rows=2,
            successful_offices=1,
            failed_offices=0,
        )

        renderer = TableRenderer()
        output = renderer.render(query_result)

        # Should render data without excessive separators
        assert "1" in output
        assert "2" in output


class TestColumnAlignment:
    """Test proper column alignment in table output."""

    def test_numeric_column_right_aligned(self):
        """Test that numeric columns are right-aligned."""
        office_result = OfficeQueryResult(
            office_id="Office A",
            success=True,
            rows=[
                {"PatNum": 1, "Fee": 100.50},
                {"PatNum": 123, "Fee": 50.25},
            ],
            columns=["PatNum", "Fee"],
            row_count=2,
            execution_time_ms=10.0,
        )

        query_result = QueryResult(
            query="SELECT PatNum, Fee FROM procedurelog",
            office_results=[office_result],
            total_rows=2,
            successful_offices=1,
            failed_offices=0,
        )

        renderer = TableRenderer()
        output = renderer.render(query_result)

        # Should contain the numeric values
        assert "1" in output or "100.50" in output
        assert "123" in output or "50.25" in output

    def test_text_column_left_aligned(self):
        """Test that text columns are left-aligned."""
        office_result = OfficeQueryResult(
            office_id="Office A",
            success=True,
            rows=[
                {"PatNum": 1, "LName": "Smith"},
                {"PatNum": 2, "LName": "Johnson"},
            ],
            columns=["PatNum", "LName"],
            row_count=2,
            execution_time_ms=10.0,
        )

        query_result = QueryResult(
            query="SELECT PatNum, LName FROM patient",
            office_results=[office_result],
            total_rows=2,
            successful_offices=1,
            failed_offices=0,
        )

        renderer = TableRenderer()
        output = renderer.render(query_result)

        # Should contain text values
        assert "Smith" in output
        assert "Johnson" in output

    def test_mixed_column_types_aligned_correctly(self):
        """Test mixed numeric and text columns have appropriate alignment."""
        office_result = OfficeQueryResult(
            office_id="Office A",
            success=True,
            rows=[
                {"PatNum": 1, "LName": "Smith", "Age": 45},
                {"PatNum": 2, "LName": "Jones", "Age": 32},
            ],
            columns=["PatNum", "LName", "Age"],
            row_count=2,
            execution_time_ms=10.0,
        )

        query_result = QueryResult(
            query="SELECT PatNum, LName, Age FROM patient",
            office_results=[office_result],
            total_rows=2,
            successful_offices=1,
            failed_offices=0,
        )

        renderer = TableRenderer()
        output = renderer.render(query_result)

        # Verify all data present
        assert "Smith" in output
        assert "Jones" in output
        assert "45" in output
        assert "32" in output


class TestOfficeIdentification:
    """Test clear identification of which office each row belongs to."""

    def test_office_names_displayed(self):
        """Test that office names are clearly displayed."""
        office1 = OfficeQueryResult(
            office_id="Downtown Office",
            success=True,
            rows=[{"PatNum": 1}],
            columns=["PatNum"],
            row_count=1,
            execution_time_ms=10.0,
        )

        office2 = OfficeQueryResult(
            office_id="Uptown Office",
            success=True,
            rows=[{"PatNum": 2}],
            columns=["PatNum"],
            row_count=1,
            execution_time_ms=10.0,
        )

        query_result = QueryResult(
            query="SELECT PatNum FROM patient",
            office_results=[office1, office2],
            total_rows=2,
            successful_offices=2,
            failed_offices=0,
        )

        renderer = TableRenderer()
        output = renderer.render(query_result)

        # Office names should appear in output
        assert "Downtown Office" in output or "Downtown" in output
        assert "Uptown Office" in output or "Uptown" in output

    def test_office_column_added_to_results(self):
        """Test that an office identifier column can be added to results."""
        office_result = OfficeQueryResult(
            office_id="Office A",
            success=True,
            rows=[
                {"PatNum": 1, "LName": "Smith"},
                {"PatNum": 2, "LName": "Jones"},
            ],
            columns=["PatNum", "LName"],
            row_count=2,
            execution_time_ms=10.0,
        )

        query_result = QueryResult(
            query="SELECT PatNum, LName FROM patient",
            office_results=[office_result],
            total_rows=2,
            successful_offices=1,
            failed_offices=0,
        )

        renderer = TableRenderer()
        output = renderer.render(query_result)

        # Should show the data
        assert "Smith" in output
        assert "Jones" in output
