"""Unit tests for ProgressIndicator."""

from io import StringIO

from rich.console import Console

from opendental_query.renderers.progress import ProgressIndicator


class TestProgressIndicator:
    """Test ProgressIndicator functionality without a Rich progress bar."""

    def test_init_default_console(self) -> None:
        """ProgressIndicator should initialise with sensible defaults."""
        indicator = ProgressIndicator()
        assert indicator.console is not None
        assert indicator.progress is None
        assert indicator.task_id is None

    def test_start_does_not_create_progress(self) -> None:
        """start() should reset counters without creating a progress bar."""
        output = StringIO()
        console = Console(file=output, force_terminal=False, color_system=None, highlight=False)
        indicator = ProgressIndicator(console=console)

        indicator.start(total_offices=5)

        assert indicator.progress is None
        assert indicator.task_id is None
        assert output.getvalue() == ""

    def test_update_emits_status_once(self) -> None:
        """update() should emit new status messages and suppress duplicates."""
        output = StringIO()
        console = Console(file=output, force_terminal=False, color_system=None, highlight=False)
        indicator = ProgressIndicator(console=console)

        indicator.start(total_offices=5)
        indicator.update(completed=1, status_message="Processing office 1")
        indicator.update(completed=2, status_message="Processing office 1")
        indicator.update(completed=3, status_message="Processing office 3")

        text = output.getvalue()
        assert text.count("Processing office 1") == 1
        assert "Processing office 3" in text

    def test_update_without_status_is_safe(self) -> None:
        """update() without a status message should be a no-op."""
        indicator = ProgressIndicator()
        indicator.start(total_offices=2)
        indicator.update(completed=1)
        # No exception is success.

    def test_stop_resets_last_status(self) -> None:
        """stop() should allow the same status to be re-emitted later."""
        output = StringIO()
        console = Console(file=output, force_terminal=False, color_system=None, highlight=False)
        indicator = ProgressIndicator(console=console)

        indicator.start(total_offices=5)
        indicator.update(completed=1, status_message="Processing")
        indicator.stop()
        indicator.update(completed=2, status_message="Processing")

        text = output.getvalue()
        assert text.count("Processing") == 2

    def test_finish_success_message(self) -> None:
        """finish() should emit a success summary when there are no failures."""
        output = StringIO()
        console = Console(file=output, force_terminal=False, color_system=None, highlight=False)
        indicator = ProgressIndicator(console=console)

        indicator.start(total_offices=5)
        indicator.finish(success_count=5, failed_count=0)

        text = output.getvalue().lower()
        assert "completed successfully" in text

    def test_finish_failure_message(self) -> None:
        """finish() should emit a warning summary when failures occur."""
        output = StringIO()
        console = Console(file=output, force_terminal=False, color_system=None, highlight=False)
        indicator = ProgressIndicator(console=console)

        indicator.start(total_offices=5)
        indicator.finish(success_count=3, failed_count=2)

        text = output.getvalue().lower()
        assert "failure" in text or "completed with" in text

    def test_finish_before_start_is_safe(self) -> None:
        """finish() should be safe to call before start()."""
        indicator = ProgressIndicator()
        indicator.finish(success_count=0, failed_count=0)
        # No exception is success.

    def test_log_writes_message(self) -> None:
        """log() should always write to the console."""
        output = StringIO()
        console = Console(file=output, force_terminal=False, color_system=None, highlight=False)
        indicator = ProgressIndicator(console=console)

        indicator.log("Test message")

        assert "Test message" in output.getvalue()
