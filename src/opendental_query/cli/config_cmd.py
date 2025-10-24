"""Configuration management CLI commands."""

from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from opendental_query.core.config import ConfigManager
from opendental_query.utils.app_logger import get_logger

console = Console()
logger = get_logger(__name__)


@click.group(name="config")
def config_group() -> None:
    """Manage application configuration settings."""
    pass


@config_group.command(name="get")
@click.argument("key", type=str)
@click.pass_context
def config_get(ctx: click.Context, key: str) -> None:
    """Get a configuration value.

    Args:
        key: Configuration key to retrieve (e.g., 'vault.auto_lock_minutes')
    """
    try:
        config_dir = ctx.obj.get("config_dir", Path.home() / ".opendental-query")
        config_mgr = ConfigManager(config_dir)

        value = config_mgr.get(key)

        if value is None:
            console.print(f"[yellow]Configuration key '{key}' not set[/yellow]")
        else:
            console.print(f"[bold]{key}[/bold] = [green]{value}[/green]")

    except Exception as e:
        console.print(f"[red]Error getting config: {e}[/red]")
        raise click.Abort()


@config_group.command(name="set")
@click.argument("key", type=str)
@click.argument("value", type=str)
@click.pass_context
def config_set(ctx: click.Context, key: str, value: str) -> None:
    """Set a configuration value.

    Args:
        key: Configuration key to set
        value: Value to assign to the key
    """
    try:
        config_dir = ctx.obj.get("config_dir", Path.home() / ".opendental-query")
        config_mgr = ConfigManager(config_dir)

        # Convert value to appropriate type
        converted_value = _convert_value(value)

        config_mgr.set(key, converted_value)
        config_mgr.save()

        console.print(f"[green]✓[/green] Set [bold]{key}[/bold] = [green]{converted_value}[/green]")
        logger.info(f"Configuration updated: {key} = {converted_value}")

    except Exception as e:
        console.print(f"[red]Error setting config: {e}[/red]")
        raise click.Abort()


@config_group.command(name="list")
@click.pass_context
def config_list(ctx: click.Context) -> None:
    """List all configuration settings."""
    try:
        config_dir = ctx.obj.get("config_dir", Path.home() / ".opendental-query")
        config_mgr = ConfigManager(config_dir)

        config_dict = config_mgr.to_dict()

        if not config_dict:
            console.print("[yellow]No configuration settings found[/yellow]")
            return

        # Create table
        table = Table(title="Configuration Settings")
        table.add_column("Key", style="cyan", no_wrap=True)
        table.add_column("Value", style="green")
        table.add_column("Type", style="dim")

        # Flatten nested config to dot-notation
        flat_config = _flatten_dict(config_dict)

        for key, value in sorted(flat_config.items()):
            value_str = str(value)
            type_str = type(value).__name__
            table.add_row(key, value_str, type_str)

        console.print(table)

    except Exception as e:
        console.print(f"[red]Error listing config: {e}[/red]")
        raise click.Abort()


@config_group.command(name="reset")
@click.argument("key", type=str, required=False)
@click.option("--all", is_flag=True, help="Reset all configuration to defaults")
@click.pass_context
def config_reset(ctx: click.Context, key: str | None, all: bool) -> None:
    """Reset configuration to default values.

    Args:
        key: Specific configuration key to reset (optional)
        all: Reset all configuration if True
    """
    try:
        config_dir = ctx.obj.get("config_dir", Path.home() / ".opendental-query")
        config_mgr = ConfigManager(config_dir)

        if all:
            # Reset entire configuration
            config_mgr.reset_to_defaults()
            config_mgr.save()
            console.print("[green]✓[/green] Reset all configuration to defaults")
            logger.info("Configuration reset to defaults")
        elif key:
            # Reset specific key
            config_mgr.reset_key(key)
            config_mgr.save()
            console.print(f"[green]✓[/green] Reset [bold]{key}[/bold] to default")
            logger.info(f"Configuration key reset: {key}")
        else:
            console.print("[yellow]Specify a key to reset or use --all flag[/yellow]")

    except Exception as e:
        console.print(f"[red]Error resetting config: {e}[/red]")
        raise click.Abort()


@config_group.command(name="path")
@click.pass_context
def config_path(ctx: click.Context) -> None:
    """Show the path to the configuration file."""
    try:
        config_dir = ctx.obj.get("config_dir", Path.home() / ".opendental-query")
        config_mgr = ConfigManager(config_dir)

        config_file = config_mgr.config_path

        console.print("[bold]Configuration file:[/bold]")
        console.print(f"  {config_file}")

        if config_file.exists():
            console.print(f"[dim]  (exists, {config_file.stat().st_size} bytes)[/dim]")
        else:
            console.print("[dim]  (not yet created)[/dim]")

    except Exception as e:
        console.print(f"[red]Error getting config path: {e}[/red]")
        raise click.Abort()


def _convert_value(value_str: str) -> bool | int | float | str:
    """Convert string value to appropriate Python type.

    Args:
        value_str: String representation of value

    Returns:
        Converted value (bool, int, float, or str)
    """
    # Try boolean
    if value_str.lower() in ("true", "yes", "1", "on"):
        return True
    if value_str.lower() in ("false", "no", "0", "off"):
        return False

    # Try integer
    try:
        return int(value_str)
    except ValueError:
        pass

    # Try float
    try:
        return float(value_str)
    except ValueError:
        pass

    # Return as string
    return value_str


def _flatten_dict(d: dict, parent_key: str = "", sep: str = ".") -> dict:
    """Flatten nested dictionary to dot-notation.

    Args:
        d: Dictionary to flatten
        parent_key: Parent key prefix
        sep: Separator character

    Returns:
        Flattened dictionary
    """
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(_flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)
