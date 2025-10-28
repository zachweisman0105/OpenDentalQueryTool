"""Encrypted SQLite persistence layer for saved query results."""

from __future__ import annotations

import json
import os
import shutil
import sqlite3
import tempfile
from pathlib import Path
from typing import Any

from cryptography.fernet import Fernet

from opendental_query.constants import DEFAULT_CONFIG_DIR

_METADATA_TABLE = "_metadata"


class PersistDatabase:
    """Manage encrypted SQLite database for persisted query results."""

    def __init__(self, config_dir: Path | None = None) -> None:
        self._config_dir = Path(config_dir or DEFAULT_CONFIG_DIR)
        self._config_dir.mkdir(parents=True, exist_ok=True)
        self._db_path = self._config_dir / "persist.db.enc"
        self._key_path = self._config_dir / "persist.key"
        self._fernet = Fernet(self._load_key())

    def append_table(
        self,
        table_name: str,
        columns: list[str],
        rows: list[dict[str, Any]],
    ) -> int:
        sanitized_table = self._sanitize_identifier(table_name)
        sanitized_columns = [self._sanitize_identifier(col) for col in columns]

        if not rows:
            return 0

        with self._open_mutable_database() as conn:
            cursor = conn.cursor()
            self._ensure_metadata_table(cursor)
            existing = self._fetch_table_metadata(cursor, table_name)

            if existing is None:
                self._create_new_table(cursor, table_name, sanitized_table, columns, sanitized_columns)
            else:
                stored_columns = json.loads(existing["columns"])
                if stored_columns != columns:
                    raise ValueError(
                        "Column mismatch: expected " + ", ".join(stored_columns)
                    )
                sanitized_columns = json.loads(existing["sanitized_columns"])

            placeholders = ", ".join(["?"] * len(columns))
            quoted_columns = ", ".join([f'"{col}"' for col in sanitized_columns])
            insert_sql = f'INSERT INTO "{sanitized_table}" ({quoted_columns}) VALUES ({placeholders})'

            to_insert = []
            for row in rows:
                to_insert.append([self._coerce_value(row.get(col)) for col in columns])

            cursor.executemany(insert_sql, to_insert)
            conn.commit()
            return len(to_insert)

    def _create_new_table(
        self,
        cursor: sqlite3.Cursor,
        table_name: str,
        sanitized_table: str,
        columns: list[str],
        sanitized_columns: list[str],
    ) -> None:
        column_defs = ", ".join([f'"{col}" TEXT' for col in sanitized_columns])
        cursor.execute(f'CREATE TABLE "{sanitized_table}" ({column_defs})')
        cursor.execute(
            f'INSERT INTO {_METADATA_TABLE} (table_name, sanitized_name, columns, sanitized_columns) '
            'VALUES (?, ?, ?, ?)',
            (
                table_name,
                sanitized_table,
                json.dumps(columns),
                json.dumps(sanitized_columns),
            ),
        )

    def _fetch_table_metadata(self, cursor: sqlite3.Cursor, table_name: str) -> dict[str, Any] | None:
        cursor.execute(
            f'SELECT table_name, sanitized_name, columns, sanitized_columns FROM {_METADATA_TABLE} WHERE table_name = ?',
            (table_name,),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        keys = [column[0] for column in cursor.description]
        return dict(zip(keys, row, strict=True))

    def _ensure_metadata_table(self, cursor: sqlite3.Cursor) -> None:
        cursor.execute(
            f"CREATE TABLE IF NOT EXISTS {_METADATA_TABLE} ("
            "table_name TEXT PRIMARY KEY,"
            "sanitized_name TEXT NOT NULL,"
            "columns TEXT NOT NULL,"
            "sanitized_columns TEXT NOT NULL"
            ")"
        )

    def _coerce_value(self, value: Any) -> str:
        if value is None:
            return ""
        return str(value)

    def _open_mutable_database(self):
        return _EncryptedDatabaseContext(self._db_path, self._fernet)

    def _load_key(self) -> bytes:
        if self._key_path.exists():
            key = self._key_path.read_bytes()
            if key:
                return key

        key = Fernet.generate_key()
        self._key_path.write_bytes(key)
        try:
            if os.name != "nt":
                os.chmod(self._key_path, 0o600)
        except OSError:
            pass
        return key

    @staticmethod
    def _sanitize_identifier(name: str) -> str:
        import re

        cleaned = re.sub(r"[^0-9a-zA-Z_]", "_", name.strip())
        if not cleaned:
            cleaned = "table"
        if cleaned[0].isdigit():
            cleaned = f"t_{cleaned}"
        return cleaned.lower()


class _EncryptedDatabaseContext:
    def __init__(self, db_path: Path, fernet: Fernet) -> None:
        self._db_path = db_path
        self._fernet = fernet
        self._temp_file: tempfile.NamedTemporaryFile | None = None
        self.connection: sqlite3.Connection | None = None

    def __enter__(self) -> sqlite3.Connection:
        self._temp_file = tempfile.NamedTemporaryFile(delete=False)
        if self._db_path.exists():
            encrypted = self._db_path.read_bytes()
            if encrypted:
                decrypted = self._fernet.decrypt(encrypted)
                self._temp_file.write(decrypted)
                self._temp_file.flush()
        self.connection = sqlite3.connect(self._temp_file.name)
        return self.connection

    def __exit__(self, exc_type, exc, tb) -> None:
        if self.connection is not None:
            self.connection.close()
        if self._temp_file is not None:
            self._temp_file.close()
            if exc_type is None:
                with open(self._temp_file.name, "rb") as tmp:
                    data = tmp.read()
                encrypted = self._fernet.encrypt(data)
                self._db_path.write_bytes(encrypted)
            os.unlink(self._temp_file.name)


