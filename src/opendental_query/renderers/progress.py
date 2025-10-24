"""
Progress indicator for query execution.

Displays real-time progress of multi-office query execution using Rich progress bars.
"""

from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskID,
    TextColumn,
    TimeElapsedColumn,
)


class ProgressIndicator:
    """
    Displays progress of multi-office query execution.

    Features:
    - Spinner animation for active queries
    - Progress bar showing completion percentage
    - Per-office status tracking (querying, success, error, timeout)
    - Time elapsed display
    - Concurrent office count
    """

    def __init__(self, console: Console | None = None) -> None:
        """
        Initialize ProgressIndicator.

        Args:
            console: Optional Rich Console instance
        """
        self.console = console or Console()
        encoding = (self.console.encoding or "").lower()
        self._supports_unicode = "utf" in encoding
        self.progress: Progress | None = None
        self.task_id: TaskID | None = None

    def start(self, total_offices: int) -> None:
        """
        Start progress tracking.

        Args:
            total_offices: Total number of offices to query
        """
        spinner = SpinnerColumn() if self._supports_unicode else SpinnerColumn(spinner_name="line")

        columns = [
            spinner,
            TextColumn("[progress.description]{task.description}"),
        ]

        if self._supports_unicode:
            columns.extend(
                [
                    BarColumn(),
                    TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                    TextColumn("•"),
                ]
            )
        else:
            columns.append(TextColumn("{task.percentage:>3.0f}%"))

        columns.append(TextColumn("{task.completed}/{task.total} offices"))
        columns.append(TimeElapsedColumn())

        self.progress = Progress(*columns, console=self.console)

        self.progress.start()
        self.task_id = self.progress.add_task(
            "[cyan]Executing queries...",
            total=total_offices,
        )

    def update(self, completed: int, status_message: str | None = None) -> None:
        """
        Update progress.

        Args:
            completed: Number of offices completed
            status_message: Optional status message to display
        """
        if self.progress is None or self.task_id is None:
            return

        description = "[cyan]Executing queries..."
        if status_message:
            description = f"[cyan]{status_message}"

        self.progress.update(
            self.task_id,
            completed=completed,
            description=description,
        )

    def finish(self, success_count: int, failed_count: int) -> None:
        """
        Finish progress tracking and display summary.

        Args:
            success_count: Number of successful queries
            failed_count: Number of failed queries
        """
        if self.progress is None or self.task_id is None:
            return

        # Update final status
        if failed_count == 0:
            if self._supports_unicode:
                description = "[green]✓ All queries completed successfully"
            else:
                description = "[green]All queries completed successfully"
        else:
            if self._supports_unicode:
                description = (
                    f"[yellow]⚠ Completed with {failed_count} failure(s), {success_count} success(es)"
                )
            else:
                description = (
                    f"[yellow]Completed with {failed_count} failure(s), {success_count} success(es)"
                )

        self.progress.update(
            self.task_id,
            description=description,
        )

        self.progress.stop()
        self.progress = None
        self.task_id = None

    def stop(self) -> None:
        """Stop progress tracking without summary."""
        if self.progress is not None:
            self.progress.stop()
            self.progress = None
            self.task_id = None

    def log(self, message: str) -> None:
        """
        Write a message without disrupting the progress display.

        Args:
            message: Text to display (Rich markup supported)
        """
        target_console = self.progress.console if self.progress is not None else self.console
        target_console.print(message)
