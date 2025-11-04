"""Unit tests for file utility functions."""

import json
from pathlib import Path

import pytest

from opendental_query.constants import EXIT_FILE_ERROR, EXIT_PERMISSION_ERROR
from opendental_query.utils.file_utils import (
    ensure_directory,
    read_json_file,
    write_json_file,
)


class TestEnsureDirectory:
    """Tests for ensure_directory function."""

    def test_create_new_directory(self, tmp_path: Path) -> None:
        """Test creating a new directory."""
        test_dir = tmp_path / "test_dir"
        ensure_directory(test_dir)

        assert test_dir.exists()
        assert test_dir.is_dir()

    def test_create_nested_directories(self, tmp_path: Path) -> None:
        """Test creating nested directories."""
        test_dir = tmp_path / "level1" / "level2" / "level3"
        ensure_directory(test_dir)

        assert test_dir.exists()
        assert test_dir.is_dir()

    def test_existing_directory(self, tmp_path: Path) -> None:
        """Test that existing directory doesn't cause error."""
        test_dir = tmp_path / "existing"
        test_dir.mkdir()

        # Should not raise error
        ensure_directory(test_dir)
        assert test_dir.exists()

    def test_directory_permissions(self, tmp_path: Path) -> None:
        """Test that directory is created with secure permissions."""
        import stat

        test_dir = tmp_path / "secure_dir"
        ensure_directory(test_dir, mode=0o700)

        # Check permissions (on Unix-like systems)
        if hasattr(stat, "S_IMODE"):
            mode = stat.S_IMODE(test_dir.stat().st_mode)
            # Check owner has rwx, others have none
            assert mode & 0o700 == 0o700


class TestReadJsonFile:
    """Tests for read_json_file function."""

    def test_read_valid_json(self, tmp_path: Path) -> None:
        """Test reading a valid JSON file."""
        test_file = tmp_path / "test.json"
        test_data = {"key": "value", "number": 42}

        with test_file.open("w", encoding="utf-8") as f:
            json.dump(test_data, f)

        result = read_json_file(test_file)
        assert result == test_data

    def test_read_nonexistent_file(self, tmp_path: Path) -> None:
        """Test that reading nonexistent file raises SystemExit."""
        test_file = tmp_path / "nonexistent.json"

        with pytest.raises(SystemExit) as exc_info:
            read_json_file(test_file)

        assert exc_info.value.code == EXIT_FILE_ERROR

    def test_read_invalid_json(self, tmp_path: Path) -> None:
        """Test that invalid JSON raises SystemExit."""
        test_file = tmp_path / "invalid.json"

        with test_file.open("w", encoding="utf-8") as f:
            f.write("{ invalid json }")

        with pytest.raises(SystemExit) as exc_info:
            read_json_file(test_file)

        assert exc_info.value.code == EXIT_FILE_ERROR

    def test_read_complex_json(self, tmp_path: Path) -> None:
        """Test reading complex nested JSON."""
        test_file = tmp_path / "complex.json"
        test_data = {
            "offices": {
                "office1": {"host": "localhost", "port": 3306},
                "office2": {"host": "192.168.1.100", "port": 3307},
            },
            "settings": {"timeout": 300, "enabled": True},
        }

        with test_file.open("w", encoding="utf-8") as f:
            json.dump(test_data, f)

        result = read_json_file(test_file)
        assert result == test_data


class TestWriteJsonFile:
    """Tests for write_json_file function."""

    def test_write_valid_json(self, tmp_path: Path) -> None:
        """Test writing valid JSON to file."""
        test_file = tmp_path / "output.json"
        test_data = {"key": "value", "number": 42}

        write_json_file(test_file, test_data)

        assert test_file.exists()

        # Verify content
        with test_file.open("r", encoding="utf-8") as f:
            result = json.load(f)

        assert result == test_data

    def test_write_creates_directory(self, tmp_path: Path) -> None:
        """Test that write creates parent directories."""
        test_file = tmp_path / "subdir" / "output.json"
        test_data = {"test": "data"}

        # Parent directory doesn't exist yet
        assert not test_file.parent.exists()

        write_json_file(test_file, test_data)

        assert test_file.exists()
        assert test_file.parent.exists()

    def test_write_file_permissions(self, tmp_path: Path) -> None:
        """Test that file is created with secure permissions."""
        import stat

        test_file = tmp_path / "secure.json"
        test_data = {"secret": "data"}

        write_json_file(test_file, test_data, mode=0o600)

        # Check permissions (on Unix-like systems)
        if hasattr(stat, "S_IMODE"):
            mode = stat.S_IMODE(test_file.stat().st_mode)
            # Check owner has rw, others have none
            assert mode & 0o600 == 0o600

    def test_write_atomic_operation(self, tmp_path: Path) -> None:
        """Test that write uses atomic rename operation."""
        test_file = tmp_path / "atomic.json"
        test_data = {"version": 1}

        # Write initial data
        write_json_file(test_file, test_data)

        # Overwrite with new data
        new_data = {"version": 2}
        write_json_file(test_file, new_data)

        # Verify final content
        with test_file.open("r", encoding="utf-8") as f:
            result = json.load(f)

        assert result == new_data

        # Temporary file should not exist
        temp_file = test_file.with_suffix(".tmp")
        assert not temp_file.exists()

    def test_write_pretty_format(self, tmp_path: Path) -> None:
        """Test that JSON is written with indentation."""
        test_file = tmp_path / "pretty.json"
        test_data = {"key": "value"}

        write_json_file(test_file, test_data)

        # Check that file has indentation
        content = test_file.read_text()
        assert "\n" in content  # Should have newlines from indentation


class TestRoundTrip:
    """Tests for read/write round-trip operations."""

    def test_read_write_roundtrip(self, tmp_path: Path) -> None:
        """Test that data survives read/write cycle."""
        test_file = tmp_path / "roundtrip.json"
        original_data = {
            "string": "test",
            "number": 123,
            "boolean": True,
            "null": None,
            "array": [1, 2, 3],
            "object": {"nested": "value"},
        }

        # Write data
        write_json_file(test_file, original_data)

        # Read it back
        result = read_json_file(test_file)

        # Should be identical
        assert result == original_data


class TestFileUtilsErrorHandling:
    """Additional error-handling scenarios for file utilities."""

    def test_ensure_directory_permission_error(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mock_logger: list[tuple[str, str]]
    ) -> None:
        """Permission errors should exit with the correct code and log a message."""
        target = tmp_path / "denied"

        def _raise_permission(self, *args: object, **kwargs: object) -> None:
            raise PermissionError("no access")

        monkeypatch.setattr(Path, "mkdir", _raise_permission)

        with pytest.raises(SystemExit) as exc:
            ensure_directory(target)

        assert exc.value.code == EXIT_PERMISSION_ERROR
        assert any("Permission denied" in message for _, message in mock_logger)

    def test_ensure_directory_oserror(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mock_logger: list[tuple[str, str]]
    ) -> None:
        """Generic OS errors should surface as file errors."""
        target = tmp_path / "broken"

        def _raise_oserror(self, *args: object, **kwargs: object) -> None:
            raise OSError("disk full")

        monkeypatch.setattr(Path, "mkdir", _raise_oserror)

        with pytest.raises(SystemExit) as exc:
            ensure_directory(target)

        assert exc.value.code == EXIT_FILE_ERROR
        assert any("Failed to create directory" in message for _, message in mock_logger)

    def test_read_json_permission_error(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mock_logger: list[tuple[str, str]]
    ) -> None:
        """Permission issues when reading should map to permission exit codes."""
        target = tmp_path / "data.json"

        def _raise_open(*args: object, **kwargs: object) -> None:
            raise PermissionError("locked down")

        monkeypatch.setattr(Path, "open", _raise_open)

        with pytest.raises(SystemExit) as exc:
            read_json_file(target)

        assert exc.value.code == EXIT_PERMISSION_ERROR
        assert any("Permission denied reading" in message for _, message in mock_logger)

    def test_write_json_permission_error(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mock_logger: list[tuple[str, str]]
    ) -> None:
        """Permission errors when writing should be surfaced with proper exit code."""
        target = tmp_path / "output.json"

        def _raise_open(*args: object, **kwargs: object) -> None:
            raise PermissionError("cannot write")

        monkeypatch.setattr(Path, "open", _raise_open)

        with pytest.raises(SystemExit) as exc:
            write_json_file(target, {"k": "v"})

        assert exc.value.code == EXIT_PERMISSION_ERROR
        assert any("Permission denied writing" in message for _, message in mock_logger)

    def test_write_json_oserror(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mock_logger: list[tuple[str, str]]
    ) -> None:
        """Unexpected OS errors on write should map to file error exit code."""
        target = tmp_path / "output.json"

        def _raise_oserror(*args: object, **kwargs: object) -> None:
            raise OSError("disk failure")

        monkeypatch.setattr(Path, "open", _raise_oserror)

        with pytest.raises(SystemExit) as exc:
            write_json_file(target, {"k": "v"})

        assert exc.value.code == EXIT_FILE_ERROR
        assert any("Failed to write" in message for _, message in mock_logger)
