"""
Progress indicator for query execution.

Provides lightweight textual updates without displaying a Rich progress bar.
"""

from rich.console import Console


class ProgressIndicator:
    """
    Tracks overall query execution progress without rendering a progress bar.

    The class keeps the same interface so callers can continue to invoke
    start/update/finish, but the implementation now emits simple textual
    messages instead of managing Rich progress components.
    """

    def __init__(self, console: Console | None = None) -> None:
        """
        Initialize ProgressIndicator.

        Args:
            console: Optional Rich Console instance
        """
        self.console = console or Console()
        self.progress = None
        self.task_id = None
        self._total_offices: int = 0
        self._completed_offices: int = 0
        self._last_status: str | None = None

    def start(self, total_offices: int) -> None:
        """
        Start progress tracking.

        Args:
            total_offices: Total number of offices to query
        """
        self._total_offices = max(total_offices, 0)
        self._completed_offices = 0
        self._last_status = None

    def update(self, completed: int, status_message: str | None = None) -> None:
        """
        Update internal counters and optionally emit a status message.

        Args:
            completed: Number of offices completed
            status_message: Optional status message to display
        """
        self._completed_offices = max(0, completed)
        if status_message and status_message != self._last_status:
            # Avoid repeating the same status message back-to-back
            self._last_status = status_message
            self.console.print(f"[cyan]{status_message}[/cyan]")

    def finish(self, success_count: int, failed_count: int) -> None:
        """
        Finish progress tracking and display summary.

        Args:
            success_count: Number of successful queries
            failed_count: Number of failed queries
        """
        self._completed_offices = self._total_offices

        if failed_count == 0:
            self.console.print("[green]All queries completed successfully[/green]")
        else:
            self.console.print(
                f"[yellow]Completed with {failed_count} failure(s) and {success_count} success(es)[/yellow]"
            )

    def stop(self) -> None:
        """Stop progress tracking without summary."""
        # Nothing to clean up, but keep for API compatibility.
        self._last_status = None

    def log(self, message: str) -> None:
        """
        Write a message to the console.

        Args:
            message: Text to display (Rich markup supported)
        """
        self.console.print(message)
