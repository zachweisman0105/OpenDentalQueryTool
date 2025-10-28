"""
CLI command for executing queries across multiple offices.

Provides interactive query interface with:
- SQL input prompt
- Office selection (ALL or comma-separated IDs)
- Query execution with progress tracking
- Table rendering for console display
- Excel export for data persistence
- Audit logging
"""

import os
import subprocess
import sys
import threading
from pathlib import Path

import click
from rich.console import Console
from rich.live import Live
from rich.table import Table

from opendental_query.constants import (
    DEFAULT_CONFIG_DIR,
    EXIT_INVALID_ARGS,
    EXIT_VAULT_AUTH_FAILED,
    EXIT_VAULT_LOCKED,
    MAX_PASSWORD_ATTEMPTS,
)
from opendental_query.core.config import ConfigManager
from opendental_query.core.query_engine import QueryEngine
from opendental_query.core.vault import VaultManager
from opendental_query.models.query import OfficeQueryResult, OfficeQueryStatus
from opendental_query.renderers.excel_exporter import ExcelExporter
from opendental_query.renderers.progress import ProgressIndicator
from opendental_query.renderers.table import TableRenderer
from opendental_query.utils.audit_logger import AuditLogger
from opendental_query.utils.saved_queries import SavedQuery, SavedQueryLibrary


def _open_workbook_with_default_app(workbook_path: Path, console: Console) -> None:
    """Attempt to open the exported workbook with the system default application."""
    try:
        if sys.platform.startswith("win"):
            startfile = getattr(os, "startfile", None)
            if startfile:
                startfile(str(workbook_path))
            else:
                raise OSError("os.startfile not available on this platform")
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(workbook_path)])
        else:
            subprocess.Popen(["xdg-open", str(workbook_path)])
    except Exception as exc:  # pragma: no cover - best effort
        console.print(f"[yellow]Warning: Unable to open Excel workbook automatically: {exc}[/yellow]")


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
    saved_query_name: str | None,
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
                "Export results to Excel workbook? [y/N]",
                default=False,
                show_default=False,
            )

        if should_export:
            console.print("\n[cyan]Exporting to Excel...[/cyan]")
            exporter = ExcelExporter()
            try:
                workbook_path = exporter.export(result.all_rows)
                console.print(f"[green]Exported to: {workbook_path}[/green]")
                console.print(
                    "[yellow]HIPAA Reminder:[/yellow] Store Excel files on encrypted media, limit distribution, and delete when no longer needed."
                )

                audit_logger = AuditLogger()
                audit_logger.log_excel_export(
                    filepath=str(workbook_path),
                    row_count=len(result.all_rows),
                    office_count=len(selected_offices),
                )
                _open_workbook_with_default_app(workbook_path, console)
            except Exception as e:
                console.print(f"[red]Excel export failed: {e}[/red]")
    else:
        console.print("\n[yellow]No results to display[/yellow]")
        if export_requested:
            console.print("[yellow]Excel export skipped because the query returned no rows.[/yellow]")

    audit_logger = AuditLogger()
    audit_logger.log_query_execution(
        query=sql,
        office_ids=selected_offices,
        success_count=result.successful_count,
        failed_count=result.failed_count,
        row_count=len(result.all_rows),
    )

    if saved_query_name is not None:
        try:
            audit_logger.log(
                "saved_query_run",
                success=result.failed_count == 0,
                details={
                    "name": saved_query_name,
                    "row_count": len(result.all_rows),
                    "office_count": len(selected_offices),
                },
            )
        except Exception:
            pass

    if result.failed_count == 0:
        return 0
    if result.successful_count > 0:
        return 1
    return 2


@click.command(name="query")
@click.option(
    "--saved-query",
    "-S",
    help="Execute a saved query by name.",
)
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
    help="Export results to an Excel workbook after execution",
)
@click.pass_context
def query_command(
    ctx: click.Context,
    saved_query: str | None,
    sql: str | None,
    offices: str | None,
    timeout: int,
    max_concurrent: int,
    export_results: bool,
) -> None:
    """Execute SQL query across multiple offices."""
    console = Console()
    vault_manager: VaultManager | None = None
    unlocked_by_command = False
    initially_unlocked = False

    if saved_query and sql:
        console.print("[red]Provide either --sql or --saved-query, not both.[/red]")
        sys.exit(EXIT_INVALID_ARGS)

    try:
        ctx_obj = ctx.obj or {}
        config_dir = ctx_obj.get("config_dir", DEFAULT_CONFIG_DIR)
        config_manager = ConfigManager(config_dir)
        config = config_manager.load()

        saved_query_record: SavedQuery | None = None
        saved_query_library = SavedQueryLibrary(config_dir)
        resolved_sql = sql
        resolved_offices = offices
        if saved_query:
            try:
                saved_query_record = saved_query_library.get_query(saved_query)
            except KeyError:
                console.print(f"[red]Saved query '{saved_query}' not found.[/red]")
                sys.exit(EXIT_INVALID_ARGS)

            console.print(f"[cyan]Running saved query '{saved_query_record.name}'.[/cyan]")
            resolved_sql = saved_query_record.sql
            if resolved_offices is None:
                if saved_query_record.default_offices == ["ALL"]:
                    resolved_offices = "ALL"
                elif saved_query_record.default_offices:
                    resolved_offices = ",".join(saved_query_record.default_offices)
            try:
                audit_logger = AuditLogger()
                audit_logger.log(
                    "saved_query_load",
                    success=True,
                    details={
                        "name": saved_query_record.name,
                        "has_default_offices": bool(saved_query_record.default_offices),
                    },
                )
            except Exception:
                pass

        saved_query_mode = saved_query_record is not None

        vault_manager = VaultManager(config.vault_path)
        try:
            vault_manager.configure_auto_lock(config.vault_auto_lock_seconds)
        except Exception as exc:
            console.print(f"[yellow]Warning: Invalid auto-lock configuration: {exc}[/yellow]")

        initially_unlocked = vault_manager.is_unlocked()
        unlocked_by_command = False

        if not initially_unlocked:
            attempts_remaining = MAX_PASSWORD_ATTEMPTS
            while attempts_remaining > 0 and not vault_manager.is_unlocked():
                prompt_label = "Enter vault password"
                if attempts_remaining < MAX_PASSWORD_ATTEMPTS:
                    prompt_label = (
                        f"Re-enter vault password ({attempts_remaining} attempt(s) remaining)"
                    )

                password = click.prompt(
                    prompt_label,
                    hide_input=True,
                    type=str,
                )

                try:
                    unlocked = vault_manager.unlock(password)
                    if unlocked:
                        unlocked_by_command = True
                        break
                except ValueError as e:
                    message = str(e)
                    console.print(f"[red]{message}[/red]")
                    lowered = message.lower()
                    if "locked due to failed attempts" in lowered or "locked due to failed" in lowered:
                        sys.exit(EXIT_VAULT_LOCKED)
                    sys.exit(EXIT_VAULT_AUTH_FAILED)
                finally:
                    # Drop password reference as soon as possible
                    password = ""

                attempts_remaining -= 1
                if vault_manager.is_unlocked():
                    unlocked_by_command = True
                    break
                if attempts_remaining > 0:
                    console.print(
                        f"[yellow]Invalid password. {attempts_remaining} attempt(s) remaining.[/yellow]"
                    )

            if not vault_manager.is_unlocked():
                console.print("[red]Maximum password attempts reached. Vault remains locked.[/red]")
                sys.exit(EXIT_VAULT_AUTH_FAILED)

        if saved_query_mode:
            interactive_loop = resolved_offices is None
        else:
            interactive_loop = resolved_sql is None and resolved_offices is None
        current_sql = resolved_sql
        current_offices = resolved_offices
        overall_exit_code = 0
        office_prompt_confirms_remaining = 0 if saved_query_mode else (3 if interactive_loop else 0)

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
                    office_prompt_confirms_remaining = 3
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

            if current_offices is None:
                if interactive_loop and office_prompt_confirms_remaining > 0:
                    while office_prompt_confirms_remaining > 0 and current_offices is None:
                        try:
                            response = input()
                        except EOFError:
                            response = ""
                        stripped = response.strip()
                        if stripped:
                            current_offices = stripped
                            break
                        office_prompt_confirms_remaining -= 1
                    if current_offices is None and office_prompt_confirms_remaining > 0:
                        continue

                if current_offices is None:
                    console.print("\n[cyan]Available offices:[/cyan]")
                    for office_id in vault_data.offices.keys():
                        console.print(f"  - {office_id}")
                    prompt_text = "\n[cyan]Enter office IDs (comma-separated) or 'ALL':[/cyan]"
                    if saved_query:
                        prompt_text = "\n[cyan]Enter office IDs for saved query (comma-separated) or 'ALL':[/cyan]"
                    console.print(prompt_text)
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
                saved_query_name=saved_query_record.name if saved_query_record else None,
            )

            if exit_code == 130:
                overall_exit_code = exit_code
                break

            overall_exit_code = max(overall_exit_code, exit_code)

            if not interactive_loop:
                sys.exit(exit_code)

            if not click.confirm("\nRun another query?", default=False):
                break

            if saved_query_mode:
                saved_query_mode = False
            current_sql = None
            interactive_loop = True
            current_offices = None
            office_prompt_confirms_remaining = 3

        sys.exit(overall_exit_code)

    except KeyboardInterrupt:
        console.print("\n[yellow]Cancelled by user[/yellow]")
        sys.exit(130)
    except Exception as e:
        console.print(f"\n[red]Unexpected error: {e}[/red]")
        sys.exit(2)
    finally:
        if vault_manager is not None and unlocked_by_command and vault_manager.is_unlocked():
            try:
                vault_manager.lock()
            except Exception as exc:  # pragma: no cover - best effort cleanup
                console.print(f"[yellow]Warning: Failed to lock vault cleanly: {exc}[/yellow]")
