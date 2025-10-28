"""CLI commands for managing encrypted query history storage."""

from __future__ import annotations

import getpass
from pathlib import Path
from typing import Any

import click

from opendental_query.constants import (
    DEFAULT_CONFIG_DIR,
    EXIT_VAULT_AUTH_FAILED,
    MAX_PASSWORD_ATTEMPTS,
)
from opendental_query.core.config import ConfigManager
from opendental_query.core.query_engine import QueryEngine
from opendental_query.core.vault import VaultManager
from opendental_query.utils.query_history_db import QueryHistoryDatabase
from opendental_query.utils.saved_queries import SavedQuery, SavedQueryLibrary

SQL_PREVIEW_LIMIT = 200


def _preview_sql(sql_text: str, limit: int = SQL_PREVIEW_LIMIT) -> tuple[str, bool]:
    """Return a trimmed SQL preview and flag if it was truncated."""
    normalized = " ".join(sql_text.split())
    if len(normalized) <= limit:
        return normalized, False
    preview = normalized[: limit - 3].rstrip()
    return preview + "...", True


@click.group(name="history")
@click.pass_context
def history_group(ctx: click.Context) -> None:
    """Manage encrypted query history storage."""
    ctx.ensure_object(dict)


@history_group.command(name="run")
@click.option("--sql", "-s", help="SQL query to execute")
@click.option("--saved-query", "-S", help="Name of saved query to execute")
@click.option("--offices", "-o", help="Comma separated office IDs or 'ALL'")
@click.option("--timeout", type=int, default=300, help="Timeout per office (seconds)")
@click.option("--max-concurrent", type=int, default=10, help="Maximum concurrent offices")
@click.pass_context
def run_query_history(
    ctx: click.Context,
    sql: str | None,
    saved_query: str | None,
    offices: str | None,
    timeout: int,
    max_concurrent: int,
) -> None:
    """Execute a query and record the result set in the history database."""
    ctx.ensure_object(dict)
    config_dir: Path = ctx.obj.get("config_dir", DEFAULT_CONFIG_DIR)

    if sql and saved_query:
        raise click.UsageError("Provide only one of --sql or --saved-query")

    library = SavedQueryLibrary(config_dir)
    saved_query_record: SavedQuery | None = None
    sql_text: str | None = None

    if saved_query:
        selection = saved_query.strip()
        if not selection:
            raise click.ClickException("Saved query name cannot be empty")
        try:
            saved_query_record = library.get_query(selection)
        except KeyError as exc:
            raise click.ClickException(str(exc)) from exc
        sql_text = saved_query_record.sql
    elif sql:
        sql_text = sql.strip()
        if not sql_text:
            raise click.ClickException("SQL text cannot be empty")
    else:
        entry, matched_saved = _select_history_entry(
            config_dir,
            library,
            "Select table to update (number or name)",
        )
        saved_query_record = matched_saved
        sql_text = entry["query_text"]

    assert sql_text is not None

    config_manager = ConfigManager(config_dir)
    config = config_manager.load()

    vault_manager = VaultManager(config.vault_path)
    try:
        vault_manager.configure_auto_lock(config.vault_auto_lock_seconds)
    except Exception as exc:  # pragma: no cover - warning only
        click.echo(f"Warning: Invalid auto-lock configuration: {exc}")

    _ensure_vault_unlocked(ctx, vault_manager)

    vault_data = vault_manager.get_vault()
    if not vault_data.offices:
        raise click.ClickException("No offices configured in vault")

    if offices is None and saved_query_record and saved_query_record.default_offices:
        offices = (
            "ALL"
            if saved_query_record.default_offices == ["ALL"]
            else ",".join(saved_query_record.default_offices)
        )

    if offices is None:
        click.echo("\nAvailable offices:")
        for office_id in vault_data.offices.keys():
            click.echo(f"  - {office_id}")
        offices = click.prompt("Enter office IDs (comma-separated) or 'ALL'")

    if offices.upper() == "ALL":
        selected_offices = list(vault_data.offices.keys())
    else:
        selected_offices = [office.strip() for office in offices.split(",") if office.strip()]

    invalid_offices = [office for office in selected_offices if office not in vault_data.offices]
    if invalid_offices:
        raise click.ClickException("Invalid office IDs: " + ", ".join(invalid_offices))

    developer_key = vault_data.developer_key
    if not developer_key:
        raise click.ClickException("No DeveloperKey found in vault")

    office_credentials = {
        office_id: (developer_key, vault_data.offices[office_id].customer_key)
        for office_id in selected_offices
    }

    engine = QueryEngine(max_concurrent=max_concurrent)
    result = engine.execute(
        sql=sql_text,
        office_credentials=office_credentials,
        api_base_url=config.api_base_url,
        timeout_seconds=float(timeout),
    )

    if result.failed_count > 0 and result.successful_count == 0:
        raise click.ClickException("Query failed for all offices")

    if not result.all_rows:
        click.echo("Query returned no rows; nothing recorded.")
        return

    columns = list(result.all_rows[0].keys())
    rows_to_store = [{col: row.get(col) for col in columns} for row in result.all_rows]

    db = QueryHistoryDatabase(config_dir)
    metadata: dict[str, Any] = {
        "offices": selected_offices,
        "username": getpass.getuser(),
        "saved_query": saved_query_record.name if saved_query_record else None,
    }
    metadata = {key: value for key, value in metadata.items() if value}

    try:
        inserted = db.record_query_result(
            query_text=sql_text,
            columns=columns,
            rows=rows_to_store,
            source="query-run",
            metadata=metadata,
        )
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc

    click.echo(
        f"Recorded {inserted} row(s) for query history (table based on query text)."
    )


@history_group.command(name="import")
@click.argument("file_path", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--sql", "-s", help="SQL query text that identifies the destination table")
@click.option("--saved-query", "-S", help="Saved query name to resolve SQL text")
@click.option("--sheet", help="Worksheet name for Excel files", default=None)
@click.option("--encoding", default="utf-8-sig", help="CSV file encoding")
@click.pass_context
def import_history(
    ctx: click.Context,
    file_path: Path,
    sql: str | None,
    saved_query: str | None,
    sheet: str | None,
    encoding: str,
) -> None:
    """Import CSV or Excel data into the history database for a query."""
    config_dir, sql_text, saved_query_record = _resolve_query_definition(ctx, sql, saved_query)

    db = QueryHistoryDatabase(config_dir)
    suffix = file_path.suffix.lower()

    try:
        if suffix == ".csv":
            inserted = db.import_csv(sql_text, file_path, encoding=encoding)
            source_description = "CSV file"
        else:
            inserted = db.import_excel(sql_text, file_path, sheet_name=sheet)
            source_description = "Excel file" + (f" (sheet '{sheet}')" if sheet else "")
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc

    if inserted == 0:
        click.echo("No data imported; file contained no rows.")
        return

    if saved_query_record is not None:
        message_suffix = f" saved query '{saved_query_record.name}'"
    else:
        message_suffix = " the provided SQL text"
    click.echo(
        f"Imported {inserted} row(s) from {source_description} into history for{message_suffix}."
    )



@history_group.command(name="list-tables")
@click.option("--show-sql", is_flag=True, help="Include SQL preview for each table.")
@click.pass_context
def list_tables_command(ctx: click.Context, show_sql: bool) -> None:
    """List stored history tables and their metadata."""
    ctx.ensure_object(dict)
    config_dir: Path = ctx.obj.get("config_dir", DEFAULT_CONFIG_DIR)

    db = QueryHistoryDatabase(config_dir)
    entries = db.list_queries()
    if not entries:
        click.echo("No persisted query history found. Use QueryTable first.")
        return

    library = SavedQueryLibrary(config_dir)
    saved_map = {item.sql: item for item in library.list_queries()}

    click.echo("History tables:")
    for idx, entry in enumerate(entries, start=1):
        saved = saved_map.get(entry["query_text"])
        label = saved.name if saved else entry["sanitized_table"]
        created_at = entry.get("created_at", "")
        suffix = " (unlinked)" if saved is None else ""
        line = f"{idx}. {label}{suffix}"
        if created_at:
            line += f" - created {created_at}"
        click.echo(line)
        if show_sql:
            preview, truncated = _preview_sql(entry["query_text"])
            click.echo(f"    SQL: {preview}")
            if truncated:
                if saved is not None:
                    click.echo(f"    (truncated, run 'saved-query show {saved.name}' to view full SQL)")
                else:
                    click.echo("    (truncated)")

@history_group.command(name="export")
@click.option("--saved-query", "-S", help="Saved query name to export")
@click.option("--output", "-o", type=click.Path(path_type=Path), help="Destination CSV file path")
@click.pass_context
def export_history(
    ctx: click.Context,
    saved_query: str | None,
    output: Path | None,
) -> None:
    """Export stored history for a saved query to CSV."""
    ctx.ensure_object(dict)
    config_dir: Path = ctx.obj.get("config_dir", DEFAULT_CONFIG_DIR)

    library = SavedQueryLibrary(config_dir)
    preset = saved_query.strip() if saved_query else None
    entry, matched_saved = _select_history_entry(
        config_dir,
        library,
        "Enter the saved query name (or raw SQL text) to export",
        preset_selection=preset,
        show_listing=saved_query is None,
    )
    display_name = matched_saved.name if matched_saved else entry["query_text"]

    db = QueryHistoryDatabase(config_dir)

    try:
        export_path, row_count = db.export_query_to_excel(entry["query_text"], output)
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc

    if row_count == 0:
        click.echo("Export skipped because the query returned no rows.")
        return

    assert export_path is not None
    click.echo(f"Exported {row_count} row(s) for '{display_name}' to {export_path}.")


@history_group.command(name="import-table")
@click.pass_context
def import_table_command(ctx: click.Context) -> None:
    """Interactively import Excel data into an existing history table."""
    ctx.ensure_object(dict)
    config_dir: Path = ctx.obj.get("config_dir", DEFAULT_CONFIG_DIR)

    library = SavedQueryLibrary(config_dir)
    entry, matched_saved = _select_history_entry(
        config_dir,
        library,
        "Select table to import into (number or name)",
    )
    display_name = matched_saved.name if matched_saved else entry["query_text"]

    file_input = click.prompt("Enter path to Excel file (.xlsx, .xlsm, .xltx, .xltm)").strip()
    cleaned_path = file_input.strip("\"'")
    workbook_path = Path(cleaned_path).expanduser()
    if not workbook_path.exists() or not workbook_path.is_file():
        raise click.ClickException(f"File not found: {workbook_path}")

    replace_existing = click.confirm(
        f"Delete existing data in '{display_name}' before importing?", default=False
    )
    sheet_name_input = click.prompt(
        "Worksheet name (leave blank for the active sheet)",
        default="",
        show_default=False,
    ).strip()

    db = QueryHistoryDatabase(config_dir)
    if replace_existing:
        db.delete_query_history(entry["query_text"])

    try:
        imported = db.import_excel(
            entry["query_text"],
            workbook_path,
            sheet_name=sheet_name_input or None,
        )
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc

    if imported == 0:
        click.echo("Import completed but no rows were added.")
    else:
        click.echo(
            f"Imported {imported} row(s) into history table for '{display_name}'."
        )


@history_group.command(name="delete")
@click.option("--saved-query", "-S", help="Saved query name to delete")
@click.option("--force", is_flag=True, help="Skip confirmation prompt")
@click.pass_context
def delete_history(
    ctx: click.Context,
    saved_query: str | None,
    force: bool,
) -> None:
    """Delete stored history for a query."""
    ctx.ensure_object(dict)
    config_dir: Path = ctx.obj.get("config_dir", DEFAULT_CONFIG_DIR)

    library = SavedQueryLibrary(config_dir)
    preset = saved_query.strip() if saved_query else None
    entry, matched_saved = _select_history_entry(
        config_dir,
        library,
        "Select table to delete (number or name)",
        preset_selection=preset,
        show_listing=saved_query is None,
    )

    display_name = matched_saved.name if matched_saved else entry["query_text"]

    if not force:
        if not click.confirm(f"Delete all persisted history for '{display_name}'?", default=False):
            click.echo("Deletion cancelled.")
            return

    db = QueryHistoryDatabase(config_dir)
    if not db.delete_query_history(entry["query_text"]):
        raise click.ClickException("History table not found or could not be deleted.")

    click.echo(f"Deleted history table for '{display_name}'.")


@history_group.command(name="create-table")
@click.option("--timeout", type=int, default=300, help="Timeout per office (seconds)")
@click.option("--max-concurrent", type=int, default=10, help="Maximum concurrent offices")
@click.pass_context
def create_table_command(
    ctx: click.Context,
    timeout: int,
    max_concurrent: int,
) -> None:
    """Interactively create a new history table based on a saved query."""
    ctx.ensure_object(dict)
    config_dir: Path = ctx.obj.get("config_dir", DEFAULT_CONFIG_DIR)

    library = SavedQueryLibrary(config_dir)
    saved_queries = library.list_queries()
    if not saved_queries:
        raise click.ClickException("No saved queries available. Use 'QuerySave' to add one first.")

    click.echo("\nSaved queries:")
    for saved_query in saved_queries:
        click.echo(f"  - {saved_query.name}")

    selection = click.prompt("Enter the saved query name to base the table on").strip()
    if not selection:
        raise click.ClickException("Saved query name cannot be empty")

    try:
        library.get_query(selection)
    except KeyError as exc:
        raise click.ClickException(str(exc)) from exc

    click.echo(f"\nCreating history table using saved query '{selection}'.")
    ctx.invoke(
        run_query_history,
        sql=None,
        saved_query=selection,
        offices=None,
        timeout=timeout,
        max_concurrent=max_concurrent,
    )


def _resolve_query_definition(
    ctx: click.Context,
    sql: str | None,
    saved_query: str | None,
) -> tuple[Path, str, SavedQuery | None]:
    if not sql and not saved_query:
        raise click.UsageError("Provide --sql or --saved-query")
    if sql and saved_query:
        raise click.UsageError("Provide only one of --sql or --saved-query")

    ctx.ensure_object(dict)
    config_dir: Path = ctx.obj.get("config_dir", DEFAULT_CONFIG_DIR)

    if saved_query:
        library = SavedQueryLibrary(config_dir)
        try:
            saved_query_record = library.get_query(saved_query)
        except KeyError as exc:
            raise click.ClickException(str(exc)) from exc
        sql_text = saved_query_record.sql
        return config_dir, sql_text, saved_query_record

    assert sql is not None
    sql_text = sql.strip()
    if not sql_text:
        raise click.ClickException("SQL text cannot be empty")

    return config_dir, sql_text, None


def _select_history_entry(
    config_dir: Path,
    library: SavedQueryLibrary,
    prompt_message: str,
    *,
    preset_selection: str | None = None,
    show_listing: bool | None = None,
) -> tuple[dict[str, Any], SavedQuery | None]:
    """Prompt user to choose a stored history entry."""
    history_db = QueryHistoryDatabase(config_dir)
    stored_entries = history_db.list_queries()
    if not stored_entries:
        raise click.ClickException("No persisted query history found. Use QueryTable first.")

    saved_items = library.list_queries()
    sql_to_saved = {item.sql: item for item in saved_items}

    options: list[dict[str, Any]] = []
    should_show = show_listing if show_listing is not None else preset_selection is None

    if should_show:
        click.echo("\nHistory tables available:")

    for idx, entry in enumerate(stored_entries, start=1):
        matched = sql_to_saved.get(entry["query_text"])
        label = matched.name if matched else entry["query_text"]
        if should_show:
            click.echo(f"  {idx}. {label}")
        options.append({"entry": entry, "saved": matched, "label": label})

    selection_input = (
        preset_selection.strip() if preset_selection else click.prompt(prompt_message).strip()
    )
    if not selection_input:
        raise click.ClickException("Selection cannot be empty")

    selection_lower = selection_input.lower()
    chosen: dict[str, Any] | None = None

    if selection_input.isdigit():
        index = int(selection_input)
        if 1 <= index <= len(options):
            chosen = options[index - 1]

    if chosen is None:
        for option in options:
            saved_option = option["saved"]
            if saved_option and saved_option.name.lower() == selection_lower:
                chosen = option
                break

    if chosen is None:
        for option in options:
            if option["label"].lower() == selection_lower:
                chosen = option
                break

    if chosen is None:
        raise click.ClickException("Selection did not match any stored history tables.")

    return chosen["entry"], chosen["saved"]


def _ensure_vault_unlocked(ctx: click.Context, vault_manager: VaultManager) -> None:
    if vault_manager.is_unlocked():
        return

    attempts_remaining = MAX_PASSWORD_ATTEMPTS
    while attempts_remaining > 0 and not vault_manager.is_unlocked():
        prompt_text = "Enter vault password"
        if attempts_remaining < MAX_PASSWORD_ATTEMPTS:
            prompt_text = (
                f"Re-enter vault password ({attempts_remaining} attempt(s) remaining)"
            )
        password = click.prompt(prompt_text, hide_input=True, default="")
        try:
            vault_manager.unlock(password)
        except ValueError:
            pass
        if vault_manager.is_unlocked():
            break
        attempts_remaining -= 1

    if not vault_manager.is_unlocked():
        click.echo("Maximum password attempts reached. Vault remains locked.")
        ctx.exit(EXIT_VAULT_AUTH_FAILED)
