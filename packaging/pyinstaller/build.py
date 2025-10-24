#!/usr/bin/env python
"""
Build a standalone opendental-query executable using PyInstaller.

Usage:
    python packaging/pyinstaller/build.py

This script expects PyInstaller to be installed (e.g. `pip install .[packaging]`)
and produces a single-file executable under `dist/standalone/`.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


def main() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    src_entry = repo_root / "src" / "opendental_query" / "cli" / "main.py"
    if not src_entry.exists():
        raise SystemExit(f"Unable to locate CLI entry point: {src_entry}")

    dist_dir = repo_root / "dist" / "standalone"
    build_dir = repo_root / "build" / "pyinstaller"
    spec_dir = repo_root / "packaging" / "pyinstaller"

    dist_dir.mkdir(parents=True, exist_ok=True)
    build_dir.mkdir(parents=True, exist_ok=True)
    spec_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--name",
        "opendental-query",
        "--onefile",
        "--console",
        "--clean",
        "--distpath",
        str(dist_dir),
        "--workpath",
        str(build_dir),
        "--specpath",
        str(spec_dir),
        "--hidden-import",
        "pydantic.validators",
        str(src_entry),
    ]

    print("Running:", " ".join(cmd))
    try:
        subprocess.run(cmd, check=True)
    except FileNotFoundError as exc:
        raise SystemExit(
            "PyInstaller is not installed. Install packaging extras with "
            "`pip install .[packaging]` and retry."
        ) from exc
    except subprocess.CalledProcessError as exc:
        raise SystemExit(f"PyInstaller failed with exit code {exc.returncode}") from exc

    executable = dist_dir / ("opendental-query.exe" if sys.platform.startswith("win") else "opendental-query")
    if executable.exists():
        print(f"\n✅ Standalone executable created: {executable}")
    else:
        print(
            "\nPyInstaller completed, but the expected executable was not found.\n"
            f"Check the contents of {dist_dir} for build artifacts."
        )


if __name__ == "__main__":
    main()
