"""Tests for CLI shortcut entry points."""

from __future__ import annotations

from typing import Any

import pytest

from opendental_query.cli import shortcuts


@pytest.fixture
def fake_cli(monkeypatch: pytest.MonkeyPatch) -> list[list[str]]:
    """Capture sys.argv mutations when a shortcut delegates to the main CLI."""
    captured: list[list[str]] = []

    def _fake_cli(obj: dict[str, Any] | None = None) -> None:
        captured.append(list(shortcuts.sys.argv))
        assert obj == {}

    monkeypatch.setattr(shortcuts, "cli", _fake_cli)
    return captured


def _set_argv(monkeypatch: pytest.MonkeyPatch, *args: str) -> None:
    monkeypatch.setattr(shortcuts.sys, "argv", list(args) or ["shortcut"])


def test_vault_shortcut_sets_arguments(monkeypatch: pytest.MonkeyPatch, fake_cli: list[list[str]]) -> None:
    _set_argv(monkeypatch, "Vault")
    shortcuts.vault_shortcut()
    assert fake_cli == [["opendental-query", "vault"]]


def test_config_shortcut_sets_arguments(monkeypatch: pytest.MonkeyPatch, fake_cli: list[list[str]]) -> None:
    _set_argv(monkeypatch, "Config")
    shortcuts.config_shortcut()
    assert fake_cli == [["opendental-query", "config"]]


def test_query_table_shortcut_inserts_subcommand(
    monkeypatch: pytest.MonkeyPatch, fake_cli: list[list[str]]
) -> None:
    _set_argv(monkeypatch, "QueryTable")
    shortcuts.query_table_shortcut()
    assert fake_cli == [["opendental-query", "history", "create-table"]]


def test_table_export_shortcut(monkeypatch: pytest.MonkeyPatch, fake_cli: list[list[str]]) -> None:
    _set_argv(monkeypatch, "TableExport")
    shortcuts.table_export_shortcut()
    assert fake_cli == [["opendental-query", "history", "export"]]
