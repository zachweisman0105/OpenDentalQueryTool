"""Tests for the encrypted query history database."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from openpyxl import Workbook

from opendental_query.utils.query_history_db import CSV_ENCODING, QueryHistoryDatabase


def _create_sample_rows() -> list[dict[str, str]]:
    return [
        {"Office": "A1", "Value": "10"},
        {"Office": "B2", "Value": "12"},
    ]


def test_record_query_result_creates_tables(tmp_config_dir: Path) -> None:
    db = QueryHistoryDatabase(tmp_config_dir)
    sql = "SELECT Office, Value FROM sample"
    columns = ["Office", "Value"]
    rows = _create_sample_rows()

    inserted = db.record_query_result(sql, columns, rows, source="test", metadata={"note": "initial"})
    assert inserted == 2

    queries = db.list_queries()
    assert len(queries) == 1
    assert queries[0]["query_text"] == sql

    runs = db.list_runs()
    assert len(runs) == 1
    stored_metadata = json.loads(runs[0]["metadata"])
    assert stored_metadata["row_count"] == 2
    assert stored_metadata["source"] == "test"
    assert stored_metadata["note"] == "initial"


def test_record_query_result_uses_saved_query_name_for_table(tmp_config_dir: Path) -> None:
    db = QueryHistoryDatabase(tmp_config_dir)
    sql = "SELECT Office, Value FROM sample"
    columns = ["Office", "Value"]
    rows = _create_sample_rows()

    db.record_query_result(
        sql,
        columns,
        rows,
        source="query-run",
        metadata={"saved_query": "Monthly Summary"},
    )

    queries = db.list_queries()
    assert queries[0]["sanitized_table"] == "monthly_summary"

    columns_loaded, rows_loaded = db._load_query_rows(sql)
    assert columns_loaded == columns
    assert [tuple(row) for row in rows_loaded]  # data persisted


def test_saved_query_table_name_collision_gets_suffix(tmp_config_dir: Path) -> None:
    db = QueryHistoryDatabase(tmp_config_dir)
    sql = "SELECT 1"
    columns = ["Value"]
    rows = [{"Value": "x"}]

    db.record_query_result(
        sql,
        columns,
        rows,
        source="query-run",
        metadata={"saved_query": "queries"},
    )

    queries = db.list_queries()
    sanitized = queries[0]["sanitized_table"]
    assert sanitized != "queries"
    assert sanitized.startswith("queries_")


def test_record_query_result_appends_for_same_schema(tmp_config_dir: Path) -> None:
    db = QueryHistoryDatabase(tmp_config_dir)
    sql = "SELECT Office, Value FROM sample"
    columns = ["Office", "Value"]
    rows = _create_sample_rows()

    db.record_query_result(sql, columns, rows, source="test", metadata=None)
    db.record_query_result(sql, columns, rows, source="test", metadata=None)

    runs = db.list_runs(sql)
    assert len(runs) == 2
    row_counts = [json.loads(run["metadata"])["row_count"] for run in runs]
    assert row_counts == [2, 2]


def test_record_query_result_rejects_schema_changes(tmp_config_dir: Path) -> None:
    db = QueryHistoryDatabase(tmp_config_dir)
    sql = "SELECT Office, Value FROM sample"

    db.record_query_result(sql, ["Office", "Value"], _create_sample_rows(), source="test", metadata=None)

    with pytest.raises(ValueError, match="Column mismatch"):
        db.record_query_result(
            sql,
            ["Office", "DifferentColumn"],
            [{"Office": "A1", "DifferentColumn": "X"}],
            source="test",
            metadata=None,
        )


def test_import_csv(tmp_config_dir: Path, tmp_path: Path) -> None:
    db = QueryHistoryDatabase(tmp_config_dir)
    sql = "SELECT Office, Value FROM sample"

    csv_file = tmp_path / "sample.csv"
    csv_file.write_text("Office,Value\nA1,10\nB2,12\n", encoding=CSV_ENCODING)

    inserted = db.import_csv(sql, csv_file)
    assert inserted == 2

    runs = db.list_runs(sql)
    assert len(runs) == 1
    metadata = json.loads(runs[0]["metadata"])
    assert metadata["source_file"].endswith("sample.csv")
    assert metadata["source"] == "csv"


def test_import_excel(tmp_config_dir: Path, tmp_path: Path) -> None:
    db = QueryHistoryDatabase(tmp_config_dir)
    sql = "SELECT Office, Value FROM sample"

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Data"
    sheet.append(["Office", "Value"])
    sheet.append(["A1", 10])
    sheet.append(["B2", 12])

    excel_path = tmp_path / "sample.xlsx"
    workbook.save(excel_path)

    inserted = db.import_excel(sql, excel_path, sheet_name="Data")
    assert inserted == 2

    runs = db.list_runs(sql)
    assert len(runs) == 1
    metadata = json.loads(runs[0]["metadata"])
    assert metadata["source"] == "excel"
    assert metadata["sheet_name"] == "Data"
