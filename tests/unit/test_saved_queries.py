"""Tests for SavedQueryLibrary."""

from pathlib import Path

import pytest

from opendental_query.utils.saved_queries import SavedQueryLibrary


class TestSavedQueryLibrary:
    def test_save_and_get_query(self, tmp_path: Path) -> None:
        library = SavedQueryLibrary(tmp_path)
        saved = library.save_query(
            "monthly_report",
            "SELECT * FROM patient",
            description="Monthly patient export",
            default_offices=["office1", "office2"],
        )

        assert saved.name == "monthly_report"
        fetched = library.get_query("monthly_report")
        assert fetched.sql == "SELECT * FROM patient"
        assert fetched.description == "Monthly patient export"
        assert fetched.default_offices == ["office1", "office2"]

    def test_save_query_prevents_overwrite(self, tmp_path: Path) -> None:
        library = SavedQueryLibrary(tmp_path)
        library.save_query("report", "SELECT 1")
        with pytest.raises(ValueError):
            library.save_query("report", "SELECT 2")

    def test_save_query_with_overwrite(self, tmp_path: Path) -> None:
        library = SavedQueryLibrary(tmp_path)
        library.save_query("report", "SELECT 1")
        updated = library.save_query("report", "SELECT 2", overwrite=True)
        assert updated.sql == "SELECT 2"

    def test_delete_query(self, tmp_path: Path) -> None:
        library = SavedQueryLibrary(tmp_path)
        library.save_query("to_delete", "SELECT 1")
        library.delete_query("to_delete")
        with pytest.raises(KeyError):
            library.get_query("to_delete")

    def test_delete_multiple_queries(self, tmp_path: Path) -> None:
        library = SavedQueryLibrary(tmp_path)
        library.save_query("one", "SELECT 1")
        library.save_query("two", "SELECT 2")
        removed = library.delete_queries(["one", "two"])
        assert removed == ["one", "two"]
        assert library.list_queries() == []

    def test_delete_queries_missing_raises(self, tmp_path: Path) -> None:
        library = SavedQueryLibrary(tmp_path)
        library.save_query("one", "SELECT 1")
        with pytest.raises(KeyError):
            library.delete_queries(["missing"])

    def test_list_queries_sorted(self, tmp_path: Path) -> None:
        library = SavedQueryLibrary(tmp_path)
        library.save_query("b_query", "SELECT 2")
        library.save_query("a_query", "SELECT 1")
        names = [item.name for item in library.list_queries()]
        assert names == ["a_query", "b_query"]

    def test_blank_name_rejected(self, tmp_path: Path) -> None:
        library = SavedQueryLibrary(tmp_path)
        with pytest.raises(ValueError):
            library.save_query("   ", "SELECT 1")

    def test_rename_office_updates_default_offices(self, tmp_path: Path) -> None:
        library = SavedQueryLibrary(tmp_path)
        library.save_query(
            "report",
            "SELECT 1",
            default_offices=["office1", "office2"],
        )
        library.save_query(
            "other",
            "SELECT 2",
            default_offices=["office3"],
        )

        updated = library.rename_office("office1", "main-office")

        assert updated == 1
        assert library.get_query("report").default_offices == ["main-office", "office2"]
        assert library.get_query("other").default_offices == ["office3"]

    def test_rename_office_returns_zero_when_not_found(self, tmp_path: Path) -> None:
        library = SavedQueryLibrary(tmp_path)
        library.save_query("report", "SELECT 1", default_offices=["office1"])

        updated = library.rename_office("missing", "new-name")

        assert updated == 0
        assert library.get_query("report").default_offices == ["office1"]
