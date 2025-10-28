"""Tests for persist CLI command."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from opendental_query.cli.persist_cmd import persist_command


class DummyResult:
    def __init__(self, all_rows):
        self.all_rows = all_rows
        self.failed_count = 0
        self.successful_count = len(all_rows)


def test_persist_command_appends_rows(tmp_path: Path, monkeypatch) -> None:
    runner = CliRunner()

    fake_config = MagicMock()
    fake_config.api_base_url = "https://api.example.com"
    fake_config.vault_path = tmp_path / "vault.vault"
    fake_config.vault_auto_lock_seconds = 900

    monkeypatch.setenv("SPEC_KIT_ALLOW_UNSAFE_EXPORTS", "1")

    with (
        patch("opendental_query.cli.persist_cmd.ConfigManager") as mock_config,
        patch("opendental_query.cli.persist_cmd.VaultManager") as mock_vault,
        patch("opendental_query.cli.persist_cmd.QueryEngine") as mock_engine,
        patch("opendental_query.cli.persist_cmd.PersistDatabase") as mock_db,
    ):
        mock_config.return_value = MagicMock(load=lambda: fake_config)

        vault_instance = MagicMock()
        vault_instance.is_unlocked.return_value = True
        vault_instance.get_vault.return_value = MagicMock(
            offices={"office1": MagicMock(customer_key="key1")},
            developer_key="dev-key",
        )
        mock_vault.return_value = vault_instance

        engine_instance = MagicMock()
        engine_instance.execute.return_value = DummyResult(
            [{"Office": "office1", "Value": 1}],
        )
        mock_engine.return_value = engine_instance

        db_instance = MagicMock()
        mock_db.return_value = db_instance

        result = runner.invoke(
            persist_command,
            ["--sql", "SELECT 1", "--table", "recent_results", "--offices", "office1"],
            obj={"config_dir": tmp_path},
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        db_instance.append_table.assert_called_once()
        args, kwargs = db_instance.append_table.call_args
        assert args[0] == "recent_results"
        assert args[1] == ["Office", "Value"]
