"""Main CLI entry point using Click framework."""

import sys
from pathlib import Path

import click
from rich.console import Console

from opendental_query import __version__
from opendental_query.constants import (
    DEFAULT_CONFIG_DIR,
    EXIT_SUCCESS,
)
from opendental_query.utils.app_logger import setup_logging
from opendental_query.utils.audit_logger import AuditLogger
from opendental_query.utils.startup_check import run_startup_checks

console = Console()


@click.group()
@click.version_option(version=__version__, prog_name="opendental-query")
@click.option(
    "--config-dir",
    type=click.Path(path_type=Path),
    default=DEFAULT_CONFIG_DIR,
    help="Configuration directory path",
    envvar="OPENDENTAL_CONFIG_DIR",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Enable verbose logging",
)
@click.pass_context
def cli(ctx: click.Context, config_dir: Path, verbose: bool) -> None:
    """OpenDental Multi-Office Query Tool.

    Securely execute SQL queries across multiple OpenDental databases
    with encrypted credential management and comprehensive audit logging.
    """
    # Ensure context object exists
    ctx.ensure_object(dict)

    # Store config in context for subcommands
    ctx.obj["config_dir"] = config_dir
    ctx.obj["verbose"] = verbose

    # Setup logging
    log_level = "DEBUG" if verbose else "INFO"
    log_file = config_dir / "app.log"

    try:
        import logging

        setup_logging(log_file, console_level=logging.DEBUG if verbose else logging.INFO)
    except Exception as e:
        console.print(f"[yellow]Warning: Could not initialize logging: {e}[/yellow]")


# Import command groups
from opendental_query.cli.config_cmd import config_group
from opendental_query.cli.query_cmd import query_command
from opendental_query.cli.update_cmd import check_update
from opendental_query.cli.vault_cmd import vault

# Register command groups
cli.add_command(vault)
cli.add_command(query_command)
cli.add_command(config_group)
cli.add_command(check_update)


def main() -> int:
    """Main entry point for CLI."""
    # Run startup checks
    try:
        success, message = run_startup_checks()
        if not success:
            console.print(f"[red]Startup check failed: {message}[/red]")
            return 1
    except Exception as e:
        console.print(f"[yellow]Warning: Startup checks failed: {e}[/yellow]")

    # Log app start
    try:
        audit_logger = AuditLogger()
        audit_logger.log("APP_START", success=True, details={"version": __version__})
    except Exception:
        pass  # Don't fail if audit logging fails

    try:
        cli(obj={})
        # Log app shutdown
        try:
            audit_logger.log("APP_SHUTDOWN", success=True)
        except Exception:
            pass
        return EXIT_SUCCESS
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        try:
            audit_logger.log("APP_SHUTDOWN", success=False, error=str(e))
        except Exception:
            pass
        return 1


if __name__ == "__main__":
    sys.exit(main())
