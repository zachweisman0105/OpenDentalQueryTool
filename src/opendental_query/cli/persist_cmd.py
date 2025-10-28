"""CLI command for persisting query results to encrypted SQLite."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import click

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
from opendental_query.utils.persist_db import PersistDatabase
from opendental_query.utils.saved_queries import SavedQuery, SavedQueryLibrary


@click.command(name="persist")
@click.option("--sql", "-s", help="SQL query to execute")
@click.option("--saved-query", "-S", help="Name of saved query to execute")
@click.option("--table", "-t", required=True, help="Destination table name")
@click.option("--offices", "-o", help="Comma separated office IDs or 'ALL'")
@click.option("--timeout", type=int, default=300, help="Timeout per office (seconds)")
@click.option("--max-concurrent", type=int, default=10, help="Maximum concurrent offices")
@click.pass_context
def persist_command(
    ctx: click.Context,
    sql: str | None,
    saved_query: str | None,
    table: str,
    offices: str | None,
    timeout: int,
    max_concurrent: int,
) -> None:
    """Execute query and append results to the encrypted persistence database."""

    if not sql and not saved_query:
        raise click.UsageError("Provide --sql or --saved-query")
    if sql and saved_query:
        raise click.UsageError("Provide only one of --sql or --saved-query")

    ctx.ensure_object(dict)
    config_dir: Path = ctx.obj.get("config_dir", DEFAULT_CONFIG_DIR)
    config_manager = ConfigManager(config_dir)
    config = config_manager.load()

    saved_query_record: SavedQuery | None = None
    if saved_query:
        library = SavedQueryLibrary(config_dir)
        try:
            saved_query_record = library.get_query(saved_query)
        except KeyError as exc:  # pragma: no cover - CLI surface
            raise click.ClickException(str(exc)) from exc
        sql = saved_query_record.sql
        if offices is None and saved_query_record.default_offices:
            offices = (
                "ALL"
                if saved_query_record.default_offices == ["ALL"]
                else ",".join(saved_query_record.default_offices)
            )

    vault_manager = VaultManager(config.vault_path)
    try:
        vault_manager.configure_auto_lock(config.vault_auto_lock_seconds)
    except Exception as exc:  # pragma: no cover - warning only
        click.echo(f"[yellow]Warning: Invalid auto-lock configuration: {exc}[/yellow]")

    if not vault_manager.is_unlocked():
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
            click.echo("[red]Maximum password attempts reached. Vault remains locked.[/red]")
            ctx.exit(EXIT_VAULT_AUTH_FAILED)

    vault_data = vault_manager.get_vault()
    if not vault_data.offices:
        raise click.ClickException("No offices configured in vault")

    if sql is None:
        raise click.ClickException("SQL must be provided")

    if offices is None:
        click.echo("\n[cyan]Available offices:[/cyan]")
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
        sql=sql,
        office_credentials=office_credentials,
        api_base_url=config.api_base_url,
        timeout_seconds=float(timeout),
    )

    if result.failed_count > 0 and result.successful_count == 0:
        raise click.ClickException("Query failed for all offices")

    if not result.all_rows:
        click.echo("[yellow]Query returned no rows; nothing persisted.[/yellow]")
        return

    columns = list(result.all_rows[0].keys())
    rows_to_store = [{col: row.get(col) for col in columns} for row in result.all_rows]

    persist_db = PersistDatabase(config_dir)
    try:
        inserted = persist_db.append_table(table, columns, rows_to_store)
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc

    click.echo(f"[green]Persisted {inserted} row(s) to table '{table}'.[/green]")
