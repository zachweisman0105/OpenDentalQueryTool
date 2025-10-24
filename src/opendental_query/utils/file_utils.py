"""File utility functions for safe file operations."""

import json
from pathlib import Path
from typing import Any

from opendental_query.constants import EXIT_FILE_ERROR, EXIT_PERMISSION_ERROR


def ensure_directory(path: Path, *, mode: int = 0o700) -> None:
    """Ensure a directory exists with secure permissions.

    Creates the directory and all parent directories if they don't exist.
    Sets restrictive permissions (700 by default) for security.

    Args:
        path: Path to the directory to create
        mode: Permission mode for the directory (default: 0o700 - owner only)

    Raises:
        SystemExit: If directory creation fails
    """
    try:
        path.mkdir(mode=mode, parents=True, exist_ok=True)
    except PermissionError as e:
        import sys

        from opendental_query.utils.app_logger import get_logger

        logger = get_logger(__name__)
        logger.error(f"Permission denied creating directory {path}: {e}")
        sys.exit(EXIT_PERMISSION_ERROR)
    except OSError as e:
        import sys

        from opendental_query.utils.app_logger import get_logger

        logger = get_logger(__name__)
        logger.error(f"Failed to create directory {path}: {e}")
        sys.exit(EXIT_FILE_ERROR)


def read_json_file(path: Path) -> dict[str, Any]:
    """Read and parse a JSON file.

    Args:
        path: Path to the JSON file to read

    Returns:
        Parsed JSON data as a dictionary

    Raises:
        SystemExit: If file cannot be read or parsed
    """
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        import sys

        from opendental_query.utils.app_logger import get_logger

        logger = get_logger(__name__)
        logger.error(f"File not found: {path}")
        sys.exit(EXIT_FILE_ERROR)
    except PermissionError as e:
        import sys

        from opendental_query.utils.app_logger import get_logger

        logger = get_logger(__name__)
        logger.error(f"Permission denied reading {path}: {e}")
        sys.exit(EXIT_PERMISSION_ERROR)
    except json.JSONDecodeError as e:
        import sys

        from opendental_query.utils.app_logger import get_logger

        logger = get_logger(__name__)
        logger.error(f"Invalid JSON in {path}: {e}")
        sys.exit(EXIT_FILE_ERROR)
    except OSError as e:
        import sys

        from opendental_query.utils.app_logger import get_logger

        logger = get_logger(__name__)
        logger.error(f"Failed to read {path}: {e}")
        sys.exit(EXIT_FILE_ERROR)


def write_json_file(path: Path, data: dict[str, Any], *, mode: int = 0o600) -> None:
    """Write data to a JSON file with secure permissions.

    Args:
        path: Path to the JSON file to write
        data: Data to serialize to JSON
        mode: Permission mode for the file (default: 0o600 - owner read/write only)

    Raises:
        SystemExit: If file cannot be written
    """
    try:
        # Ensure parent directory exists
        ensure_directory(path.parent)

        # Write to temporary file first for atomic operation
        temp_path = path.with_suffix(".tmp")

        with temp_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        # Set secure permissions before moving
        temp_path.chmod(mode)

        # Atomic rename
        temp_path.replace(path)

    except PermissionError as e:
        import sys

        from opendental_query.utils.app_logger import get_logger

        logger = get_logger(__name__)
        logger.error(f"Permission denied writing {path}: {e}")
        sys.exit(EXIT_PERMISSION_ERROR)
    except OSError as e:
        import sys

        from opendental_query.utils.app_logger import get_logger

        logger = get_logger(__name__)
        logger.error(f"Failed to write {path}: {e}")
        sys.exit(EXIT_FILE_ERROR)
