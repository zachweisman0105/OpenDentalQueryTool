"""Utilities for formatting values for display/export."""

from __future__ import annotations

from datetime import date, datetime, time
from typing import Any


def _normalize_iso_string(value: str) -> str:
    """Prepare ISO-like strings for datetime parsing."""
    stripped = value.strip()
    if not stripped:
        return stripped
    if stripped.endswith("Z"):
        # datetime.fromisoformat doesn't understand Z directly
        stripped = stripped[:-1] + "+00:00"
    return stripped


def _try_parse_datetime(value: str) -> datetime | None:
    """Attempt to parse a value into a datetime object."""
    normalized = _normalize_iso_string(value)
    if not normalized:
        return None

    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        pass

    # Fallbacks for common SQL/MySQL timestamp formats
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(normalized, fmt)
        except ValueError:
            continue
    return None


def _is_midnight(dt: datetime) -> bool:
    """Return True when datetime has an all-zero time component."""
    return dt.time().replace(microsecond=0) == time(0, 0)


def format_cell_value(value: Any) -> str:
    """
    Format raw query values for display/export.

    - Datetime strings/objects with zero time → MM-DD-YYYY
    - Datetime strings/objects with non-zero time → original ISO-like repr
    - Date objects → MM-DD-YYYY
    - Other values → stringified as-is
    """
    if value is None:
        return ""

    if isinstance(value, datetime):
        if _is_midnight(value):
            return value.strftime("%m-%d-%Y")
        return value.isoformat(timespec="seconds")

    if isinstance(value, date):
        return value.strftime("%m-%d-%Y")

    if isinstance(value, str):
        parsed = _try_parse_datetime(value)
        if parsed is not None:
            if _is_midnight(parsed):
                return parsed.strftime("%m-%d-%Y")
            # Preserve the original formatting when time is meaningful
            return value
        return value

    return str(value)
