"""Startup checks for application prerequisites and configuration."""

import os
import sys
from pathlib import Path

import httpx

from opendental_query.constants import (
    DEFAULT_AUDIT_FILE,
    DEFAULT_CONFIG_DIR,
    DEFAULT_LOG_FILE,
    DEFAULT_VAULT_FILE,
)
from opendental_query.renderers.excel_exporter import ExcelExporter
from opendental_query.utils.app_logger import cleanup_old_logs, get_logger
from opendental_query.utils.audit_logger import AuditLogger

logger = get_logger(__name__)


class StartupCheckError(Exception):
    """Exception raised when startup checks fail."""


def _cleanup_old_logs() -> None:
    """Clean up existing log files using configured retention policies."""
    log_file = DEFAULT_CONFIG_DIR / DEFAULT_LOG_FILE
    if log_file.exists():
        cleanup_old_logs(log_file, retention_days=30)

    audit_file = DEFAULT_CONFIG_DIR / DEFAULT_AUDIT_FILE
    if audit_file.exists():
        AuditLogger(audit_file)


def check_python_version() -> tuple[bool, str]:
    version = sys.version_info
    major = getattr(version, "major", version[0])
    minor = getattr(version, "minor", version[1])
    if (major, minor) >= (3, 11):
        return True, f"Python {major}.{minor} detected"
    return False, f"Python 3.11+ required (found {major}.{minor})"


def check_vault_exists() -> tuple[bool, str]:
    vault_path = DEFAULT_CONFIG_DIR / DEFAULT_VAULT_FILE
    if vault_path.exists():
        return True, f"Vault present at {vault_path}"
    return False, f"Vault not found at {vault_path}. Run 'opendental-query vault-init'."


def check_vault_permissions() -> tuple[bool, str]:
    vault_path = DEFAULT_CONFIG_DIR / DEFAULT_VAULT_FILE
    if not vault_path.exists():
        return True, "Vault file not created yet (skipping permission check)"
    if os.name == "nt":
        return True, "Vault permission check skipped on Windows"

    try:
        mode = os.stat(vault_path).st_mode & 0o777
        if mode == 0o600:
            return True, "Vault permissions set to 0600"
        return False, f"Vault permissions are {oct(mode)} (expected 0600)"
    except OSError as exc:
        return False, f"Unable to read vault permissions: {exc}"


def check_vault_directory_permissions() -> tuple[bool, str]:
    vault_dir = DEFAULT_CONFIG_DIR
    if os.name == "nt":
        return True, "Vault directory permission check skipped on Windows"
    if not vault_dir.exists():
        return True, "Vault directory not created yet (skipping permission check)"
    try:
        mode = os.stat(vault_dir).st_mode & 0o777
        if mode == 0o700:
            return True, "Vault directory permissions set to 0700"
        return False, f"Vault directory permissions are {oct(mode)} (expected 0700)"
    except OSError as exc:
        return False, f"Unable to read vault directory permissions: {exc}"


def check_audit_log_writable() -> tuple[bool, str]:
    audit_file = DEFAULT_CONFIG_DIR / DEFAULT_AUDIT_FILE
    audit_file.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    try:
        with open(audit_file, "a", encoding="utf-8"):
            pass
        return True, f"Audit log writable at {audit_file}"
    except OSError as exc:
        return False, f"Audit log not writable: {exc}"


def check_downloads_accessible() -> tuple[bool, str]:
    downloads = Path.home() / "Downloads"
    if downloads.exists() and downloads.is_dir():
        if os.access(downloads, os.W_OK):
            return True, f"Downloads folder accessible at {downloads}"
        return False, f"Downloads folder not writable: {downloads}"
    return True, "Downloads folder not found; exporter will use current working directory"


def check_export_directory_policy() -> tuple[bool, str]:
    exporter = ExcelExporter()
    try:
        default_dir = exporter._resolve_output_dir(None)
        exporter._ensure_secure_directory(default_dir)
        return True, f"Export directory policy OK (default {default_dir})"
    except ValueError as exc:
        return False, (
            "Excel export directory policy misconfigured: " + str(exc)
            + "\nSet SPEC_KIT_EXPORT_ROOT to an approved directory or create ~/Downloads with secure permissions."
        )
    except Exception as exc:
        return False, f"Failed to validate Excel export directory policy: {exc}"


def check_https_connectivity(test_url: str = "https://www.google.com") -> tuple[bool, str]:
    try:
        with httpx.Client(timeout=5.0, verify=True) as client:
            response = client.get(test_url)
            if response.status_code == 200:
                return True, "HTTPS connectivity verified"
            return False, f"HTTPS test returned status code {response.status_code}"
    except httpx.TimeoutException:
        return False, "HTTPS connectivity test timed out"
    except httpx.HTTPError as exc:
        return False, f"HTTPS connectivity failed: {exc}"


def run_startup_checks(skip_vault: bool = False, skip_network: bool = False) -> None:
    _cleanup_old_logs()

    checks: list[tuple[str, tuple[bool, str]]] = [
        ("Python Version", check_python_version()),
        ("Audit Log", check_audit_log_writable()),
        ("Download Folder", check_downloads_accessible()),
        ("Export Directory Policy", check_export_directory_policy()),
    ]

    if not skip_vault:
        checks.extend([
            ("Vault Exists", check_vault_exists()),
            ("Vault Directory Permissions", check_vault_directory_permissions()),
            ("Vault Permissions", check_vault_permissions()),
        ])

    if not skip_network:
        checks.append(("HTTPS Connectivity", check_https_connectivity()))

    failures: list[tuple[str, str]] = []
    logger.info("Running startup checks...")
    for name, (success, message) in checks:
        if success:
            logger.info("%s: %s", name, message)
        else:
            logger.error("%s: %s", name, message)
            failures.append((name, message))

    if failures:
        formatted = "\n".join(f"- {name}: {message}" for name, message in failures)
        raise StartupCheckError("Startup checks failed:\n" + formatted)


    logger.info("All startup checks passed")


def get_remediation_steps(check_name: str) -> str | None:
    remediation_map = {
        "Python Version": "Install Python 3.11 or higher from https://www.python.org/",
        "Vault Exists": "Run 'opendental-query vault-init' to create the encrypted vault file.",
        "Vault Directory Permissions": "Run 'chmod 700 ~/.opendental-query' on Unix-like systems.",
        "Vault Permissions": "Run 'chmod 600 ~/.opendental-query/credentials.vault' on Unix-like systems.",
        "Audit Log": "Ensure ~/.opendental-query/ is writable by the current user.",
        "Download Folder": "Create or fix permissions on your Downloads directory.",
        "Export Directory Policy": "Set SPEC_KIT_EXPORT_ROOT to a secure directory or create ~/Downloads.",
        "HTTPS Connectivity": "Verify network connectivity and proxy/firewall settings.",
    }
    return remediation_map.get(check_name)
