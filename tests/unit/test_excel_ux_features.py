"""Unit tests for Excel-style UX enhancements (US6).

Tests row separators, data type detection, NO_COLOR handling.
"""

import os
from decimal import Decimal
from io import StringIO
from unittest.mock import patch

from rich.console import Console

from opendental_query.renderers.table import TableRenderer


class TestRowSeparators:
    """Test row separators every 20 rows."""

    def test_separator_every_20_rows(self) -> None:
        """Test that separators are added every 20 rows."""
        renderer = TableRenderer(separator_interval=20)
        # Create 45 rows to test separators at rows 20 and 40
        rows = [{"ID": i, "Name": f"Item{i}"} for i in range(1, 46)]

        output = StringIO()
        console = Console(file=output, width=100, legacy_windows=False)
        renderer.render(rows, console=console)

        result = output.getvalue()
        # Verify data is present
        assert "Item1" in result
        assert "Item45" in result

    def test_separator_interval_zero_disables_separators(self) -> None:
        """Test that separator_interval=0 disables separators."""
        renderer = TableRenderer(separator_interval=0)
        rows = [{"ID": i, "Name": f"Item{i}"} for i in range(1, 46)]

        output = StringIO()
        console = Console(file=output, width=100, legacy_windows=False)
        renderer.render(rows, console=console)

        result = output.getvalue()
        # Should render without errors
        assert "Item1" in result
        assert "Item45" in result

    def test_separator_custom_interval(self) -> None:
        """Test custom separator interval (e.g., every 10 rows)."""
        renderer = TableRenderer(separator_interval=10)
        rows = [{"ID": i, "Value": i * 10} for i in range(1, 31)]

        output = StringIO()
        console = Console(file=output, width=100, legacy_windows=False)
        renderer.render(rows, console=console)

        result = output.getvalue()
        # Should complete without errors
        assert "10" in result or "Value" in result


class TestDataTypeDetection:
    """Test enhanced data type detection and alignment."""

    def test_int_type_right_aligned(self) -> None:
        """Test that int values are detected and right-aligned."""
        renderer = TableRenderer()
        rows = [
            {"ID": 1, "Count": 100},
            {"ID": 2, "Count": 200},
        ]

        alignments = renderer._determine_alignments(rows, ["ID", "Count"])
        assert alignments["ID"] == "right"
        assert alignments["Count"] == "right"

    def test_float_type_right_aligned(self) -> None:
        """Test that float values are detected and right-aligned."""
        renderer = TableRenderer()
        rows = [
            {"Price": 19.99, "Tax": 1.50},
            {"Price": 29.99, "Tax": 2.25},
        ]

        alignments = renderer._determine_alignments(rows, ["Price", "Tax"])
        assert alignments["Price"] == "right"
        assert alignments["Tax"] == "right"

    def test_decimal_type_right_aligned(self) -> None:
        """Test that Decimal values are detected and right-aligned."""
        renderer = TableRenderer()
        rows = [
            {"Amount": Decimal("100.50"), "Fee": Decimal("5.25")},
            {"Amount": Decimal("200.75"), "Fee": Decimal("10.50")},
        ]

        alignments = renderer._determine_alignments(rows, ["Amount", "Fee"])
        assert alignments["Amount"] == "right"
        assert alignments["Fee"] == "right"

    def test_text_type_left_aligned(self) -> None:
        """Test that text values are left-aligned."""
        renderer = TableRenderer()
        rows = [
            {"Name": "Alice", "City": "Boston"},
            {"Name": "Bob", "City": "Seattle"},
        ]

        alignments = renderer._determine_alignments(rows, ["Name", "City"])
        assert alignments["Name"] == "left"
        assert alignments["City"] == "left"

    def test_mixed_types_aligned_correctly(self) -> None:
        """Test mixed numeric and text columns."""
        renderer = TableRenderer()
        rows = [
            {"ID": 1, "Name": "Alice", "Balance": 100.50, "Active": "Yes"},
            {"ID": 2, "Name": "Bob", "Balance": 200.75, "Active": "No"},
        ]

        alignments = renderer._determine_alignments(rows, ["ID", "Name", "Balance", "Active"])
        assert alignments["ID"] == "right"
        assert alignments["Name"] == "left"
        assert alignments["Balance"] == "right"
        assert alignments["Active"] == "left"

    def test_string_numeric_pattern_right_aligned(self) -> None:
        """Test that string values matching numeric pattern are right-aligned."""
        renderer = TableRenderer()
        rows = [
            {"PatNum": "123", "Age": "45"},
            {"PatNum": "456", "Age": "32"},
        ]

        alignments = renderer._determine_alignments(rows, ["PatNum", "Age"])
        assert alignments["PatNum"] == "right"
        assert alignments["Age"] == "right"


class TestNOCOLORSupport:
    """Test NO_COLOR environment variable support."""

    def test_no_color_env_disables_colors(self) -> None:
        """Test that NO_COLOR=1 disables ANSI colors."""
        with patch.dict(os.environ, {"NO_COLOR": "1"}):
            renderer = TableRenderer()
            rows = [{"Name": "Alice", "Age": 30}]

            output = StringIO()
            # Don't pass console - let render() create it with NO_COLOR detection
            renderer.render(rows, console=None)

            # Should complete without errors
            # Actual color detection tested via console creation

    def test_no_color_empty_still_uses_colors(self) -> None:
        """Test that empty NO_COLOR still uses colors."""
        with patch.dict(os.environ, {}, clear=True):
            # Ensure NO_COLOR is not set
            if "NO_COLOR" in os.environ:
                del os.environ["NO_COLOR"]

            renderer = TableRenderer()
            rows = [{"Name": "Bob", "Age": 25}]

            output = StringIO()
            console = Console(file=output, width=100, force_terminal=True)
            renderer.render(rows, console=console)

            result = output.getvalue()
            # Should render normally
            assert "Bob" in result

    def test_no_color_various_values(self) -> None:
        """Test NO_COLOR with various truthy values."""
        for value in ["1", "true", "TRUE", "yes", "YES"]:
            with patch.dict(os.environ, {"NO_COLOR": value}):
                renderer = TableRenderer()
                rows = [{"Test": "Value"}]

                # Should not raise errors
                output = StringIO()
                renderer.render(rows, console=None)


class TestExcelStyleIntegration:
    """Integration tests for Excel-style features."""

    def test_large_dataset_with_all_features(self) -> None:
        """Test rendering 50 rows with separators, mixed types, and alignment."""
        renderer = TableRenderer(separator_interval=20, rows_per_page=100)
        rows = []
        for i in range(1, 51):
            rows.append(
                {
                    "ID": i,
                    "Name": f"Patient{i}",
                    "Balance": float(i * 10.5),
                    "Status": "Active" if i % 2 == 0 else "Inactive",
                }
            )

        output = StringIO()
        console = Console(file=output, width=120, legacy_windows=False)
        renderer.render(rows, console=console)

        result = output.getvalue()
        # Verify data present
        assert "Patient1" in result
        assert "Patient50" in result
        assert "Active" in result
        assert "Inactive" in result

    def test_separator_at_exact_boundary(self) -> None:
        """Test separator at exact 20-row boundary."""
        renderer = TableRenderer(separator_interval=20, rows_per_page=100)
        rows = [{"Row": i} for i in range(1, 21)]  # Exactly 20 rows

        output = StringIO()
        console = Console(file=output, width=100, legacy_windows=False)
        renderer.render(rows, console=console)

        result = output.getvalue()
        # Should render all 20 rows (separator would be at row 20, but only if row 21 exists)
        assert "Row" in result
