"""Project-wide encoding safeguards.

This module is imported automatically by Python when it is discoverable on
``sys.path``.  By placing it in the repository root we ensure every developer
session and unit test run defaults to UTF-8 when reading text files, avoiding
Windows cp1252 decoding errors for resources such as README.md.
"""

from __future__ import annotations

import builtins
from pathlib import Path
from typing import Any, Optional

_original_open = builtins.open
_original_read_text = Path.read_text
_original_write_text = Path.write_text


def _utf8_open(
    file: Any,
    mode: str = "r",
    buffering: int = -1,
    encoding: Optional[str] = None,
    errors: Optional[str] = None,
    newline: Optional[str] = None,
    closefd: bool = True,
    opener: Any = None,
):
    """Wrap builtin open to default to UTF-8 for text mode."""
    if "b" not in mode and encoding is None:
        encoding = "utf-8"
    return _original_open(
        file,
        mode=mode,
        buffering=buffering,
        encoding=encoding,
        errors=errors,
        newline=newline,
        closefd=closefd,
        opener=opener,
    )


def _utf8_read_text(self: Path, encoding: Optional[str] = None, errors: Optional[str] = None) -> str:
    """Default Path.read_text to UTF-8."""
    if encoding is None:
        encoding = "utf-8"
    return _original_read_text(self, encoding=encoding, errors=errors)


def _utf8_write_text(
    self: Path,
    data: str,
    encoding: Optional[str] = None,
    errors: Optional[str] = None,
    newline: Optional[str] = None,
) -> int:
    """Default Path.write_text to UTF-8."""
    if encoding is None:
        encoding = "utf-8"
    return _original_write_text(self, data, encoding=encoding, errors=errors, newline=newline)


builtins.open = _utf8_open
Path.read_text = _utf8_read_text  # type: ignore[assignment]
Path.write_text = _utf8_write_text  # type: ignore[assignment]
