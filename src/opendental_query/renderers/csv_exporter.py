"""
CSV Exporter for query results.

Exports query results to CSV files with:
- Random filename generation (opendental_query_{token}_{timestamp}.csv)
- UTF-8 BOM encoding for Excel compatibility
- CRLF line endings (\r\n)
- QUOTE_MINIMAL quoting strategy
- Downloads folder detection with fallback to cwd
"""

import csv
import os
import secrets
import shlex
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

from opendental_query.constants import DEFAULT_CONFIG_DIR


class CSVExporter:
    """
    Exports query results to CSV files with secure storage defaults.
    """

    def export(
        self,
        rows: list[dict[str, Any]],
        output_dir: Path | None = None,
    ) -> Path:
        if not rows:
            raise ValueError("Cannot export empty rows list - no data to write")

        target_dir = self._resolve_output_dir(output_dir)
        self._ensure_secure_directory(target_dir)
        target_dir.mkdir(parents=True, exist_ok=True)
        self._set_permissions(target_dir, dir_mode=0o700)

        filename = self._generate_filename()
        filepath = (target_dir / filename).resolve()

        fieldnames = list(rows[0].keys())

        with open(filepath, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=fieldnames,
                quoting=csv.QUOTE_MINIMAL,
                lineterminator="\r\n",
            )
            writer.writeheader()
            for row in rows:
                cleaned_row = {key: "" if value is None else value for key, value in row.items()}
                writer.writerow(cleaned_row)

        self._set_permissions(filepath, file_mode=0o600)
        return self._maybe_encrypt_file(filepath)

    def _resolve_output_dir(self, output_dir: Path | None) -> Path:
        return Path(output_dir) if output_dir is not None else self._get_downloads_folder()

    def _ensure_secure_directory(self, output_dir: Path) -> None:
        if os.getenv("SPEC_KIT_ALLOW_UNSAFE_EXPORTS") == "1":
            return

        allowed_roots = [self._get_downloads_folder().resolve(), DEFAULT_CONFIG_DIR.resolve()]
        env_root = os.getenv("SPEC_KIT_EXPORT_ROOT")
        if env_root:
            allowed_roots.append(Path(env_root).expanduser().resolve())

        resolved_dir = output_dir.resolve()
        for root in allowed_roots:
            try:
                if resolved_dir == root or resolved_dir.is_relative_to(root):
                    return
            except AttributeError:
                try:
                    resolved_dir.relative_to(root)
                    return
                except ValueError:
                    continue

        raise ValueError(
            f"Export directory {resolved_dir} is outside allowed roots. "
            "Set SPEC_KIT_EXPORT_ROOT to an approved location or set "
            "SPEC_KIT_ALLOW_UNSAFE_EXPORTS=1 to override (not recommended)."
        )

    def _set_permissions(self, path: Path, *, dir_mode: int | None = None, file_mode: int | None = None) -> None:
        if os.name == "nt":
            return
        mode = dir_mode if path.is_dir() else file_mode
        if mode is None:
            return
        try:
            os.chmod(path, mode)
        except PermissionError:
            pass

    def _generate_filename(self) -> str:
        token = secrets.token_hex(4)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"opendental_query_{token}_{timestamp}.csv"

    def _get_downloads_folder(self) -> Path:
        downloads = Path.home() / "Downloads"
        return downloads if downloads.exists() and downloads.is_dir() else Path.cwd()

    def _maybe_encrypt_file(self, filepath: Path) -> Path:
        command_template = os.getenv("SPEC_KIT_EXPORT_ENCRYPTION_COMMAND")
        if not command_template:
            return filepath

        command = command_template.format(input=str(filepath))
        try:
            args = shlex.split(command, posix=(os.name != "nt"))
            subprocess.run(args, check=True)
        except Exception as exc:
            raise RuntimeError(f"Export encryption command failed: {exc}") from exc
        return filepath
