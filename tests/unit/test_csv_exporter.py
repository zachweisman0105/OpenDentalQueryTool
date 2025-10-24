"""
Unit tests for CSVExporter.

Tests CSV export with random filenames, UTF-8 BOM encoding, CRLF line endings,
Downloads folder detection, and proper CSV formatting.
"""

import csv
import os
import sys
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from opendental_query.renderers.csv_exporter import CSVExporter

@pytest.fixture
def allow_unrestricted_exports(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("SPEC_KIT_ALLOW_UNSAFE_EXPORTS", "1")
    yield
    monkeypatch.delenv("SPEC_KIT_ALLOW_UNSAFE_EXPORTS", raising=False)
    monkeypatch.delenv("SPEC_KIT_EXPORT_ENCRYPTION_COMMAND", raising=False)
    monkeypatch.delenv("SPEC_KIT_EXPORT_ROOT", raising=False)



class TestFilenameGeneration:
    """Test random filename generation."""

    def test_generates_unique_filenames(self, allow_unrestricted_exports: None) -> None:
        """Should generate unique filenames with random tokens."""
        exporter = CSVExporter()

        # Generate multiple filenames
        filenames = [exporter._generate_filename() for _ in range(10)]

        # All should be unique
        assert len(set(filenames)) == 10

    def test_filename_format_includes_timestamp(self, allow_unrestricted_exports: None) -> None:
        """Should include timestamp in filename."""
        exporter = CSVExporter()
        filename = exporter._generate_filename()

        # Format: opendental_query_{token}_{timestamp}.csv
        assert filename.startswith("opendental_query_")
        assert filename.endswith(".csv")

        # Should have 3 parts separated by underscores
        parts = filename.replace(".csv", "").split("_")
        assert len(parts) >= 3  # opendental, query, token, timestamp parts

    def test_filename_uses_random_token(self, allow_unrestricted_exports: None) -> None:
        """Should use random token in filename."""
        exporter = CSVExporter()
        filename = exporter._generate_filename()

        # Extract token (between opendental_query_ and timestamp)
        assert "opendental_query_" in filename
        # Token should be alphanumeric
        assert any(char.isalnum() for char in filename)


class TestDownloadsFolderDetection:
    """Test Downloads folder detection and fallback."""

    def test_detects_downloads_folder(self, allow_unrestricted_exports: None) -> None:
        """Should detect user's Downloads folder."""
        exporter = CSVExporter()
        downloads_path = exporter._get_downloads_folder()

        # Should return a Path object
        assert isinstance(downloads_path, Path)

        # On Windows, typically C:\Users\{username}\Downloads
        # On Unix-like, typically /home/{username}/Downloads or ~/Downloads
        assert "Downloads" in str(downloads_path) or downloads_path == Path.cwd()

    def test_falls_back_to_cwd_if_downloads_not_found(self, allow_unrestricted_exports: None) -> None:
        """Should fall back to current directory if Downloads not found."""
        exporter = CSVExporter()

        with patch("pathlib.Path.home") as mock_home:
            # Mock home to return path without Downloads folder
            fake_home = Path(tempfile.gettempdir()) / "fake_home"
            mock_home.return_value = fake_home

            downloads_path = exporter._get_downloads_folder()

            # Should fall back to cwd
            assert downloads_path == Path.cwd()


class TestCSVEncoding:
    """Test CSV encoding with UTF-8 BOM."""

    def test_writes_utf8_bom(self, allow_unrestricted_exports: None) -> None:
        """Should write UTF-8 BOM at start of file."""
        exporter = CSVExporter()
        rows = [{"Office": "office1", "Name": "Smith"}]

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            filepath = exporter.export(rows, output_dir=output_dir)

            # Read raw bytes
            with open(filepath, "rb") as f:
                first_bytes = f.read(3)

            # UTF-8 BOM is EF BB BF
            assert first_bytes == b"\xef\xbb\xbf"

    def test_handles_unicode_characters(self, allow_unrestricted_exports: None) -> None:
        """Should correctly encode Unicode characters."""
        exporter = CSVExporter()
        rows = [
            {"Office": "office1", "Name": "Müller"},
            {"Office": "office2", "Name": "José"},
            {"Office": "office3", "Name": "北京"},
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            filepath = exporter.export(rows, output_dir=output_dir)

            # Read with UTF-8 encoding
            with open(filepath, encoding="utf-8-sig") as f:
                content = f.read()

            assert "Müller" in content
            assert "José" in content
            assert "北京" in content


class TestLineEndings:
    """Test CRLF line endings."""

    def test_uses_crlf_line_endings(self, allow_unrestricted_exports: None) -> None:
        """Should use CRLF (\\r\\n) line endings."""
        exporter = CSVExporter()
        rows = [
            {"Office": "office1", "Name": "Smith"},
            {"Office": "office2", "Name": "Jones"},
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            filepath = exporter.export(rows, output_dir=output_dir)

            # Read in binary mode to check line endings
            with open(filepath, "rb") as f:
                content = f.read()

            # Should contain CRLF
            assert b"\r\n" in content


class TestCSVFormatting:
    """Test CSV formatting with QUOTE_MINIMAL."""

    def test_uses_quote_minimal(self, allow_unrestricted_exports: None) -> None:
        """Should use QUOTE_MINIMAL quoting."""
        exporter = CSVExporter()
        rows = [
            {"Office": "office1", "Name": "Smith", "Balance": "100.50"},
            {"Office": "office2", "Name": "O'Brien", "Balance": "200.75"},
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            filepath = exporter.export(rows, output_dir=output_dir)

            with open(filepath, encoding="utf-8-sig") as f:
                lines = f.readlines()

            # O'Brien should be quoted (contains special char)
            content = "".join(lines)
            assert '"O\'Brien"' in content or "O'Brien" in content

            # Simple values should not be quoted
            # (though csv.QUOTE_MINIMAL may quote if needed)

    def test_writes_header_row(self, allow_unrestricted_exports: None) -> None:
        """Should write column headers as first row."""
        exporter = CSVExporter()
        rows = [
            {"Office": "office1", "PatNum": "1", "LName": "Smith"},
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            filepath = exporter.export(rows, output_dir=output_dir)

            with open(filepath, encoding="utf-8-sig", newline="") as f:
                reader = csv.DictReader(f)
                fieldnames = reader.fieldnames

            assert fieldnames == ["Office", "PatNum", "LName"]

    def test_writes_data_rows(self, allow_unrestricted_exports: None) -> None:
        """Should write all data rows correctly."""
        exporter = CSVExporter()
        rows = [
            {"Office": "office1", "PatNum": "1", "LName": "Smith"},
            {"Office": "office2", "PatNum": "2", "LName": "Jones"},
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            filepath = exporter.export(rows, output_dir=output_dir)

            with open(filepath, encoding="utf-8-sig", newline="") as f:
                reader = csv.DictReader(f)
                data_rows = list(reader)

            assert len(data_rows) == 2
            assert data_rows[0]["Office"] == "office1"
            assert data_rows[0]["LName"] == "Smith"
            assert data_rows[1]["Office"] == "office2"
            assert data_rows[1]["LName"] == "Jones"


class TestExportMethod:
    """Test export method behavior."""

    def test_returns_filepath(self, allow_unrestricted_exports: None) -> None:
        """Should return Path to exported file."""
        exporter = CSVExporter()
        rows = [{"Office": "office1", "Name": "Smith"}]

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            filepath = exporter.export(rows, output_dir=output_dir)

            # Should return Path object
            assert isinstance(filepath, Path)

            # File should exist
            assert filepath.exists()

            # Should be in output_dir
            assert filepath.parent == output_dir

    def test_uses_downloads_folder_by_default(self, allow_unrestricted_exports: None) -> None:
        """Should use Downloads folder when output_dir not specified."""
        exporter = CSVExporter()
        rows = [{"Office": "office1", "Name": "Smith"}]

        with patch.object(exporter, "_get_downloads_folder") as mock_downloads:
            mock_downloads_path = Path(tempfile.gettempdir()) / "Downloads"
            mock_downloads_path.mkdir(exist_ok=True)
            mock_downloads.return_value = mock_downloads_path

            filepath = exporter.export(rows)

            # Should have used Downloads folder
            assert filepath.parent == mock_downloads_path

            # Clean up
            if filepath.exists():
                filepath.unlink()

    def test_creates_output_directory_if_missing(self, allow_unrestricted_exports: None) -> None:
        """Should create output directory if it doesn't exist."""
        exporter = CSVExporter()
        rows = [{"Office": "office1", "Name": "Smith"}]

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "subdir" / "nested"

            # Directory doesn't exist yet
            assert not output_dir.exists()

            filepath = exporter.export(rows, output_dir=output_dir)

            # Directory should be created
            assert output_dir.exists()

            # File should exist
            assert filepath.exists()


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_handles_empty_rows_list(self, allow_unrestricted_exports: None) -> None:
        """Should handle empty rows list."""
        exporter = CSVExporter()
        rows: list[dict[str, Any]] = []

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)

            # Should either raise ValueError or create empty CSV
            with pytest.raises(ValueError, match="empty|no data"):
                exporter.export(rows, output_dir=output_dir)

    def test_handles_missing_columns_in_rows(self, allow_unrestricted_exports: None) -> None:
        """Should handle rows with missing columns."""
        exporter = CSVExporter()
        rows = [
            {"Office": "office1", "PatNum": "1", "LName": "Smith"},
            {"Office": "office2", "PatNum": "2"},  # Missing LName
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            filepath = exporter.export(rows, output_dir=output_dir)

            with open(filepath, encoding="utf-8-sig", newline="") as f:
                reader = csv.DictReader(f)
                data_rows = list(reader)

            # Second row should have empty LName
            assert data_rows[1]["Office"] == "office2"
            assert data_rows[1]["LName"] == ""

    def test_handles_none_values(self, allow_unrestricted_exports: None) -> None:
        """Should handle None values in cells."""
        exporter = CSVExporter()
        rows = [
            {"Office": "office1", "PatNum": None, "LName": "Smith"},
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            filepath = exporter.export(rows, output_dir=output_dir)

            with open(filepath, encoding="utf-8-sig", newline="") as f:
                reader = csv.DictReader(f)
                data_rows = list(reader)

            # None should be written as empty string
            assert data_rows[0]["PatNum"] == "" or data_rows[0]["PatNum"] == "None"

    def test_handles_special_characters_in_data(self, allow_unrestricted_exports: None) -> None:
        """Should properly escape special characters."""
        exporter = CSVExporter()
        rows = [
            {"Office": "office1", "Name": 'Smith, "Jr."', "Notes": "Line1\nLine2"},
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            filepath = exporter.export(rows, output_dir=output_dir)

            with open(filepath, encoding="utf-8-sig", newline="") as f:
                reader = csv.DictReader(f)
                data_rows = list(reader)

            # Should handle comma and quotes
            assert "Smith" in data_rows[0]["Name"]
            assert "Jr" in data_rows[0]["Name"]



class TestExportSecurity:
    """Tests enforcing secure export destinations and optional encryption."""

    def test_rejects_directory_outside_allowed_roots(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        monkeypatch.delenv("SPEC_KIT_ALLOW_UNSAFE_EXPORTS", raising=False)
        monkeypatch.delenv("SPEC_KIT_EXPORT_ROOT", raising=False)
        exporter = CSVExporter()
        rows = [{"Office": "office1", "Name": "Smith"}]
        with pytest.raises(ValueError):
            exporter.export(rows, output_dir=tmp_path / "untrusted")

    def test_allows_configured_export_root(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        safe_root = tmp_path / "approved"
        safe_root.mkdir()
        monkeypatch.setenv("SPEC_KIT_EXPORT_ROOT", str(safe_root))
        exporter = CSVExporter()
        rows = [{"Office": "office1", "Name": "Jones"}]
        filepath = exporter.export(rows, output_dir=safe_root)
        assert filepath.exists()

    def test_encryption_command_runs(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        monkeypatch.setenv("SPEC_KIT_ALLOW_UNSAFE_EXPORTS", "1")
        encrypt_script = tmp_path / "encrypt.py"
        encrypt_script.write_text(
            "import pathlib\n"
            "import sys\n"
            "path = pathlib.Path(sys.argv[1])\n"
            "path.write_text(path.read_text() + \'\\n#encrypted\')\n"
        )
        monkeypatch.setenv(
            "SPEC_KIT_EXPORT_ENCRYPTION_COMMAND",
            f"{sys.executable} {encrypt_script} {{input}}",
        )
        exporter = CSVExporter()
        rows = [{"Office": "office1", "Name": "Doe"}]
        filepath = exporter.export(rows, output_dir=tmp_path)
        assert filepath.read_text(encoding="utf-8-sig").endswith("#encrypted")
