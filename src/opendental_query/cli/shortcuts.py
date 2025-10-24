"""Shortcut entry points for CLI commands.

These functions provide convenient single-word commands that users can
invoke directly without typing the full 'opendental-query' prefix.

Examples:
    Query           # instead of: opendental-query query
    Vault           # instead of: opendental-query vault
    Config          # instead of: opendental-query config
    VaultInit       # instead of: opendental-query vault init
    VaultAdd        # instead of: opendental-query vault add-office
"""

import sys

import click

from opendental_query.cli.main import cli


def vault_shortcut() -> None:
    """Entry point for 'Vault' command."""
    # Replace program name and inject vault command
    sys.argv[0] = "opendental-query"
    sys.argv.insert(1, "vault")
    cli(obj={})


def config_shortcut() -> None:
    """Entry point for 'Config' command."""
    # Replace program name and inject config command
    sys.argv[0] = "opendental-query"
    sys.argv.insert(1, "config")
    cli(obj={})


def update_shortcut() -> None:
    """Entry point for 'Update' command."""
    # Replace program name and inject check-update command
    sys.argv[0] = "opendental-query"
    sys.argv.insert(1, "check-update")
    cli(obj={})


def vault_init_shortcut() -> None:
    """Entry point for 'VaultInit' command."""
    sys.argv[0] = "opendental-query"
    sys.argv.insert(1, "vault")
    sys.argv.insert(2, "init")
    cli(obj={})


def vault_add_shortcut() -> None:
    """Entry point for 'VaultAdd' command."""
    sys.argv[0] = "opendental-query"
    sys.argv.insert(1, "vault")
    sys.argv.insert(2, "add-office")
    cli(obj={})


def vault_remove_shortcut() -> None:
    """Entry point for 'VaultRemove' command."""
    sys.argv[0] = "opendental-query"
    sys.argv.insert(1, "vault")
    sys.argv.insert(2, "remove-office")
    cli(obj={})


def vault_list_shortcut() -> None:
    """Entry point for 'VaultList' command."""
    sys.argv[0] = "opendental-query"
    sys.argv.insert(1, "vault")
    sys.argv.insert(2, "list-offices")
    cli(obj={})


def vault_update_key_shortcut() -> None:
    """Entry point for 'VaultUpdateKey' command."""
    sys.argv[0] = "opendental-query"
    sys.argv.insert(1, "vault")
    sys.argv.insert(2, "update-developer-key")
    cli(obj={})


def config_get_shortcut() -> None:
    """Entry point for 'ConfigGet' command."""
    sys.argv[0] = "opendental-query"
    sys.argv.insert(1, "config")
    sys.argv.insert(2, "get")
    cli(obj={})


def config_set_shortcut() -> None:
    """Entry point for 'ConfigSet' command."""
    sys.argv[0] = "opendental-query"
    sys.argv.insert(1, "config")
    sys.argv.insert(2, "set")
    cli(obj={})


def config_list_shortcut() -> None:
    """Entry point for 'ConfigList' command."""
    sys.argv[0] = "opendental-query"
    sys.argv.insert(1, "config")
    sys.argv.insert(2, "list")
    cli(obj={})


def config_reset_shortcut() -> None:
    """Entry point for 'ConfigReset' command."""
    sys.argv[0] = "opendental-query"
    sys.argv.insert(1, "config")
    sys.argv.insert(2, "reset")
    cli(obj={})


def config_path_shortcut() -> None:
    """Entry point for 'ConfigPath' command."""
    sys.argv[0] = "opendental-query"
    sys.argv.insert(1, "config")
    sys.argv.insert(2, "path")
    cli(obj={})


def vault_clear_shortcut() -> None:
    """Entry point for 'VaultClear' command."""
    sys.argv[0] = "opendental-query"
    sys.argv.insert(1, "vault")
    sys.argv.insert(2, "clear")
    cli(obj={})


def vault_destroy_shortcut() -> None:
    """Entry point for 'VaultDestroy' command."""
    sys.argv[0] = "opendental-query"
    sys.argv.insert(1, "vault")
    sys.argv.insert(2, "destroy")
    cli(obj={})

