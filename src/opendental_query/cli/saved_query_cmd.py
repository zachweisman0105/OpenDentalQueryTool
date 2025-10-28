"""CLI commands for managing saved SQL queries."""

from __future__ import annotations

import sys
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from opendental_query.constants import DEFAULT_CONFIG_DIR
from opendental_query.utils.saved_queries import SavedQuery, SavedQueryLibrary

console = Console()
SQL_PREVIEW_LIMIT = 200


def _format_sql_preview(sql_text: str, limit: int = SQL_PREVIEW_LIMIT) -> tuple[str, bool]:
    """Return a trimmed preview of SQL text."""
    normalized = " ".join(sql_text.split())
    if len(normalized) <= limit:
        return normalized, False
    preview = normalized[: limit - 3].rstrip()
    return preview + "...", True


@click.group(name="saved-query")
@click.pass_context
def saved_query_group(ctx: click.Context) -> None:
    """Manage saved SQL queries."""
    ctx.ensure_object(dict)


def _get_library(ctx: click.Context) -> SavedQueryLibrary:
    ctx_obj = ctx.obj or {}
    config_dir: Path = ctx_obj.get("config_dir", DEFAULT_CONFIG_DIR)
    return SavedQueryLibrary(config_dir)


def _resolve_query_names(raw: str, existing: list[SavedQuery]) -> list[str]:
    tokens = [token.strip() for token in raw.split(",") if token.strip()]
    if not tokens:
        return []

    if not existing:
        return []

    name_map = {query.name.lower(): query.name for query in existing}

    if any(token.lower() == "all" for token in tokens):
        return [query.name for query in existing]

    resolved: list[str] = []
    seen: set[str] = set()
    missing: list[str] = []

    for token in tokens:
        key = token.lower()
        if key in seen:
            continue
        seen.add(key)
        actual = name_map.get(key)
        if actual is None:
            missing.append(token)
        else:
            resolved.append(actual)

    if missing:
        raise KeyError(", ".join(missing))

    return resolved


@saved_query_group.command("list")
@click.option(
    "--show-sql",
    is_flag=True,
    help="Display the SQL for each saved query.",
)
@click.pass_context
def list_saved_queries(ctx: click.Context, show_sql: bool) -> None:
    """List saved queries."""
    library = _get_library(ctx)
    queries = library.list_queries()
    if not queries:
        console.print("[yellow]No saved queries found.[/yellow]")
        return

    if show_sql:
        for query in queries:
            console.print(f"[bold cyan]{query.name}[/bold cyan]")
            if query.description:
                console.print(f"[dim]{query.description}[/dim]")
            if query.default_offices:
                console.print(f"[blue]Default offices:[/blue] {', '.join(query.default_offices)}")
            preview, truncated = _format_sql_preview(query.sql)
            console.print("[bold]SQL Preview:[/bold]")
            console.print(preview, highlight=False)
            if truncated:
                console.print(
                    f"[dim](truncated, run 'saved-query show {query.name}' to view full SQL)[/dim]"
                )
            console.print("-" * 60)
    else:
        table = Table(title="Saved Queries", show_lines=False, header_style="bold cyan")
        table.add_column("Name", style="bold")
        table.add_column("Description")
        table.add_column("Default Offices")
        table.add_column("Updated")

        for query in queries:
            offices = ", ".join(query.default_offices) if query.default_offices else "-"
            desc = query.description or "-"
            table.add_row(query.name, desc, offices, query.updated_at)

        console.print(table)


@saved_query_group.command("save")
@click.option("--name", "-n", required=True, help="Unique name for the saved query.")
@click.option("--sql", "-s", help="SQL text to save.")
@click.option(
    "--sql-file",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Path to a file containing the SQL to save.",
)
@click.option("--description", "-d", help="Optional description for the query.")
@click.option(
    "--offices",
    "-o",
    help="Default offices for this query (comma-separated list, or 'ALL').",
)
@click.option(
    "--overwrite",
    is_flag=True,
    help="Allow replacing an existing saved query with the same name.",
)
@click.pass_context
def save_query_cmd(
    ctx: click.Context,
    name: str,
    sql: str | None,
    sql_file: Path | None,
    description: str | None,
    offices: str | None,
    overwrite: bool,
) -> None:
    """Save a SQL query for future reuse."""
    if sql and sql_file:
        raise click.UsageError("Specify only one of --sql or --sql-file")

    if sql_file:
        sql = sql_file.read_text(encoding="utf-8")

    if not sql:
        edited = click.edit(text="\n-- Enter SQL above this line --\n")
        if edited is None:
            console.print("[yellow]Aborted - no SQL provided.[/yellow]")
            return
        sql = edited

    default_offices = _parse_office_string(offices)
    library = _get_library(ctx)

    try:
        saved = library.save_query(
            name,
            sql,
            description=description,
            default_offices=default_offices,
            overwrite=overwrite,
        )
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc

    action = "Updated" if overwrite else "Saved"
    console.print(f"[green]{action} query '{saved.name}'.[/green]")


@saved_query_group.command("savesimple")
@click.pass_context
def save_query_simple(ctx: click.Context) -> None:
    """Interactive shortcut to save a query via prompts."""
    name = click.prompt("Saved query name", type=str).strip()
    sql_lines: list[str] = []
    console.print("[cyan]Enter SQL (finish with an empty line):[/cyan]")
    while True:
        try:
            line = input()
        except EOFError:
            line = ""
        if not line:
            break
        sql_lines.append(line)
    sql = "\n".join(sql_lines).strip()
    if not sql:
        console.print("[red]No SQL provided. Query not saved.[/red]")
        return

    library = _get_library(ctx)
    try:
        saved = library.save_query(name, sql, overwrite=False)
    except ValueError as exc:
        console.print(f"[red]{exc}[/red]")
        return
    console.print(f"[green]Query '{saved.name}' saved.[/green]")


@saved_query_group.command("show")
@click.argument("name")
@click.pass_context
def show_saved_query(ctx: click.Context, name: str) -> None:
    """Display details about a saved query."""
    library = _get_library(ctx)
    try:
        query = library.get_query(name)
    except KeyError as exc:
        raise click.ClickException(str(exc)) from exc

    console.print(f"[bold cyan]{query.name}[/bold cyan]")
    if query.description:
        console.print(f"[dim]{query.description}[/dim]")
    if query.default_offices:
        console.print(f"[blue]Default offices:[/blue] {', '.join(query.default_offices)}")
    console.print()
    console.print("[bold]SQL:[/bold]")
    console.print(query.sql, highlight=False)


@saved_query_group.command("delete")
@click.argument("name")
@click.option("--force", "-f", is_flag=True, help="Do not prompt for confirmation.")
@click.pass_context
def delete_saved_query(ctx: click.Context, name: str, force: bool) -> None:
    """Delete saved query or queries."""
    library = _get_library(ctx)
    existing = library.list_queries()

    try:
        names = _resolve_query_names(name, existing)
    except KeyError as exc:
        console.print(f"[red]Saved query '{exc.args[0]}' not found.[/red]")
        return

    if not names:
        console.print("[yellow]No saved queries matched your selection.[/yellow]")
        return

    if not force:
        if len(names) == len(existing):
            prompt_label = f"all {len(names)} saved queries"
        elif len(names) > 3:
            prompt_label = f"{len(names)} saved queries ({', '.join(names[:3])}...)"
        else:
            prompt_label = ", ".join(names)

        if not click.confirm(f"Delete {prompt_label}?", default=False):
            console.print("[yellow]Deletion cancelled.[/yellow]")
            return

    try:
        library.delete_queries(names)
    except KeyError as exc:
        console.print(f"[red]{exc}[/red]")
        return

    if len(names) == 1:
        console.print(f"[green]Deleted saved query '{names[0]}'.[/green]")
    else:
        console.print(f"[green]Deleted saved queries: {', '.join(names)}[/green]")


@saved_query_group.command("deleteinteractive")
@click.pass_context
def delete_saved_query_interactive(ctx: click.Context) -> None:
    """Interactively delete a saved query by prompting for the name."""
    library = _get_library(ctx)
    queries = library.list_queries()
    if not queries:
        console.print("[yellow]No saved queries available to delete.[/yellow]")
        return

    console.print("[cyan]Saved queries:[/cyan]")
    for query in queries:
        console.print(f"  - {query.name}")

    raw_input = click.prompt("Enter saved query names to delete (comma separated or 'ALL')").strip()
    if not raw_input:
        console.print("[yellow]Deletion cancelled.[/yellow]")
        return

    try:
        names = _resolve_query_names(raw_input, queries)
    except KeyError as exc:
        console.print(f"[red]Saved query '{exc.args[0]}' not found.[/red]")
        return

    if not names:
        console.print("[yellow]No saved queries matched your selection.[/yellow]")
        return

    try:
        library.delete_queries(names)
    except KeyError as exc:
        console.print(f"[red]{exc}")
        return

    if len(names) == 1:
        console.print(f"[green]Deleted saved query '{names[0]}'.[/green]")
    else:
        console.print(f"[green]Deleted saved queries: {', '.join(names)}[/green]")


@saved_query_group.command("run")
@click.argument("name")
@click.option(
    "--offices",
    "-o",
    help="Override saved default offices (comma-separated list or 'ALL').",
)
@click.option(
    "--timeout",
    "-t",
    type=int,
    default=300,
    help="Timeout per office in seconds.",
)
@click.option(
    "--max-concurrent",
    "-c",
    type=int,
    default=10,
    help="Maximum concurrent office queries.",
)
@click.option(
    "--export",
    "export_results",
    is_flag=True,
    help="Export results to Excel after execution.",
)
@click.pass_context
def run_saved_query(
    ctx: click.Context,
    name: str,
    offices: str | None,
    timeout: int,
    max_concurrent: int,
    export_results: bool,
) -> None:
    """Execute a saved query."""
    from opendental_query.cli.query_cmd import query_command

    params = {
        "sql": None,
        "saved_query": name,
        "offices": offices,
        "timeout": timeout,
        "max_concurrent": max_concurrent,
        "export_results": export_results,
    }
    ctx.invoke(query_command, **params)


def _parse_office_string(offices: str | None) -> list[str]:
    if not offices:
        return []
    if offices.strip().upper() == "ALL":
        return ["ALL"]
    return [office.strip() for office in offices.split(",") if office.strip()]


def shortcut_save_query() -> None:
    """Entry point for the QuerySave console script."""
    from opendental_query.cli.main import cli

    args = sys.argv[1:]
    if args and args[0].lower() == "list":
        cli.main(args=["saved-query", "list", "--show-sql"])
    elif args and args[0].lower() == "delete":
        cli.main(args=["saved-query", "deleteinteractive"])
    elif args:
        query_name = " ".join(args)
        cli.main(
            args=[
                "saved-query",
                "run",
                query_name,
            ]
        )
    else:
        cli.main(args=["saved-query", "savesimple"])
