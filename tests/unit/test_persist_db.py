"""Tests for PersistDatabase."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from opendental_query.utils.persist_db import PersistDatabase


class TestPersistDatabase:
    def test_creates_encrypted_database(self, tmp_path: Path) -> None:
        db = PersistDatabase(tmp_path)
        inserted = db.append_table(
            table_name="RecentAppointments",
            columns=["Office", "ApptDate"],
            rows=[{"Office": "office1", "ApptDate": "2025-10-25"}],
        )
        assert inserted == 1

        persist_path = tmp_path / "persist.db.enc"
        assert persist_path.exists()
        raw_bytes = persist_path.read_bytes()
        assert raw_bytes  # file not empty

        with db._open_mutable_database() as conn:  # type: ignore[attr-defined]
            cursor = conn.execute('SELECT "Office", "ApptDate" FROM "recentappointments"')
            row = cursor.fetchone()
            assert row == ("office1", "2025-10-25")

    def test_column_mismatch_raises(self, tmp_path: Path) -> None:
        db = PersistDatabase(tmp_path)
        db.append_table(
            table_name="RecentAppointments",
            columns=["Office", "ApptDate"],
            rows=[{"Office": "office1", "ApptDate": "2025-10-25"}],
        )

        with pytest.raises(ValueError):
            db.append_table(
                table_name="RecentAppointments",
                columns=["Office", "Doctor"],
                rows=[{"Office": "office1", "Doctor": "Smith"}],
            )

