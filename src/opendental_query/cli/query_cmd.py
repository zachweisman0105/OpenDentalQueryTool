"""
CLI command for executing queries across multiple offices.

Provides interactive query interface with:
- SQL input prompt
- Office selection (ALL or comma-separated IDs)
- Query execution with progress tracking
- Table rendering for console display
- CSV export for data persistence
- Audit logging
"""

import sys
import threading

import click
from rich.console import Console
from rich.live import Live
from rich.table import Table

from opendental_query.constants import DEFAULT_CONFIG_DIR
from opendental_query.core.config import ConfigManager
from opendental_query.core.query_engine import QueryEngine
from opendental_query.core.vault import VaultManager
from opendental_query.models.query import OfficeQueryResult, OfficeQueryStatus
from opendental_query.renderers.csv_exporter import CSVExporter
from opendental_query.renderers.progress import ProgressIndicator
from opendental_query.renderers.table import TableRenderer
from opendental_query.utils.audit_logger import AuditLogger
from opendental_query.utils.sql_parser import SQLParser


class LiveRowTracker:
    """Tracks per-office row counts and logs per-second updates."""

    def __init__(
        self,
        *,
        progress_indicator: ProgressIndicator,
        office_ids: list[str],
    ) -> None:
        self._progress_indicator = progress_indicator
        self._office_totals: dict[str, int] = {office_id: 0 for office_id in office_ids}
        self._last_print_totals: dict[str, int] = {office_id: 0 for office_id in office_ids}
        self._active_offices: set[str] = set(office_ids)
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._live: Live | None = None

    def start(self) -> None:
        """Begin background logging if any offices are active."""
        if not self._active_offices:
            return
        self._stop_event.clear()
        live_console = (
            self._progress_indicator.progress.console
            if self._progress_indicator.progress is not None
            else self._progress_indicator.console
        )
        initial_rows, _ = self._snapshot(update_last=False)
        self._live = Live(
            self._render_table(initial_rows),
            console=live_console,
            refresh_per_second=4,
            transient=False,
        )
        self._live.start()
        self._thread = threading.Thread(target=self._run, name="row-tracker", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop background logging."""
        self._stop_event.set()
        thread = self._thread
        if thread and thread.is_alive():
            thread.join(timeout=1.0)
        if self._live is not None:
            # Ensure final snapshot is rendered before stopping
            final_rows, _ = self._snapshot(update_last=False)
            self._live.update(self._render_table(final_rows))
            self._live.stop()
            self._live = None

    def handle_update(self, office_id: str, total_rows: int) -> None:
        """Update running total for an office."""
        with self._lock:
            if office_id in self._office_totals:
                # Ensure totals are monotonic even if callback arrives out of order
                self._office_totals[office_id] = max(total_rows, self._office_totals[office_id])

    def mark_complete(self, office_id: str) -> None:
        """Mark an office as complete to stop further logging."""
        with self._lock:
            self._active_offices.discard(office_id)

    def _run(self) -> None:
        """Background loop emitting per-second row counts."""
        while True:
            rows, has_active = self._snapshot(update_last=True)
            if self._live is not None:
                self._live.update(self._render_table(rows))

            if self._stop_event.wait(timeout=1.0):
                break

            if not has_active:
                break

        # Render one last snapshot to capture final counts
        rows, _ = self._snapshot(update_last=False)
        if self._live is not None:
            self._live.update(self._render_table(rows))

    def _snapshot(self, *, update_last: bool) -> tuple[list[tuple[str, int, int, bool]], bool]:
        """Capture current totals and whether offices remain active."""
        with self._lock:
            rows: list[tuple[str, int, int, bool]] = []
            for office_id in sorted(self._office_totals):
                total = self._office_totals[office_id]
                previous = self._last_print_totals[office_id]
                delta = max(total - previous, 0)
                if update_last:
                    self._last_print_totals[office_id] = total
                rows.append((office_id, total, delta, office_id in self._active_offices))
            has_active = bool(self._active_offices)
        return rows, has_active

    def _render_table(self, rows: list[tuple[str, int, int, bool]]) -> Table:
        """Render a Rich table for the provided row data."""
        table = Table(box=None, show_header=True, header_style="bold cyan")
        table.add_column("Office", style="bold")
        table.add_column("Rows", justify="right")
        table.add_column("Δ/s", justify="right")

        for office_id, total, delta, is_active in rows:
            delta_text = f"+{delta:,}/s"
            style = None if is_active else "dim"
            table.add_row(office_id, f"{total:,}", delta_text, style=style)

        return table


def _execute_single_query(
    *,
    console: Console,
    engine: QueryEngine,
    sql: str,
    selected_offices: list[str],
    office_credentials: dict[str, tuple[str, str]],
    api_base_url: str,
    timeout_seconds: float,
    export_requested: bool,
    allow_export_prompt: bool,
) -> int:
    """Execute a single query run, returning an exit code (0/1/2/130)."""
    progress = ProgressIndicator(console=console)
    console.print(f"\n[cyan]Executing query across {len(selected_offices)} office(s)...[/cyan]\n")
    progress.start(len(selected_offices))

    row_tracker = LiveRowTracker(
        progress_indicator=progress,
        office_ids=selected_offices,
    )
    row_tracker.start()

    result = None
    total_rows_retrieved = 0
    completed_offices = 0

    def _on_office_complete(result: OfficeQueryResult) -> None:
        """Update progress indicator with per-office record counts."""
        nonlocal total_rows_retrieved, completed_offices
        completed_offices += 1

        if result.status == OfficeQueryStatus.SUCCESS:
            total_rows_retrieved += result.row_count
            per_office_message = (
                f"[green]{result.office_id}[/green]: Retrieved {result.row_count:,} row(s)"
            )
            status_message = f"Total rows retrieved: {total_rows_retrieved:,}"
        elif result.status == OfficeQueryStatus.TIMEOUT:
            per_office_message = (
                f"[yellow]{result.office_id}[/yellow]: Timed out after {timeout_seconds}s"
            )
            status_message = f"{completed_offices}/{len(selected_offices)} offices processed"
        else:
            reason = result.error_message or result.status
            per_office_message = f"[red]{result.office_id}[/red]: {reason}"
            status_message = f"{completed_offices}/{len(selected_offices)} offices processed"

        progress.update(completed_offices, status_message=status_message)
        progress.log(per_office_message)
        row_tracker.mark_complete(result.office_id)

    try:
        result = engine.execute(
            sql=sql,
            office_credentials=office_credentials,
            api_base_url=api_base_url,
            timeout_seconds=timeout_seconds,
            progress_callback=_on_office_complete,
            row_progress_callback=row_tracker.handle_update,
        )
    except ValueError as e:
        progress.stop()
        console.print(f"\n[red]Error: Query failed: {e}[/red]")
        return 2
    except KeyboardInterrupt:
        progress.stop()
        console.print("\n[yellow]Warning: Query cancelled by user[/yellow]")
        return 130
    finally:
        row_tracker.stop()
        if result is not None:
            progress.finish(result.successful_count, result.failed_count)

    console.print("\n[cyan]Query completed:[/cyan]")
    console.print(f"  - Total offices: {result.total_offices}")
    console.print(f"  - Successful: {result.successful_count}")
    console.print(f"  - Failed: {result.failed_count}")
    console.print(f"  - Total rows: {len(result.all_rows)}")

    if result.failed_count > 0:
        console.print("\n[yellow]Failed offices:[/yellow]")
        for office_result in result.office_results:
            if office_result.status != "success":
                console.print(
                    f"  ! {office_result.office_id}: "
                    f"[red]{office_result.status}[/red] - {office_result.error_message}",
                )

    if result.all_rows:
        console.print("\n[cyan]Results:[/cyan]\n")
        renderer = TableRenderer(paginate=False)
        renderer.render(result.all_rows, console=console)

        should_export = export_requested
        if not should_export and allow_export_prompt:
            console.print()
            should_export = click.confirm(
                "Export results to CSV? [y/N]",
                default=False,
                show_default=False,
            )

        if should_export:
            console.print("\n[cyan]Exporting to CSV...[/cyan]")
            exporter = CSVExporter()
            try:
                csv_path = exporter.export(result.all_rows)
                console.print(f"[green]Exported to: {csv_path}[/green]")
                console.print(
                    "[yellow]HIPAA Reminder:[/yellow] Store CSV files on encrypted media, limit distribution, and delete when no longer needed."
                )

                audit_logger = AuditLogger()
                audit_logger.log_csv_export(
                    filepath=str(csv_path),
                    row_count=len(result.all_rows),
                    office_count=len(selected_offices),
                )
            except Exception as e:
                console.print(f"[red]CSV export failed: {e}[/red]")
    else:
        console.print("\n[yellow]No results to display[/yellow]")
        if export_requested:
            console.print("[yellow]CSV export skipped because the query returned no rows.[/yellow]")

    audit_logger = AuditLogger()
    audit_logger.log_query_execution(
        query=sql,
        office_ids=selected_offices,
        success_count=result.successful_count,
        failed_count=result.failed_count,
        row_count=len(result.all_rows),
    )

    if result.failed_count == 0:
        return 0
    if result.successful_count > 0:
        return 1
    return 2


@click.command(name="query")
@click.option(
    "--sql",
    "-s",
    help="SQL query to execute (interactive prompt if not provided)",
)
@click.option(
    "--offices",
    "-o",
    help="Comma-separated office IDs, or 'ALL' (interactive prompt if not provided)",
)
@click.option(
    "--timeout",
    "-t",
    type=int,
    default=300,
    help="Timeout per office in seconds (default 300 = 5 minutes)",
)
@click.option(
    "--max-concurrent",
    "-c",
    type=int,
    default=10,
    help="Maximum concurrent office queries (default 10)",
)
@click.option(
    "--export",
    "export_results",
    is_flag=True,
    help="Export results to CSV after execution",
)
@click.pass_context
def query_command(
    ctx: click.Context,
    sql: str | None,
    offices: str | None,
    timeout: int,
    max_concurrent: int,
    export_results: bool,
) -> None:
    """Execute SQL query across multiple offices."""
    console = Console()

    try:
        ctx_obj = ctx.obj or {}
        config_dir = ctx_obj.get("config_dir", DEFAULT_CONFIG_DIR)
        config_manager = ConfigManager(config_dir)
        config = config_manager.load()

        vault_manager = VaultManager(config.vault_path)

        if not vault_manager.is_unlocked():
            password = click.prompt(
                "Enter vault password",
                hide_input=True,
                type=str,
            )

            try:
                vault_manager.unlock(password)
            except ValueError as e:
                console.print(f"[red]Failed to unlock vault: {e}[/red]")
                sys.exit(2)

        interactive_loop = sql is None and offices is None
        current_sql = sql
        current_offices = offices
        overall_exit_code = 0

        while True:
            vault_data = vault_manager.get_vault()

            if not vault_data.offices:
                console.print("[red]No offices configured in vault[/red]")
                console.print(
                    "[yellow]Use 'opendental-query vault add-office' to add offices[/yellow]"
                )
                overall_exit_code = max(overall_exit_code, 2)
                if interactive_loop:
                    if not click.confirm("Retry after configuring offices?", default=False):
                        break
                    current_sql = None
                    current_offices = None
                    continue
                sys.exit(2)

            if current_sql is None:
                console.print(
                    "[cyan]Enter SQL query (multi-line, press Enter on a blank line or Ctrl+D/Ctrl+Z to finish):[/cyan]"
                )
                lines: list[str] = []
                try:
                    while True:
                        line = input()
                        if line == "":
                            if not lines:
                                # Ignore leading blank lines before any SQL is entered
                                continue
                            break
                        lines.append(line)
                except EOFError:
                    pass
                current_sql = "\n".join(lines).strip()

            if not current_sql:
                console.print("[red]No SQL query provided[/red]")
                overall_exit_code = max(overall_exit_code, 1)
                if interactive_loop:
                    current_sql = None
                    continue
                sys.exit(1)

            if not SQLParser.is_read_only(current_sql):
                console.print(
                    "[red]Only read-only SQL statements are permitted (SELECT, SHOW, DESCRIBE, EXPLAIN).[/red]"
                )
                overall_exit_code = max(overall_exit_code, 2)
                if interactive_loop:
                    current_sql = None
                    continue
                sys.exit(2)

            if current_offices is None:
                console.print("\n[cyan]Available offices:[/cyan]")
                for office_id in vault_data.offices.keys():
                    console.print(f"  - {office_id}")
                console.print("\n[cyan]Enter office IDs (comma-separated) or 'ALL':[/cyan]")
                current_offices = input().strip()

            if current_offices.upper() == "ALL":
                selected_offices = list(vault_data.offices.keys())
            else:
                selected_offices = [o.strip() for o in current_offices.split(",") if o.strip()]

            if not selected_offices:
                console.print("[red]No offices selected[/red]")
                overall_exit_code = max(overall_exit_code, 1)
                if interactive_loop:
                    current_offices = None
                    continue
                sys.exit(1)

            invalid_offices = [o for o in selected_offices if o not in vault_data.offices]
            if invalid_offices:
                console.print(f"[red]Invalid office IDs: {', '.join(invalid_offices)}[/red]")
                available = list(vault_data.offices.keys())
                console.print(f"[yellow]Available office IDs: {', '.join(available)}[/yellow]")
                overall_exit_code = max(overall_exit_code, 1)
                if interactive_loop:
                    current_offices = None
                    continue
                sys.exit(1)

            audit_logger = AuditLogger()
            total_available = len(vault_data.offices)
            audit_logger.log(
                "office_selection",
                success=True,
                details={
                    "selected_count": len(selected_offices),
                    "total_available": total_available,
                    "selection_type": "ALL"
                    if len(selected_offices) == total_available
                    else "SUBSET",
                },
            )

            developer_key = vault_data.developer_key
            if not developer_key:
                console.print("[red]No DeveloperKey found in vault[/red]")
                console.print(
                    "[yellow]Re-run 'opendental-query vault init' or 'opendental-query vault update-developer-key' to set it.[/yellow]"
                )
                overall_exit_code = max(overall_exit_code, 2)
                if interactive_loop:
                    break
                sys.exit(2)

            office_credentials = {
                office_id: (developer_key, vault_data.offices[office_id].customer_key)
                for office_id in selected_offices
            }

            engine = QueryEngine(max_concurrent=max_concurrent)
            exit_code = _execute_single_query(
                console=console,
                engine=engine,
                sql=current_sql,
                selected_offices=selected_offices,
                office_credentials=office_credentials,
                api_base_url=config.api_base_url,
                timeout_seconds=float(timeout),
                export_requested=export_results,
                allow_export_prompt=interactive_loop,
            )

            if exit_code == 130:
                overall_exit_code = exit_code
                break

            overall_exit_code = max(overall_exit_code, exit_code)

            if not interactive_loop:
                sys.exit(exit_code)

            if not click.confirm("\nRun another query?", default=False):
                break

            current_sql = None
            current_offices = None

        sys.exit(overall_exit_code)

    except KeyboardInterrupt:
        console.print("\n[yellow]Cancelled by user[/yellow]")
        sys.exit(130)
    except Exception as e:
        console.print(f"\n[red]Unexpected error: {e}[/red]")
        sys.exit(2)
