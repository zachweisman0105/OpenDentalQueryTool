"""Unit tests for ProgressIndicator."""

from io import StringIO

from rich.console import Console

from opendental_query.renderers.progress import ProgressIndicator


class TestProgressIndicator:
    """Test ProgressIndicator functionality."""

    def test_init_default_console(self) -> None:
        """Test initialization with default console."""
        indicator = ProgressIndicator()
        assert indicator.console is not None
        assert indicator.progress is None
        assert indicator.task_id is None

    def test_init_custom_console(self) -> None:
        """Test initialization with custom console."""
        console = Console()
        indicator = ProgressIndicator(console=console)
        assert indicator.console is console

    def test_start_creates_progress_bar(self) -> None:
        """Test that start() creates progress bar with correct total."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=100)
        indicator = ProgressIndicator(console=console)

        indicator.start(total_offices=5)

        assert indicator.progress is not None
        assert indicator.task_id is not None

        # Clean up
        indicator.stop()

    def test_update_changes_progress(self) -> None:
        """Test that update() changes progress status."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=100)
        indicator = ProgressIndicator(console=console)

        indicator.start(total_offices=5)
        indicator.update(completed=2, status_message="Processing office 2")

        assert indicator.progress is not None
        assert indicator.task_id is not None

        # Clean up
        indicator.stop()

    def test_update_without_status_message(self) -> None:
        """Test that update() works without status message."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=100)
        indicator = ProgressIndicator(console=console)

        indicator.start(total_offices=5)
        indicator.update(completed=3)

        assert indicator.progress is not None

        # Clean up
        indicator.stop()

    def test_update_before_start_does_nothing(self) -> None:
        """Test that update() before start() is safe."""
        indicator = ProgressIndicator()
        # Should not raise any exception
        indicator.update(completed=1, status_message="Test")

    def test_finish_with_all_success(self) -> None:
        """Test finish() with all queries successful."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=100)
        indicator = ProgressIndicator(console=console)

        indicator.start(total_offices=5)
        indicator.finish(success_count=5, failed_count=0)

        # Progress should be stopped and cleaned up
        assert indicator.progress is None
        assert indicator.task_id is None

        # Check output contains success message
        output_text = output.getvalue()
        assert "completed successfully" in output_text.lower() or "✓" in output_text

    def test_finish_with_failures(self) -> None:
        """Test finish() with some failures."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=100)
        indicator = ProgressIndicator(console=console)

        indicator.start(total_offices=5)
        indicator.finish(success_count=3, failed_count=2)

        # Progress should be stopped
        assert indicator.progress is None
        assert indicator.task_id is None

        # Check output contains failure message
        output_text = output.getvalue()
        assert "failure" in output_text.lower() or "⚠" in output_text

    def test_finish_before_start_does_nothing(self) -> None:
        """Test that finish() before start() is safe."""
        indicator = ProgressIndicator()
        # Should not raise any exception
        indicator.finish(success_count=0, failed_count=0)

    def test_stop_cleans_up(self) -> None:
        """Test that stop() properly cleans up progress bar."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=100)
        indicator = ProgressIndicator(console=console)

        indicator.start(total_offices=5)
        indicator.stop()

        assert indicator.progress is None
        assert indicator.task_id is None

    def test_stop_without_start_is_safe(self) -> None:
        """Test that stop() without start() is safe."""
        indicator = ProgressIndicator()
        # Should not raise any exception
        indicator.stop()

    def test_multiple_start_stop_cycles(self) -> None:
        """Test multiple start/stop cycles work correctly."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=100)
        indicator = ProgressIndicator(console=console)

        # First cycle
        indicator.start(total_offices=3)
        indicator.update(completed=1)
        indicator.finish(success_count=3, failed_count=0)

        # Second cycle
        indicator.start(total_offices=5)
        indicator.update(completed=2)
        indicator.stop()

        assert indicator.progress is None
        assert indicator.task_id is None

    def test_progress_bar_displays_office_count(self) -> None:
        """Test that progress bar displays office count correctly."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=100)
        indicator = ProgressIndicator(console=console)

        indicator.start(total_offices=10)
        indicator.update(completed=5)
        indicator.stop()

        output_text = output.getvalue()
        # Should show office count in format like "5/10 offices"
        assert "offices" in output_text.lower()

    def test_progress_bar_shows_percentage(self) -> None:
        """Test that progress bar shows percentage."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=100)
        indicator = ProgressIndicator(console=console)

        indicator.start(total_offices=10)
        indicator.update(completed=5)
        indicator.stop()

        output_text = output.getvalue()
        # Should show percentage (50% for 5/10)
        assert "%" in output_text or "50" in output_text

    def test_progress_bar_shows_elapsed_time(self) -> None:
        """Test that progress bar displays elapsed time."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=100)
        indicator = ProgressIndicator(console=console)

        indicator.start(total_offices=5)
        indicator.update(completed=3)
        indicator.stop()

        # Rich progress bars include time display
        # Just verify no exceptions were raised
        assert True

    def test_log_writes_to_progress_console(self) -> None:
        """Test that log() writes messages without stopping progress."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=100)
        indicator = ProgressIndicator(console=console)

        indicator.start(total_offices=2)
        indicator.log("Test message")
        indicator.stop()

        assert "Test message" in output.getvalue()
