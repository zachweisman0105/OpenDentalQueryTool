"""Tests for the primary CLI entry point and alias handling."""

from click.testing import CliRunner

from opendental_query.cli.main import cli


def test_query_proccode_alias_exposes_command(tmp_path) -> None:
    """The QueryProcCode shortcut should map to the query-proc-code command."""
    runner = CliRunner()
    env = {"OPENDENTAL_CONFIG_DIR": str(tmp_path)}

    result = runner.invoke(cli, ["QueryProcCode", "--help"], env=env)

    assert result.exit_code == 0
    assert "Procedure code" in result.output
