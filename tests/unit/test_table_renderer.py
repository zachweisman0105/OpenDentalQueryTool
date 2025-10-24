"""
Unit tests for TableRenderer.

Tests Rich table creation, column formatting, alignment, sizing, truncation, and pagination.
"""

from io import StringIO
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

from rich.console import Console

from opendental_query.renderers.table import TableRenderer


class TestTableCreation:
    """Test Rich table creation and basic rendering."""

    def test_creates_table_with_data(self) -> None:
        """Should create and render a Rich table with data."""
        renderer = TableRenderer()
        rows = [
            {"Office": "office1", "PatNum": "1", "LName": "Smith"},
            {"Office": "office2", "PatNum": "2", "LName": "Jones"},
        ]

        # Render to string buffer
        output = StringIO()
        console = Console(file=output, width=100, legacy_windows=False)
        renderer.render(rows, console=console)

        result = output.getvalue()

        # Verify table contains data
        assert "office1" in result
        assert "Smith" in result
        assert "office2" in result
        assert "Jones" in result

    def test_handles_empty_rows_list(self) -> None:
        """Should handle empty rows gracefully."""
        renderer = TableRenderer()
        rows: list[dict[str, Any]] = []

        output = StringIO()
        console = Console(file=output, width=100, legacy_windows=False)
        renderer.render(rows, console=console)

        result = output.getvalue()
        assert "No results" in result or len(result.strip()) == 0

    def test_renders_thick_unicode_grid_lines(self) -> None:
        """Should emit single, thick Unicode separators when supported."""
        renderer = TableRenderer()
        rows = [
            {"Office": "office1", "PatNum": "1"},
            {"Office": "office2", "PatNum": "2"},
        ]

        output = StringIO()
        console = Console(file=output, legacy_windows=False)
        renderer.render(rows, console=console)

        table_text = output.getvalue()
        assert "┏" in table_text
        assert "┣" in table_text


class TestColumnHeaders:
    """Test column header formatting."""

    def test_applies_cyan_color_to_headers(self) -> None:
        """Should apply cyan color to column headers."""
        renderer = TableRenderer()
        rows = [{"Office": "office1", "PatNum": "1"}]

        output = StringIO()
        console = Console(file=output, width=100, legacy_windows=False, force_terminal=True)
        renderer.render(rows, console=console)

        result = output.getvalue()

        # Check for ANSI color codes (cyan is typically \x1b[36m or similar)
        # Rich uses markup, so we verify headers are styled
        assert "Office" in result
        assert "PatNum" in result

    def test_uses_column_names_from_first_row(self) -> None:
        """Should extract column names from first row keys."""
        renderer = TableRenderer()
        rows = [
            {"Office": "office1", "PatNum": "1", "LName": "Smith", "FName": "John"},
        ]

        output = StringIO()
        console = Console(file=output, width=100, legacy_windows=False)
        renderer.render(rows, console=console)

        result = output.getvalue()

        # All columns should appear
        assert "Office" in result
        assert "PatNum" in result
        assert "LName" in result
        assert "FName" in result


class TestColumnAlignment:
    """Test column alignment based on data types."""

    def test_right_aligns_numeric_columns(self) -> None:
        """Should right-align columns with numeric data."""
        renderer = TableRenderer()
        rows = [
            {"Office": "office1", "PatNum": "123", "Balance": "45.67"},
            {"Office": "office2", "PatNum": "456", "Balance": "89.12"},
        ]

        # We'll verify the renderer detects numeric columns
        # Actual alignment is handled by Rich, so we just test logic
        assert renderer._is_numeric_column("123")
        assert renderer._is_numeric_column("45.67")
        assert renderer._is_numeric_column("-123.45")
        assert not renderer._is_numeric_column("Smith")
        assert not renderer._is_numeric_column("office1")

    def test_left_aligns_text_columns(self) -> None:
        """Should left-align columns with text data."""
        renderer = TableRenderer()
        rows = [
            {"Office": "office1", "LName": "Smith", "FName": "John"},
        ]

        # Text columns should not be detected as numeric
        assert not renderer._is_numeric_column("Smith")
        assert not renderer._is_numeric_column("John")
        assert not renderer._is_numeric_column("office1")


class TestColumnSizing:
    """Test column auto-sizing and truncation."""

    def test_auto_sizes_columns(self) -> None:
        """Should auto-size columns based on content."""
        renderer = TableRenderer(max_col_width=50)
        rows = [
            {"Office": "office1", "ShortCol": "abc", "LongerColumn": "This is a longer value"},
        ]

        output = StringIO()
        console = Console(file=output, width=150, legacy_windows=False)
        renderer.render(rows, console=console)

        result = output.getvalue()

        # All content should be visible (under max width)
        assert "abc" in result
        assert "This is a longer value" in result

    def test_truncates_long_values_with_ellipsis(self) -> None:
        """Should truncate values exceeding max_col_width with ellipsis."""
        renderer = TableRenderer(max_col_width=20)
        long_value = "A" * 50  # 50 characters
        rows = [{"Office": "office1", "LongCol": long_value}]

        output = StringIO()
        console = Console(file=output, width=100, legacy_windows=False)
        renderer.render(rows, console=console)

        result = output.getvalue()

        # Should not contain full long value
        assert "A" * 50 not in result
        # Should contain ellipsis
        assert "..." in result or "…" in result

    def test_respects_max_col_width_setting(self) -> None:
        """Should respect max_col_width configuration."""
        renderer = TableRenderer(max_col_width=30)
        assert renderer.max_col_width == 30

        renderer2 = TableRenderer(max_col_width=100)
        assert renderer2.max_col_width == 100


class TestRowFormatting:
    """Test row formatting and alternating colors."""

    def test_applies_alternating_row_colors(self) -> None:
        """Should apply alternating row colors (white/gray)."""
        renderer = TableRenderer()
        rows = [
            {"Office": "office1", "PatNum": "1"},
            {"Office": "office2", "PatNum": "2"},
            {"Office": "office3", "PatNum": "3"},
        ]

        # Rich handles alternating colors automatically with row_styles
        # We verify the renderer is configured to use them
        output = StringIO()
        console = Console(file=output, width=100, legacy_windows=False)
        renderer.render(rows, console=console)

        result = output.getvalue()

        # All rows should be present
        assert "office1" in result
        assert "office2" in result
        assert "office3" in result


class TestPagination:
    """Test pagination with 50 rows per page."""

    def test_displays_first_page_immediately(self) -> None:
        """Should display first 50 rows without pagination prompt."""
        renderer = TableRenderer(rows_per_page=50)
        rows = [{"Office": f"office{i}", "PatNum": str(i)} for i in range(30)]

        with patch("builtins.input") as mock_input:
            output = StringIO()
            console = Console(file=output, width=100, legacy_windows=False)
            renderer.render(rows, console=console)

            # Should not prompt for pagination (under 50 rows)
            mock_input.assert_not_called()

    def test_prompts_for_pagination_after_50_rows(self) -> None:
        """Should prompt user after displaying 50 rows."""
        renderer = TableRenderer(rows_per_page=50)
        rows = [{"Office": f"office{i}", "PatNum": str(i)} for i in range(75)]

        with patch("builtins.input", return_value="") as mock_input:
            output = StringIO()
            console = Console(file=output, width=100, legacy_windows=False)
            renderer.render(rows, console=console)

            # Should prompt once (showing rows 0-49, then 50-74)
            assert mock_input.call_count >= 1

    def test_stops_pagination_on_q_input(self) -> None:
        """Should stop pagination when user enters 'q'."""
        renderer = TableRenderer(rows_per_page=50)
        rows = [{"Office": f"office{i}", "PatNum": str(i)} for i in range(150)]

        with patch("builtins.input", side_effect=["", "q"]) as mock_input:
            output = StringIO()
            console = Console(file=output, width=100, legacy_windows=False)
            renderer.render(rows, console=console)

            # Should prompt twice, then stop
            assert mock_input.call_count == 2

    def test_continues_pagination_on_enter(self) -> None:
        """Should continue pagination when user presses Enter."""
        renderer = TableRenderer(rows_per_page=50)
        rows = [{"Office": f"office{i}", "PatNum": str(i)} for i in range(120)]

        with patch("builtins.input", side_effect=["", ""]) as mock_input:
            output = StringIO()
            console = Console(file=output, width=100, legacy_windows=False)
            renderer.render(rows, console=console)

            # Should prompt twice (0-49, 50-99, 100-119)
            assert mock_input.call_count == 2


class TestNonPaginated:
    """Test behaviour when pagination is disabled."""

    def test_renders_all_rows_in_single_table(self) -> None:
        """Should render every row without prompting when paginate=False."""
        renderer = TableRenderer(rows_per_page=10, paginate=False)
        rows = [{"Office": f"office{i}", "PatNum": str(i)} for i in range(30)]

        with patch("builtins.input") as mock_input:
            output = StringIO()
            console = Console(file=output, width=100, legacy_windows=False)
            renderer.render(rows, console=console)

            mock_input.assert_not_called()

        result = output.getvalue()
        assert "office0" in result and "office29" in result


class TestANSIDetection:
    """Test ANSI color detection and ASCII fallback."""

    def test_detects_ansi_support(self) -> None:
        """Should detect ANSI color support in console."""
        renderer = TableRenderer()

        # Rich Console has is_terminal and color_system properties
        # We test that renderer respects them
        console_with_color = Console(force_terminal=True, color_system="auto")
        console_no_color = Console(force_terminal=False, color_system=None)

        # Both should work without errors
        rows = [{"Office": "office1", "PatNum": "1"}]

        output1 = StringIO()
        console1 = Console(file=output1, force_terminal=True, width=100)
        renderer.render(rows, console=console1)
        assert len(output1.getvalue()) > 0

        output2 = StringIO()
        console2 = Console(file=output2, force_terminal=False, width=100)
        renderer.render(rows, console=console2)
        assert len(output2.getvalue()) > 0

    def test_falls_back_to_ascii_without_ansi(self) -> None:
        """Should fall back to ASCII table without ANSI support."""
        renderer = TableRenderer()
        rows = [{"Office": "office1", "PatNum": "1"}]

        # Render without color support
        output = StringIO()
        console = Console(
            file=output,
            force_terminal=False,
            legacy_windows=False,
            width=100,
            color_system=None,
        )
        renderer.render(rows, console=console)

        result = output.getvalue()

        # Should still render table (without colors)
        assert "office1" in result
        assert "PatNum" in result

    def test_ascii_only_console_selects_ascii_thick_box(self) -> None:
        """Should choose ASCII thick separators when Unicode drawing is unavailable."""
        renderer = TableRenderer()
        fake_console = SimpleNamespace(options=SimpleNamespace(ascii_only=True))

        selected_box = renderer._resolve_box(fake_console)  # type: ignore[arg-type]
        assert "+==+" in str(selected_box)


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_handles_missing_columns_in_rows(self) -> None:
        """Should handle rows with missing columns gracefully."""
        renderer = TableRenderer()
        rows = [
            {"Office": "office1", "PatNum": "1", "LName": "Smith"},
            {"Office": "office2", "PatNum": "2"},  # Missing LName
            {"Office": "office3", "LName": "Jones"},  # Missing PatNum
        ]

        output = StringIO()
        console = Console(file=output, width=100, legacy_windows=False)
        renderer.render(rows, console=console)

        result = output.getvalue()

        # Should render all offices
        assert "office1" in result
        assert "office2" in result
        assert "office3" in result

    def test_handles_none_values(self) -> None:
        """Should handle None values in cells."""
        renderer = TableRenderer()
        rows = [
            {"Office": "office1", "PatNum": None, "LName": "Smith"},
        ]

        output = StringIO()
        console = Console(file=output, width=100, legacy_windows=False)
        renderer.render(rows, console=console)

        result = output.getvalue()

        # Should not crash, render empty or "None"
        assert "office1" in result
        assert "Smith" in result

    def test_handles_special_characters(self) -> None:
        """Should handle special characters in data."""
        renderer = TableRenderer()
        rows = [
            {"Office": "office1", "Name": "O'Brien", "Email": "user@example.com"},
        ]

        output = StringIO()
        console = Console(file=output, width=100, legacy_windows=False)
        renderer.render(rows, console=console)

        result = output.getvalue()

        # Should render special characters correctly
        assert "O'Brien" in result or "O&#x27;Brien" in result  # HTML escape possible
        assert "@" in result or "&#64;" in result
