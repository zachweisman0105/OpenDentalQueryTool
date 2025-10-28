"""Tests for saved query CLI commands."""

import sys
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from opendental_query.cli.saved_query_cmd import saved_query_group, shortcut_save_query


class TestSavedQueryCLI:
    def test_save_and_list_queries(self, tmp_path: Path) -> None:
        runner = CliRunner()
        result = runner.invoke(
            saved_query_group,
            ["save", "--name", "daily", "--sql", "SELECT * FROM patient"],
            obj={"config_dir": tmp_path},
        )
        assert result.exit_code == 0

        list_result = runner.invoke(
            saved_query_group,
            ["list"],
            obj={"config_dir": tmp_path},
        )
        assert list_result.exit_code == 0
        assert "daily" in list_result.output

    def test_list_show_sql(self, tmp_path: Path) -> None:
        runner = CliRunner()
        runner.invoke(
            saved_query_group,
            ["save", "--name", "daily", "--sql", "SELECT * FROM patient"],
            obj={"config_dir": tmp_path},
        )
        result = runner.invoke(
            saved_query_group,
            ["list", "--show-sql"],
            obj={"config_dir": tmp_path},
        )
        assert "SELECT * FROM patient" in result.output

    def test_list_show_sql_truncates_long_queries(self, tmp_path: Path) -> None:
        runner = CliRunner()
        long_sql = "SELECT * FROM patient WHERE " + " OR ".join([f"Col{i} = {i}" for i in range(200)])
        runner.invoke(
            saved_query_group,
            ["save", "--name", "long", "--sql", long_sql],
            obj={"config_dir": tmp_path},
        )
        result = runner.invoke(
            saved_query_group,
            ["list", "--show-sql"],
            obj={"config_dir": tmp_path},
        )
        assert "long" in result.output
        assert "..." in result.output
        assert "truncated" in result.output
        assert long_sql not in result.output


    def test_show_displays_saved_query(self, tmp_path: Path) -> None:
        runner = CliRunner()
        runner.invoke(
            saved_query_group,
            ["save", "--name", "showcase", "--sql", "SELECT 1", "--description", "demo"],
            obj={"config_dir": tmp_path},
        )
        show_result = runner.invoke(
            saved_query_group,
            ["show", "showcase"],
            obj={"config_dir": tmp_path},
        )
        assert show_result.exit_code == 0
        assert "SELECT 1" in show_result.output
        assert "demo" in show_result.output

    def test_delete_saved_query(self, tmp_path: Path) -> None:
        runner = CliRunner()
        runner.invoke(
            saved_query_group,
            ["save", "--name", "cleanup", "--sql", "SELECT 1"],
            obj={"config_dir": tmp_path},
        )
        delete_result = runner.invoke(
            saved_query_group,
            ["delete", "--force", "cleanup"],
            obj={"config_dir": tmp_path},
        )
        assert delete_result.exit_code == 0
        assert "Deleted saved query 'cleanup'." in delete_result.output
        list_result = runner.invoke(
            saved_query_group,
            ["list"],
            obj={"config_dir": tmp_path},
        )
        assert "cleanup" not in list_result.output


    def test_delete_multiple_saved_queries(self, tmp_path: Path) -> None:
        runner = CliRunner()
        runner.invoke(saved_query_group, ["save", "--name", "one", "--sql", "SELECT 1"], obj={"config_dir": tmp_path})
        runner.invoke(saved_query_group, ["save", "--name", "two", "--sql", "SELECT 2"], obj={"config_dir": tmp_path})
        result = runner.invoke(
            saved_query_group,
            ["delete", "--force", "one, two"],
            obj={"config_dir": tmp_path},
        )
        assert result.exit_code == 0
        assert "Deleted saved queries: one, two" in result.output
        list_result = runner.invoke(saved_query_group, ["list"], obj={"config_dir": tmp_path})
        assert "one" not in list_result.output
        assert "two" not in list_result.output

    def test_delete_all_saved_queries(self, tmp_path: Path) -> None:
        runner = CliRunner()
        runner.invoke(saved_query_group, ["save", "--name", "one", "--sql", "SELECT 1"], obj={"config_dir": tmp_path})
        runner.invoke(saved_query_group, ["save", "--name", "two", "--sql", "SELECT 2"], obj={"config_dir": tmp_path})
        result = runner.invoke(
            saved_query_group,
            ["delete", "--force", "All"],
            obj={"config_dir": tmp_path},
        )
        assert result.exit_code == 0
        assert "Deleted saved queries:" in result.output
        list_result = runner.invoke(saved_query_group, ["list"], obj={"config_dir": tmp_path})
        assert "one" not in list_result.output
        assert "two" not in list_result.output

    def test_run_dispatches_to_query_command(self, tmp_path: Path) -> None:
        runner = CliRunner()
        runner.invoke(
            saved_query_group,
            ["save", "--name", "runme", "--sql", "SELECT 1"],
            obj={"config_dir": tmp_path},
        )
        with patch("opendental_query.cli.query_cmd.query_command") as mock_query:
            run_result = runner.invoke(
                saved_query_group,
                ["run", "runme", "--export"],
                obj={"config_dir": tmp_path},
            )
            assert run_result.exit_code == 0
            mock_query.assert_called_once()
            kwargs = mock_query.call_args.kwargs
            assert kwargs["saved_query"] == "runme"
            assert kwargs["export_results"] is True

    def test_delete_interactive(self, tmp_path: Path) -> None:
        runner = CliRunner()
        runner.invoke(
            saved_query_group,
            ["save", "--name", "remove_me", "--sql", "SELECT 1"],
            obj={"config_dir": tmp_path},
        )
        result = runner.invoke(
            saved_query_group,
            ["deleteinteractive"],
            obj={"config_dir": tmp_path},
            input="remove_me\n",
        )
        assert result.exit_code == 0
        assert "Deleted saved query 'remove_me'." in result.output
        list_result = runner.invoke(
            saved_query_group,
            ["list"],
            obj={"config_dir": tmp_path},
        )
        assert "remove_me" not in list_result.output

    def test_delete_interactive_all(self, tmp_path: Path) -> None:
        runner = CliRunner()
        runner.invoke(saved_query_group, ["save", "--name", "one", "--sql", "SELECT 1"], obj={"config_dir": tmp_path})
        runner.invoke(saved_query_group, ["save", "--name", "two", "--sql", "SELECT 2"], obj={"config_dir": tmp_path})
        result = runner.invoke(
            saved_query_group,
            ["deleteinteractive"],
            obj={"config_dir": tmp_path},
            input="All\n",
        )
        assert result.exit_code == 0
        assert "Deleted saved queries:" in result.output
        list_result = runner.invoke(saved_query_group, ["list"], obj={"config_dir": tmp_path})
        assert "one" not in list_result.output
        assert "two" not in list_result.output


def test_shortcut_entry_invokes_cli(monkeypatch) -> None:
    monkeypatch.setattr(sys, "argv", ["QuerySave"])
    with patch("opendental_query.cli.main.cli.main") as mock_main:
        shortcut_save_query()
        mock_main.assert_called_once_with(args=["saved-query", "savesimple"])


def test_shortcut_entry_list_invokes_cli(monkeypatch) -> None:
    monkeypatch.setattr(sys, "argv", ["QuerySave", "List"])
    with patch("opendental_query.cli.main.cli.main") as mock_main:
        shortcut_save_query()
        mock_main.assert_called_with(args=["saved-query", "list", "--show-sql"])


def test_shortcut_entry_delete_invokes_cli(monkeypatch) -> None:
    monkeypatch.setattr(sys, "argv", ["QuerySave", "Delete"])
    with patch("opendental_query.cli.main.cli.main") as mock_main:
        shortcut_save_query()
        mock_main.assert_called_with(args=["saved-query", "deleteinteractive"])


def test_shortcut_entry_run_invokes_cli() -> None:
    with patch("opendental_query.cli.main.cli.main") as mock_main:
        with patch.object(sys, "argv", ["QuerySave", "My", "Query"]):
            shortcut_save_query()
    mock_main.assert_called_with(args=["saved-query", "run", "My Query"])
