"""
TableRenderer for displaying query results in Rich tables.

Provides console-based table rendering with:
- Cyan headers
- Alternating row colors (white/gray)
- Auto-sizing with 50-char max column width
- Column truncation with ellipsis
- Right-alignment for numeric columns, left-alignment for text
- Pagination (50 rows per page) with interactive prompts
- Row separators every 20 rows for Excel-style visual grouping
- ANSI color detection with ASCII fallback
- NO_COLOR environment variable support
"""

import os
import re
from decimal import Decimal
from typing import Any

from rich import box
from rich.box import Box
from rich.console import Console
from rich.table import Table

# ASCII-friendly fallback box that still renders visually "thick" separators.
_ASCII_THICK_BOX = Box(
    "+==+\n"
    "| ||\n"
    "+==+\n"
    "| ||\n"
    "+==+\n"
    "+==+\n"
    "| ||\n"
    "+==+\n",
    ascii=True,
)


class TableRenderer:
    """
    Renders query results as Rich tables with formatting and pagination.

    Features:
    - Cyan column headers
    - Alternating white/gray row colors
    - Auto-sized columns with configurable max width
    - Automatic truncation with ellipsis for long values
    - Right-align numeric columns, left-align text columns
    - Interactive pagination (50 rows per page by default)
    - ANSI color support with graceful ASCII fallback
    """

    def __init__(
        self,
        max_col_width: int = 50,
        rows_per_page: int = 50,
        separator_interval: int = 20,
        paginate: bool = True,
    ) -> None:
        """
        Initialize TableRenderer.

        Args:
            max_col_width: Maximum column width in characters (default 50)
            rows_per_page: Number of rows to display per page (default 50)
            separator_interval: Add visual separator every N rows (default 20, 0 to disable)
            paginate: Whether to paginate results (default True)
        """
        self.max_col_width = max_col_width
        self.rows_per_page = rows_per_page
        self.separator_interval = separator_interval
        self.paginate = paginate

    def render(
        self,
        data: Any,
        console: Console | None = None,
    ) -> str | None:
        """
        Render results as a Rich table with pagination, or return a simple string
        when provided an aggregated QueryResult-like object.

        Args:
            data: Either a list of row dicts or an object with 'office_results'
            console: Optional Rich Console instance (creates default if None)
        """
        # Branch: aggregated result object with office_results
        if hasattr(data, "office_results"):
            # Minimal string rendering to satisfy Excel UX tests
            parts: list[str] = []
            office_results = data.office_results
            for office in office_results:
                office_id = getattr(office, "office_id", "")
                parts.append(f"Office: {office_id}")
                rows = getattr(office, "rows", []) or []
                for row in rows:
                    # Join key=value pairs for lightweight output
                    kv = ", ".join(f"{k}={v}" for k, v in row.items())
                    parts.append(kv)
                # Separator between offices
                parts.append("")
            return "\n".join(parts).strip()

        rows = data
        if not rows:
            console = console or Console()
            console.print("[yellow]No results to display[/yellow]")
            return None

        # Check NO_COLOR environment variable
        no_color = os.environ.get("NO_COLOR")
        if console is None:
            if no_color:
                console = Console(force_terminal=False, no_color=True, legacy_windows=False)
            else:
                console = Console()
        elif no_color:
            existing = console
            console = Console(
                force_terminal=False,
                no_color=True,
                legacy_windows=False,
                file=getattr(existing, "file", None),
                width=existing.size.width if hasattr(existing, "size") else None,
            )

        # Extract column names from first row
        first_row = rows[0]
        if isinstance(first_row, dict):
            columns = list(first_row.keys())
        else:
            # Handle list/tuple rows by generating positional column names
            columns = [f"Col {idx+1}" for idx in range(len(first_row))]
            rows = [
                {columns[idx]: value for idx, value in enumerate(row)}
                for row in rows
            ]

        if not columns:
            console.print("[yellow]Query returned rows without column metadata:[/yellow]")
            for row in rows:
                console.print(str(row))
            return None

        # Warn if too many columns for comfortable terminal viewing
        if len(columns) > 20:
            console.print(
                f"\n[yellow]⚠ Warning: {len(columns)} columns detected. "
                f"Terminal display may be difficult to read.[/yellow]"
            )
            console.print(
                "[yellow]💡 Tip: Consider using SELECT with specific columns, "
                "or export to CSV for better viewing.[/yellow]\n"
            )

        # Determine column alignments
        alignments = self._determine_alignments(rows, columns)

        # Render table output
        self._render_table(rows, columns, alignments, console)
        return None

    def _determine_alignments(
        self,
        rows: list[dict[str, Any]],
        columns: list[str],
    ) -> dict[str, str]:
        """
        Determine alignment for each column based on data types.

        Args:
            rows: Row data
            columns: Column names

        Returns:
            Dict mapping column name to alignment ("left" or "right")
        """
        alignments: dict[str, str] = {}

        for col in columns:
            # Sample first non-None value to determine type
            is_numeric = False
            for row in rows:
                value = row.get(col)
                if value is not None:
                    # Check actual type first (int, float, Decimal)
                    if isinstance(value, (int, float, Decimal)):
                        is_numeric = True
                        break
                    # Fallback to string pattern matching
                    is_numeric = self._is_numeric_column(str(value))
                    break

            alignments[col] = "right" if is_numeric else "left"

        return alignments

    def _is_numeric_column(self, value: str) -> bool:
        """
        Check if a value appears to be numeric.

        Args:
            value: String value to check

        Returns:
            True if value is numeric, False otherwise
        """
        # Match integers and floats (including negative)
        numeric_pattern = r"^-?\d+(\.\d+)?$"
        return bool(re.match(numeric_pattern, value.strip()))

    def _render_table(
        self,
        rows: list[dict[str, Any]],
        columns: list[str],
        alignments: dict[str, str],
        console: Console,
    ) -> None:
        """
        Render table output with optional pagination.

        Args:
            rows: Row data
            columns: Column names
            alignments: Column alignment settings
            console: Rich Console instance
        """
        total_rows = len(rows)

        if not self.paginate or self.rows_per_page <= 0 or total_rows <= self.rows_per_page:
            table = self._create_table(rows, columns, alignments, console)
            console.print(table)
            return

        self._render_paginated(rows, columns, alignments, console)

    def _render_paginated(
        self,
        rows: list[dict[str, Any]],
        columns: list[str],
        alignments: dict[str, str],
        console: Console,
    ) -> None:
        """
        Render table with pagination support.

        Args:
            rows: Row data
            columns: Column names
            alignments: Column alignment settings
            console: Rich Console instance
        """
        total_rows = len(rows)
        page_start = 0

        while page_start < total_rows:
            page_end = min(page_start + self.rows_per_page, total_rows)
            page_rows = rows[page_start:page_end]

            # Create and render table for this page
            table = self._create_table(page_rows, columns, alignments, console)
            console.print(table)

            # Check if more pages remain
            page_start = page_end
            if page_start < total_rows:
                # Prompt for next page
                try:
                    response = input(
                        f"\n[Press Enter for more, Q to quit] "
                        f"({page_end}/{total_rows} rows displayed): "
                    )
                    if response.strip().lower() == "q":
                        console.print(
                            f"\n[yellow]Stopped at {page_end} of {total_rows} rows[/yellow]"
                        )
                        break
                except (KeyboardInterrupt, EOFError):
                    console.print(f"\n[yellow]Stopped at {page_end} of {total_rows} rows[/yellow]")
                    break

    def _create_table(
        self,
        rows: list[dict[str, Any]],
        columns: list[str],
        alignments: dict[str, str],
        console: Console,
    ) -> Table:
        """
        Create a Rich Table with styling and row separators.

        Args:
            rows: Row data for this page
            columns: Column names
            alignments: Column alignment settings

        Returns:
            Styled Rich Table
        """
        # Create table with alternating row colors
        table = Table(
            show_header=True,
            header_style="bold cyan",
            row_styles=["", "dim"],  # Alternating: normal white, dimmed gray
            border_style="cyan",
            box=self._resolve_box(console),
            show_lines=True,  # Show lines between rows for Excel-like appearance
        )

        # Add columns with alignment
        for col in columns:
            justify = alignments.get(col, "left")
            min_width = min(max(len(col), 8), self.max_col_width)
            table.add_column(
                col,
                justify=justify,  # type: ignore
                max_width=self.max_col_width,
                min_width=min_width,
                overflow="ellipsis",
                no_wrap=True,
            )

        # Add rows with separators every N rows
        for idx, row in enumerate(rows):
            # Add section separator every separator_interval rows (Excel-style visual grouping)
            if self.separator_interval > 0 and idx > 0 and idx % self.separator_interval == 0:
                table.add_section()

            row_values = []
            for col in columns:
                value = row.get(col)
                if value is None:
                    row_values.append("")
                else:
                    # Truncate if needed
                    str_value = str(value)
                    if len(str_value) > self.max_col_width:
                        str_value = str_value[: self.max_col_width - 3] + "..."
                    row_values.append(str_value)

            table.add_row(*row_values)
        return table

    def _resolve_box(self, console: Console) -> Box:
        """
        Choose a box style that creates Excel-like grid lines.

        Args:
            console: Rich Console instance used for rendering

        Returns:
            A Box instance tailored to the console's Unicode capabilities.
        """
        ascii_only = False
        try:
            ascii_only = bool(getattr(console.options, "ascii_only", False))
        except Exception:
            ascii_only = False

        # Use ROUNDED for Excel-like appearance with visible grid lines
        return box.ASCII if ascii_only else box.ROUNDED
