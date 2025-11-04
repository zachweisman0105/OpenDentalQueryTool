"""Vault management CLI commands."""

from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from opendental_query.constants import DEFAULT_VAULT_FILE
from opendental_query.core.vault import VaultManager
from opendental_query.utils.saved_queries import SavedQueryLibrary

console = Console()


class AliasedGroup(click.Group):
    """Custom Click Group that supports command aliases."""

    def get_command(self, ctx: click.Context, cmd_name: str) -> click.Command | None:
        """Override to support command aliases."""
        # Define aliases mapping
        aliases = {
            "add": "add-office",
            "remove": "remove-office",
            "rm": "remove-office",
            "rename": "rename-office",
            "edit": "rename-office",
            "mv": "rename-office",
            "list": "list-offices",
            "ls": "list-offices",
            "update-key": "update-developer-key",
            "delete": "destroy",
            "reset": "clear",
        }
        
        # Check if cmd_name is an alias
        actual_name = aliases.get(cmd_name, cmd_name)
        return super().get_command(ctx, actual_name)


@click.group(cls=AliasedGroup)
def vault() -> None:
    """Manage encrypted credential vault."""
    pass


@vault.command("init", short_help="Initialize a new encrypted vault")
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
    your OpenDental DeveloperKey. No password complexity requirements are
    enforced.
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
    console.print("Choose a master password (no complexity requirements).")
    console.print("You will need this password whenever you unlock the vault.\n")

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


@vault.command("add-office", short_help="Add office credentials to vault")
@click.argument("office_ids")
@click.option(
    "--vault-file",
    type=click.Path(path_type=Path),
    help="Vault file path",
)
@click.pass_context
def vault_add_office(ctx: click.Context, office_ids: str, vault_file: Path | None) -> None:
    """Add office credentials to vault.

    Adds CustomerKey for one or more offices to the vault. You must unlock
    the vault with your master password first.

    OFFICE_IDS: Comma-separated office identifiers (e.g., 'office1' or 'office1,office2,office3')
    
    Examples:
        vault add-office office1
        vault add-office office1,office2,office3
    """
    config_dir = ctx.obj["config_dir"]

    if vault_file is None:
        vault_file = config_dir / DEFAULT_VAULT_FILE

    if not vault_file.exists():
        console.print(f"[red]Error: Vault not found at {vault_file}[/red]")
        console.print("[yellow]Run 'opendental-query vault init' first.[/yellow]")
        raise click.Abort()

    # Parse office IDs (split by comma, strip whitespace)
    office_list = [office_id.strip() for office_id in office_ids.split(",") if office_id.strip()]
    
    if not office_list:
        console.print("[red]Error: No office IDs provided[/red]")
        raise click.Abort()

    # Collect CustomerKeys for all offices
    console.print(f"\n[bold]Adding {len(office_list)} office(s) to vault[/bold]\n")
    office_credentials = {}
    
    for office_id in office_list:
        customer_key = click.prompt(f"CustomerKey for {office_id}")
        office_credentials[office_id] = customer_key

    # Prompt for master password once
    console.print()
    password = click.prompt("Master password", hide_input=True)

    # Add all offices
    try:
        manager = VaultManager(vault_file)

        if not manager.unlock(password):
            console.print("[red]Error: Incorrect password[/red]")
            raise click.Abort()

        # Add each office and track results
        success_count = 0
        failed_offices = []
        
        console.print()
        for office_id, customer_key in office_credentials.items():
            try:
                manager.add_office(office_id, customer_key)
                console.print(f"[green]✓[/green] Added credentials for office: {office_id}")
                success_count += 1
            except ValueError as e:
                console.print(f"[red]✗[/red] Failed to add {office_id}: {e}")
                failed_offices.append(office_id)

        # Summary
        console.print()
        console.print(f"[bold]Summary:[/bold] {success_count}/{len(office_list)} office(s) added successfully")
        
        if failed_offices:
            console.print(f"[yellow]Failed offices: {', '.join(failed_offices)}[/yellow]")

    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise click.Abort()


@vault.command("remove-office", short_help="Remove office credentials from vault")
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


@vault.command("rename-office", short_help="Rename an existing office ID")
@click.argument("current_office_id")
@click.argument("new_office_id")
@click.option(
    "--vault-file",
    type=click.Path(path_type=Path),
    help="Vault file path",
)
@click.pass_context
def vault_rename_office(
    ctx: click.Context,
    current_office_id: str,
    new_office_id: str,
    vault_file: Path | None,
) -> None:
    """Rename an office credential while preserving its CustomerKey."""

    config_dir = ctx.obj["config_dir"]

    if vault_file is None:
        vault_file = config_dir / DEFAULT_VAULT_FILE

    if not vault_file.exists():
        console.print(f"[red]Error: Vault not found at {vault_file}[/red]")
        raise click.Abort()

    if current_office_id == new_office_id:
        console.print("[red]Error: New office ID must be different from the current ID[/red]")
        raise click.Abort()

    password = click.prompt("Master password", hide_input=True)

    try:
        manager = VaultManager(vault_file)
        if not manager.unlock(password):
            console.print("[red]Error: Incorrect password[/red]")
            raise click.Abort()

        manager.rename_office(current_office_id, new_office_id)

        updated_queries = 0
        try:
            library = SavedQueryLibrary(config_dir)
            updated_queries = library.rename_office(current_office_id, new_office_id)
        except Exception as exc:  # pragma: no cover - defensive logging
            console.print(
                f"[yellow]Warning: Unable to update saved queries for renamed office: {exc}[/yellow]"
            )

        console.print(
            f"[green]✓[/green] Renamed office '{current_office_id}' to '{new_office_id}'"
        )
        if updated_queries:
            noun = "query" if updated_queries == 1 else "queries"
            console.print(
                f"[green]✓[/green] Updated default offices in {updated_queries} saved {noun}"
            )

    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise click.Abort()


@vault.command("list-offices", short_help="List all offices in vault")
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


@vault.command("update-developer-key", short_help="Update DeveloperKey in vault")
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


@vault.command("clear", short_help="Remove all offices from vault")
@click.option(
    "--vault-file",
    type=click.Path(path_type=Path),
    help="Vault file path",
)
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    help="Skip confirmation prompt",
)
@click.pass_context
def vault_clear(ctx: click.Context, vault_file: Path | None, yes: bool) -> None:
    """Remove all offices from vault.

    Removes all office credentials from the vault while keeping the vault
    file and DeveloperKey intact. This is useful for cleaning up offices
    without having to reinitialize the entire vault.
    
    The DeveloperKey and master password remain unchanged.
    """
    config_dir = ctx.obj["config_dir"]

    if vault_file is None:
        vault_file = config_dir / DEFAULT_VAULT_FILE

    if not vault_file.exists():
        console.print(f"[red]Error: Vault not found at {vault_file}[/red]")
        raise click.Abort()

    # Prompt for master password
    password = click.prompt("Master password", hide_input=True)

    # Clear offices
    try:
        manager = VaultManager(vault_file)

        if not manager.unlock(password):
            console.print("[red]Error: Incorrect password[/red]")
            raise click.Abort()

        offices = manager.list_offices()

        if not offices:
            console.print("[yellow]Vault is already empty (no offices configured).[/yellow]")
            return

        # Confirm action
        console.print(f"\n[bold red]Warning:[/bold red] This will remove all {len(offices)} office(s) from the vault:")
        for office_id in sorted(offices):
            console.print(f"  • {office_id}")
        
        console.print("\n[dim]The vault file and DeveloperKey will remain intact.[/dim]")
        
        if not yes:
            if not click.confirm("\nAre you sure you want to remove all offices?"):
                console.print("[yellow]Cancelled[/yellow]")
                return

        # Remove all offices
        removed_count = 0
        failed_offices = []
        
        console.print()
        for office_id in offices:
            try:
                manager.remove_office(office_id)
                console.print(f"[green]✓[/green] Removed office: {office_id}")
                removed_count += 1
            except ValueError as e:
                console.print(f"[red]✗[/red] Failed to remove {office_id}: {e}")
                failed_offices.append(office_id)

        # Summary
        console.print()
        console.print(f"[bold]Summary:[/bold] {removed_count}/{len(offices)} office(s) removed")
        
        if failed_offices:
            console.print(f"[yellow]Failed offices: {', '.join(failed_offices)}[/yellow]")
        else:
            console.print("[green]All offices removed successfully[/green]")

    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise click.Abort()


@vault.command("destroy", short_help="Completely delete the vault file")
@click.option(
    "--vault-file",
    type=click.Path(path_type=Path),
    help="Vault file path",
)
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    help="Skip confirmation prompt",
)
@click.pass_context
def vault_destroy(ctx: click.Context, vault_file: Path | None, yes: bool) -> None:
    """Completely delete the vault file.

    Permanently deletes the entire vault file, including all office credentials
    and the DeveloperKey. This action cannot be undone.
    
    After destroying the vault, you will need to run 'vault init' to create
    a new vault before you can use vault commands again.
    
    Use 'vault clear' instead if you only want to remove offices while keeping
    the vault and DeveloperKey.
    """
    config_dir = ctx.obj["config_dir"]

    if vault_file is None:
        vault_file = config_dir / DEFAULT_VAULT_FILE

    if not vault_file.exists():
        console.print(f"[yellow]Vault file does not exist at {vault_file}[/yellow]")
        console.print("[dim]Nothing to destroy.[/dim]")
        return

    # Show warning
    console.print(f"\n[bold red]⚠️  WARNING: DESTRUCTIVE ACTION ⚠️[/bold red]")
    console.print(f"\nThis will [bold]permanently delete[/bold] the vault file at:")
    console.print(f"  {vault_file}")
    console.print("\n[red]All office credentials and the DeveloperKey will be lost.[/red]")
    console.print("[red]This action cannot be undone.[/red]")
    
    if not yes:
        console.print("\nType the vault file name to confirm deletion:")
        confirmation = click.prompt(f"Enter '{vault_file.name}'")
        
        if confirmation != vault_file.name:
            console.print("[yellow]Confirmation failed. Vault not destroyed.[/yellow]")
            return

    # Delete the vault file
    try:
        vault_file.unlink()
        console.print(f"\n[green]✓[/green] Vault file deleted: {vault_file}")
        console.print("\n[dim]Run 'vault init' to create a new vault.[/dim]")
    except Exception as e:
        console.print(f"\n[red]Error deleting vault file: {e}[/red]")
        raise click.Abort()
