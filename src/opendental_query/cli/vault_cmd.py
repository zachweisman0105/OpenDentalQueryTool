"""Vault management CLI commands."""

from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from opendental_query.constants import DEFAULT_VAULT_FILE
from opendental_query.core.vault import VaultManager

console = Console()


@click.group()
def vault() -> None:
    """Manage encrypted credential vault."""
    pass


@vault.command("init")
@click.option(
    "--vault-file",
    type=click.Path(path_type=Path),
    help="Vault file path (default: ~/.opendental-query/credentials.vault)",
)
@click.pass_context
def vault_init(ctx: click.Context, vault_file: Path | None) -> None:
    """Initialize a new encrypted vault.

    Creates a new vault file protected by a master password. You will be
    prompted to enter the password twice for confirmation, and to provide
    your OpenDental DeveloperKey.

    Requirements:
    - Password must be at least 12 characters
    - Must contain uppercase, lowercase, digit, and special character
    """
    config_dir = ctx.obj["config_dir"]

    if vault_file is None:
        vault_file = config_dir / DEFAULT_VAULT_FILE

    # Check if vault already exists
    if vault_file.exists():
        console.print(f"[red]Error: Vault already exists at {vault_file}[/red]")
        console.print("[yellow]Use vault-update-developer-key to change the key.[/yellow]")
        raise click.Abort()

    console.print("[bold]Initialize Vault[/bold]\n")
    console.print("Create a strong master password with:")
    console.print("  • At least 12 characters")
    console.print("  • Uppercase and lowercase letters")
    console.print("  • Numbers and special characters\n")

    # Prompt for password
    password = click.prompt("Master password", hide_input=True)
    password_confirm = click.prompt("Confirm password", hide_input=True)

    if password != password_confirm:
        console.print("[red]Error: Passwords do not match[/red]")
        raise click.Abort()

    # Prompt for DeveloperKey
    console.print()
    developer_key = click.prompt("OpenDental DeveloperKey")

    # Create vault
    try:
        manager = VaultManager(vault_file)
        manager.init(password, developer_key)

        console.print(f"\n[green]✓[/green] Vault initialized at {vault_file}")
        console.print("[green]✓[/green] Vault is unlocked and ready")
        console.print("\n[dim]The vault will auto-lock after 15 minutes of inactivity.[/dim]")

    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise click.Abort()


@vault.command("add-office")
@click.argument("office_id")
@click.option(
    "--vault-file",
    type=click.Path(path_type=Path),
    help="Vault file path",
)
@click.pass_context
def vault_add_office(ctx: click.Context, office_id: str, vault_file: Path | None) -> None:
    """Add office credentials to vault.

    Adds CustomerKey for a specific office to the vault. You must unlock
    the vault with your master password first.

    OFFICE_ID: Unique identifier for the office (e.g., 'main-office')
    """
    config_dir = ctx.obj["config_dir"]

    if vault_file is None:
        vault_file = config_dir / DEFAULT_VAULT_FILE

    if not vault_file.exists():
        console.print(f"[red]Error: Vault not found at {vault_file}[/red]")
        console.print("[yellow]Run 'opendental-query vault init' first.[/yellow]")
        raise click.Abort()

    # Prompt for CustomerKey
    customer_key = click.prompt(f"CustomerKey for {office_id}")

    # Prompt for master password
    password = click.prompt("Master password", hide_input=True)

    # Add office
    try:
        manager = VaultManager(vault_file)

        if not manager.unlock(password):
            console.print("[red]Error: Incorrect password[/red]")
            raise click.Abort()

        manager.add_office(office_id, customer_key)

        console.print(f"[green]✓[/green] Added credentials for office: {office_id}")

    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise click.Abort()


@vault.command("remove-office")
@click.argument("office_id")
@click.option(
    "--vault-file",
    type=click.Path(path_type=Path),
    help="Vault file path",
)
@click.pass_context
def vault_remove_office(ctx: click.Context, office_id: str, vault_file: Path | None) -> None:
    """Remove office credentials from vault.

    Removes CustomerKey for a specific office from the vault.

    OFFICE_ID: Office identifier to remove
    """
    config_dir = ctx.obj["config_dir"]

    if vault_file is None:
        vault_file = config_dir / DEFAULT_VAULT_FILE

    if not vault_file.exists():
        console.print(f"[red]Error: Vault not found at {vault_file}[/red]")
        raise click.Abort()

    # Confirm removal
    if not click.confirm(f"Remove credentials for {office_id}?"):
        console.print("[yellow]Cancelled[/yellow]")
        return

    # Prompt for master password
    password = click.prompt("Master password", hide_input=True)

    # Remove office
    try:
        manager = VaultManager(vault_file)

        if not manager.unlock(password):
            console.print("[red]Error: Incorrect password[/red]")
            raise click.Abort()

        manager.remove_office(office_id)

        console.print(f"[green]✓[/green] Removed credentials for office: {office_id}")

    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise click.Abort()


@vault.command("list-offices")
@click.option(
    "--vault-file",
    type=click.Path(path_type=Path),
    help="Vault file path",
)
@click.pass_context
def vault_list_offices(ctx: click.Context, vault_file: Path | None) -> None:
    """List all offices in vault.

    Shows office IDs only (credentials are not displayed for security).
    """
    config_dir = ctx.obj["config_dir"]

    if vault_file is None:
        vault_file = config_dir / DEFAULT_VAULT_FILE

    if not vault_file.exists():
        console.print(f"[red]Error: Vault not found at {vault_file}[/red]")
        console.print("[yellow]Run 'opendental-query vault init' first.[/yellow]")
        raise click.Abort()

    # Prompt for master password
    password = click.prompt("Master password", hide_input=True)

    # List offices
    try:
        manager = VaultManager(vault_file)

        if not manager.unlock(password):
            console.print("[red]Error: Incorrect password[/red]")
            raise click.Abort()

        offices = manager.list_offices()

        if not offices:
            console.print("[yellow]No offices configured in vault.[/yellow]")
            console.print("[dim]Use 'opendental-query vault add-office' to add offices.[/dim]")
            return

        # Display table
        table = Table(title="Configured Offices")
        table.add_column("Office ID", style="cyan")

        for office_id in sorted(offices):
            table.add_row(office_id)

        console.print()
        console.print(table)
        console.print(f"\n[dim]Total: {len(offices)} office(s)[/dim]")

    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise click.Abort()


@vault.command("update-developer-key")
@click.option(
    "--vault-file",
    type=click.Path(path_type=Path),
    help="Vault file path",
)
@click.pass_context
def vault_update_developer_key(ctx: click.Context, vault_file: Path | None) -> None:
    """Update DeveloperKey in vault.

    Updates the OpenDental DeveloperKey stored in the vault.
    """
    config_dir = ctx.obj["config_dir"]

    if vault_file is None:
        vault_file = config_dir / DEFAULT_VAULT_FILE

    if not vault_file.exists():
        console.print(f"[red]Error: Vault not found at {vault_file}[/red]")
        raise click.Abort()

    # Prompt for new DeveloperKey
    new_key = click.prompt("New DeveloperKey")

    # Prompt for master password
    password = click.prompt("Master password", hide_input=True)

    # Update key
    try:
        manager = VaultManager(vault_file)

        if not manager.unlock(password):
            console.print("[red]Error: Incorrect password[/red]")
            raise click.Abort()

        manager.update_developer_key(new_key)

        console.print("[green]✓[/green] DeveloperKey updated successfully")

    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise click.Abort()
