"""
Utility helpers for managing saved SQL queries on disk.

Provides a lightweight JSON-based library that stores named queries along with
optional descriptions and default office selections.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from opendental_query.constants import (
    DEFAULT_CONFIG_DIR,
    DEFAULT_SAVED_QUERIES_FILE,
)


@dataclass(slots=True)
class SavedQuery:
    """Represents a persisted SQL query definition."""

    name: str
    sql: str
    description: str | None = None
    default_offices: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


class SavedQueryLibrary:
    """Manages persistence of saved queries in the configuration directory."""

    def __init__(self, config_dir: Path | str = DEFAULT_CONFIG_DIR) -> None:
        self._config_dir = Path(config_dir)
        self._file_path = self._config_dir / DEFAULT_SAVED_QUERIES_FILE
        self._config_dir.mkdir(parents=True, exist_ok=True)
        if not self._file_path.exists():
            self._write_data({"queries": {}})

    def list_queries(self) -> list[SavedQuery]:
        """Return all saved queries sorted by name."""
        data = self._read_data()
        queries = [
            self._from_record(name, record) for name, record in data.get("queries", {}).items()
        ]
        return sorted(queries, key=lambda item: item.name.lower())

    def get_query(self, name: str) -> SavedQuery:
        """Return a saved query by name."""
        self._validate_name(name)
        data = self._read_data()
        record = data.get("queries", {}).get(name)
        if record is None:
            raise KeyError(f"Saved query '{name}' not found")
        return self._from_record(name, record)

    def save_query(
        self,
        name: str,
        sql: str,
        *,
        description: str | None = None,
        default_offices: list[str] | None = None,
        overwrite: bool = False,
    ) -> SavedQuery:
        """Persist a query definition."""
        self._validate_name(name)
        normalized_sql = sql.strip()
        if not normalized_sql:
            raise ValueError("SQL text cannot be empty")

        data = self._read_data()
        existing = data.get("queries", {}).get(name)
        if existing and not overwrite:
            raise ValueError(f"Saved query '{name}' already exists. Use overwrite=True to replace it.")

        timestamp = datetime.now(UTC).isoformat()
        created_at = existing.get("created_at", timestamp) if existing else timestamp

        payload: dict[str, Any] = {
            "sql": normalized_sql,
            "description": description,
            "default_offices": list(default_offices or []),
            "created_at": created_at,
            "updated_at": timestamp,
        }

        data.setdefault("queries", {})[name] = payload
        self._write_data(data)
        return self._from_record(name, payload)

    def delete_query(self, name: str) -> None:
        """Remove a saved query from the library."""
        self.delete_queries([name])

    def delete_queries(self, names: list[str]) -> list[str]:
        """Remove multiple saved queries from the library."""
        if not names:
            return []

        data = self._read_data()
        queries = data.get("queries", {})

        missing = [name for name in names if name not in queries]
        if missing:
            missing_str = ", ".join(missing)
            raise KeyError(f"Saved query '{missing_str}' not found")

        for name in names:
            del queries[name]

        self._write_data(data)
        return names

    def _read_data(self) -> dict[str, Any]:
        """Read and parse the saved queries file."""
        try:
            raw = self._file_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return {"queries": {}}

        if not raw.strip():
            return {"queries": {}}

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Saved query library is corrupted: {exc}") from exc
        if not isinstance(parsed, dict):
            raise ValueError("Saved query library has unexpected structure")
        parsed.setdefault("queries", {})
        if not isinstance(parsed["queries"], dict):
            raise ValueError("Saved query list must be an object mapping names to queries")
        return parsed

    def _write_data(self, data: dict[str, Any]) -> None:
        """Persist library data using an atomic write."""
        temp_path = self._file_path.with_suffix(".tmp")
        temp_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        temp_path.replace(self._file_path)

    def _from_record(self, name: str, record: dict[str, Any]) -> SavedQuery:
        """Convert raw JSON record to SavedQuery."""
        return SavedQuery(
            name=name,
            sql=str(record.get("sql", "")),
            description=record.get("description"),
            default_offices=list(record.get("default_offices") or []),
            created_at=str(record.get("created_at") or ""),
            updated_at=str(record.get("updated_at") or ""),
        )

    def _validate_name(self, name: str) -> None:
        """Ensure saved query names are present."""
        stripped = name.strip()
        if not stripped:
            raise ValueError("Saved query name cannot be empty")
