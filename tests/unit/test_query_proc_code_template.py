"""Tests for procedure code template helper."""


from pathlib import Path

import click
import pytest
from click import ClickException

from opendental_query.cli import query_cmd as query_cmd_module
from opendental_query.cli.query_cmd import _load_and_update_proc_code_template


def _write_template(path: Path, content: str) -> Path:
    path.write_text(content, encoding="utf-8")
    return path


def test_prepare_template_substitutes_code_without_modifying_file(tmp_path: Path) -> None:
    """Should emit SQL with the requested code while leaving the file unchanged."""
    template = _write_template(
        tmp_path / "QueryProcCode SQL.txt",
        """-- Replace 'D1110' with your target procedure code
SELECT * FROM procedurecode WHERE pc.ProcCode = 'D1110';""",
    )

    sql, path, previous = _load_and_update_proc_code_template("d0120", template_path=template)

    assert previous == "D1110"
    assert path == template
    assert "D0120" in sql
    original = template.read_text(encoding="utf-8")
    assert "'D1110'" in original
    assert "'D0120'" not in original


def test_load_and_update_template_rejects_invalid_code(tmp_path: Path) -> None:
    """Non-alphanumeric codes should be rejected."""
    template = _write_template(
        tmp_path / "QueryProcCode SQL.txt",
        "SELECT * FROM procedurecode WHERE pc.ProcCode = 'D1110';",
    )

    with pytest.raises(ClickException) as exc:
        _load_and_update_proc_code_template("D01-20", template_path=template)

    assert "letters and numbers" in str(exc.value)


def test_load_and_update_template_missing_assignment(tmp_path: Path) -> None:
    """Files without the expected pc.ProcCode assignment should raise an error."""
    template = _write_template(tmp_path / "QueryProcCode SQL.txt", "SELECT 1;")

    with pytest.raises(ClickException) as exc:
        _load_and_update_proc_code_template("D0120", template_path=template)

    assert "pc.ProcCode" in str(exc.value)


def test_load_and_update_template_missing_file(tmp_path: Path) -> None:
    """Missing files should result in a friendly ClickException."""
    missing = tmp_path / "missing.sql"

    with pytest.raises(ClickException) as exc:
        _load_and_update_proc_code_template("D0120", template_path=missing)

    assert "Template SQL file not found" in str(exc.value)


def test_default_path_prefers_project_root(monkeypatch, tmp_path: Path) -> None:
    """When no path is provided, the project root template should be located."""
    fake_cli_dir = tmp_path / "src" / "opendental_query" / "cli"
    fake_cli_dir.mkdir(parents=True)
    fake_file = fake_cli_dir / "query_cmd.py"
    fake_file.write_text("", encoding="utf-8")

    template = tmp_path / "QueryProcCode SQL.txt"
    template.write_text(
        "SELECT * FROM procedurecode WHERE pc.ProcCode = 'D1110';",
        encoding="utf-8",
    )

    monkeypatch.setattr(query_cmd_module, "__file__", str(fake_file))

    sql, path, previous = query_cmd_module._load_and_update_proc_code_template("D0120")

    assert path == template
    assert previous == "D1110"
    assert "D0120" in sql
    assert "'D1110'" in template.read_text(encoding="utf-8")


def test_query_proc_code_command_invokes_query(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """The command should emit user feedback and delegate to query_command with expected kwargs."""

    def _fake_loader(code: str, template_path: Path | None = None):
        return ("SELECT 1", tmp_path / "QueryProcCode SQL.txt", "D1110")

    monkeypatch.setattr(query_cmd_module, "_load_and_update_proc_code_template", _fake_loader)

    printed: list[str] = []

    class _DummyConsole:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def print(self, *args, **kwargs) -> None:
            text = args[0] if args else ""
            printed.append(str(text))

    monkeypatch.setattr(query_cmd_module, "Console", _DummyConsole)

    captured: dict[str, object] = {}

    class _DummyContext(click.Context):
        def __init__(self) -> None:
            super().__init__(query_cmd_module.query_proc_code_command)

        def invoke(self, callback, *args, **kwargs):
            captured["callback"] = callback
            captured["kwargs"] = kwargs
            return None

    ctx = _DummyContext()

    with ctx:
        query_cmd_module.query_proc_code_command.callback(
            code="D0120",
            offices=None,
            timeout=300,
            max_concurrent=10,
            export_results=False,
        )

    assert any("Running query for procedure code D0120" in message for message in printed)
    assert captured["callback"] is query_cmd_module.query_command
    assert captured["kwargs"] == {
        "saved_query": None,
        "sql": "SELECT 1",
        "offices": None,
        "timeout": 300,
        "max_concurrent": 10,
        "export_results": False,
    }
