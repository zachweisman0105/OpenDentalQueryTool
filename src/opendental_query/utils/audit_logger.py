"""Audit logging for security-relevant events in JSONL format."""

import hashlib
import hmac
import json
import os
import secrets
import socket
import uuid
from datetime import UTC
from pathlib import Path
from threading import Lock
from typing import Any

from opendental_query.models.audit import AuditEntry
from opendental_query.utils.app_logger import get_logger

logger = get_logger(__name__)


class AuditLogger:
    """Thread-safe audit logger for writing security events to JSONL file.

    Writes audit entries as single-line JSON records to a JSONL (JSON Lines)
    file for easy parsing and analysis. Each line is a complete JSON object.

    Attributes:
        audit_file: Path to the JSONL audit log file
        _lock: Thread lock for synchronized file writes
        RETENTION_DAYS: Number of days to retain audit logs (90 days for HIPAA compliance)
    """

    RETENTION_DAYS = 90  # HIPAA requirement: retain audit logs for 90 days minimum

    def __init__(self, audit_file: Path | None = None) -> None:
        """Initialize audit logger.

        Args:
            audit_file: Path to audit log file (defaults to ~/.opendental-query/audit.jsonl)
        """
        if audit_file is None:
            from opendental_query.constants import DEFAULT_AUDIT_FILE, DEFAULT_CONFIG_DIR

            audit_file = DEFAULT_CONFIG_DIR / DEFAULT_AUDIT_FILE

        self.audit_file = audit_file
        self._lock = Lock()
        self._hash_secret: bytes = b""
        self._session_id = uuid.uuid4().hex
        self._hostname = socket.gethostname()
        self._ip_address = self._resolve_ip_address(self._hostname)

        # Ensure audit file directory exists
        from opendental_query.utils.file_utils import ensure_directory

        ensure_directory(audit_file.parent)

        # Create audit file if it doesn't exist
        if not audit_file.exists():
            audit_file.touch(mode=0o600)  # Owner read/write only

        self._hash_secret = self._load_hash_secret(audit_file.parent)

        # Clean up old audit entries on initialization
        self.cleanup_old_entries()

    def log(
        self,
        event_type: str,
        *,
        success: bool,
        office_id: str | None = None,
        details: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> None:
        """Log a security-relevant event to the audit file.

        Args:
            event_type: Type of event (e.g., "vault_unlock", "query_execute")
            success: Whether the action succeeded
            office_id: Office identifier if applicable
            details: Additional event-specific details
            error: Error message if action failed
        """
        # Get current system username
        user = os.getenv("USER") or os.getenv("USERNAME") or "unknown"

        office_token = self._tokenize_office(office_id) if office_id else None
        sanitized_details = self._sanitize_details(details or {})

        # Create audit entry
        entry = AuditEntry(
            event_type=event_type,
            user=user,
            office_id=office_token,
            success=success,
            details=sanitized_details,
            error=error,
            ip_address=self._ip_address,
            hostname=self._hostname,
            session_id=self._session_id,
        )

        # Write to file with thread safety
        try:
            with self._lock:
                with self.audit_file.open("a", encoding="utf-8") as f:
                    f.write(entry.to_jsonl())
        except OSError as e:
            logger.error(f"Failed to write audit log: {e}")

    def log_vault_unlock(self, *, success: bool, error: str | None = None) -> None:
        """Log a vault unlock attempt.

        Args:
            success: Whether unlock succeeded
            error: Error message if unlock failed
        """
        self.log("vault_unlock", success=success, error=error)

    def log_vault_lock(self) -> None:
        """Log a vault lock event."""
        self.log("vault_lock", success=True)

    def log_query_execute(
        self,
        *,
        office_id: str,
        query: str,
        success: bool,
        row_count: int | None = None,
        execution_time_ms: float | None = None,
        error: str | None = None,
    ) -> None:
        """Log query execution event without storing PHI."""
        query_hash = hashlib.sha256(query.encode("utf-8")).hexdigest()
        details = {"query_hash": query_hash}
        if row_count is not None:
            details["row_count"] = row_count
        if execution_time_ms is not None:
            details["execution_time_ms"] = execution_time_ms

        self.log(
            "query_execute",
            success=success,
            office_id=office_id,
            details=details,
            error=error,
        )

    def log_config_change(self, *, action: str, details: dict[str, Any]) -> None:
        """Log a configuration change event.

        Args:
            action: Configuration action performed
            details: Details about the change
        """
        details_with_action = {"action": action, **details}
        self.log("config_change", success=True, details=details_with_action)

    def log_query_execution(
        self,
        *,
        query: str,
        office_ids: list[str],
        success_count: int,
        failed_count: int,
        row_count: int,
    ) -> None:
        """Log a multi-office query execution event.

        Args:
            query: SQL query executed
            office_ids: List of office IDs queried
            success_count: Number of successful queries
            failed_count: Number of failed queries
            row_count: Total rows returned
        """
        query_hash = hashlib.sha256(query.encode("utf-8")).hexdigest()
        details = {
            "query_hash": query_hash,
            "office_tokens": [self._tokenize_office(o) for o in office_ids],
            "office_count": len(office_ids),
            "success_count": success_count,
            "failed_count": failed_count,
            "row_count": row_count,
        }
        self.log("query_execution", success=True, details=details)

    def log_excel_export(
        self,
        *,
        filepath: str,
        row_count: int,
        office_count: int,
    ) -> None:
        """Log an Excel export event.

        Args:
            filepath: Path to exported Excel file
            row_count: Number of rows exported
            office_count: Number of offices in export
        """
        # Calculate SHA256 hash of file for integrity verification
        file_hash = "unknown"
        try:
            with open(filepath, "rb") as f:
                file_hash = hashlib.sha256(f.read()).hexdigest()
        except Exception:
            pass

        details = {
            "filepath": filepath,
            "row_count": row_count,
            "office_count": office_count,
            "sha256": file_hash,
        }
        self.log("excel_export", success=True, details=details)

    @property
    def current_user(self) -> str:
        """Get current system username."""
        return os.getenv("USER") or os.getenv("USERNAME") or "unknown"

    def log_vault_created(self) -> None:
        """Log vault creation event."""
        self.log("VAULT_CREATED", success=True)

    def log_vault_unlocked(self) -> None:
        """Log successful vault unlock."""
        self.log("VAULT_UNLOCKED", success=True)

    def log_vault_locked(self) -> None:
        """Log vault lock event."""
        self.log("VAULT_LOCKED", success=True)

    def log_office_added(self, office_name: str) -> None:
        """Log office addition event.

        Args:
            office_name: Name of the office added
        """
        self.log("OFFICE_ADDED", success=True, details={"office_name": office_name})

    def log_office_removed(self, office_name: str) -> None:
        """Log office removal event.

        Args:
            office_name: Name of the office removed
        """
        self.log("OFFICE_REMOVED", success=True, details={"office_name": office_name})

    def log_query_executed(self, sql: str, offices: list[str]) -> None:
        """Log query execution with SHA256 hash (not plaintext SQL).

        Args:
            sql: SQL query executed (will be hashed, not stored plaintext)
            offices: List of office names queried
        """
        query_hash = hashlib.sha256(sql.encode()).hexdigest()
        self.log(
            "QUERY_EXECUTED",
            success=True,
            details={
                "query_hash": query_hash,
                "office_tokens": [self._tokenize_office(o) for o in offices],
                "office_count": len(offices),
            },
        )

    def log_export_created(self, export_path: Path, row_count: int) -> None:
        """Log export creation event.

        Args:
            export_path: Path to the exported file
            row_count: Number of rows exported
        """
        self.log(
            "EXPORT_CREATED",
            success=True,
            details={
                "file_path": str(export_path),
                "row_count": row_count,
            },
        )

    def log_authentication_failed(self, reason: str) -> None:
        """Log failed authentication attempt.

        Args:
            reason: Reason for authentication failure
        """
        self.log("AUTHENTICATION_FAILED", success=False, details={"reason": reason})

    def log_vault_lockout(self) -> None:
        """Log vault lockout due to too many failed attempts."""
        self.log("VAULT_LOCKOUT", success=True)

    def log_network_error(
        self, *, operation: str, error: str, office_id: str | None = None
    ) -> None:
        """Log a network error event.

        Args:
            operation: The operation that failed (e.g., "query_execute", "update_check")
            error: Error message describing the network failure
            office_id: Office identifier if applicable
        """
        self.log(
            "NETWORK_ERROR",
            success=False,
            office_id=office_id,
            details={"operation": operation},
            error=error,
        )

    def log_update_checked(
        self,
        *,
        current_version: str,
        latest_version: str | None,
        update_available: bool,
        error: str | None = None,
    ) -> None:
        """Log a software update check event.

        Args:
            current_version: Currently running version
            latest_version: Latest version found (None if error)
            update_available: Whether an update is available
            error: Error message if the check failed
        """
        details: dict[str, Any] = {
            "current_version": current_version,
            "latest_version": latest_version,
            "update_available": update_available,
        }
        self.log("UPDATE_CHECKED", success=error is None, details=details, error=error)

    def _load_hash_secret(self, directory: Path) -> bytes:
        """Load or generate the secret used to hash sensitive fields."""
        env_value = os.getenv("SPEC_KIT_AUDIT_SALT")
        if env_value:
            return hashlib.sha256(env_value.encode("utf-8")).digest()

        salt_file = directory / ".audit_salt"
        if salt_file.exists():
            try:
                secret = salt_file.read_bytes()
                if secret:
                    return secret
            except OSError:
                pass

        secret = secrets.token_bytes(32)
        try:
            temp_file = salt_file.with_suffix(".tmp")
            temp_file.write_bytes(secret)
            try:
                os.chmod(temp_file, 0o600)
            except PermissionError:
                pass
            temp_file.replace(salt_file)
        except OSError:
            return secret

        return secret

    def _hash_value(self, value: str) -> str:
        """Hash a string with the audit secret."""
        if not value:
            return "unknown"
        secret = self._hash_secret
        if not secret:
            return hashlib.sha256(value.encode("utf-8")).hexdigest()
        return hmac.new(secret, value.encode("utf-8"), hashlib.sha256).hexdigest()

    def _tokenize_office(self, office_id: str | None) -> str | None:
        """Convert an office identifier into a deterministic, non-reversible token."""
        if office_id is None:
            return None
        return self._hash_value(office_id)

    def _sanitize_details(self, details: dict[str, Any]) -> dict[str, Any]:
        """Redact sensitive values from log detail payloads."""
        sanitized: dict[str, Any] = {}
        for key, value in details.items():
            if key in {"filepath", "file_path"} and isinstance(value, str):
                sanitized.setdefault("filename", Path(value).name)
                sanitized["path_hash"] = self._hash_value(value)
            elif key in {"office_id", "office", "office_name"} and isinstance(value, str):
                sanitized["office_token"] = self._hash_value(value)
            elif key in {"office_ids", "offices"} and isinstance(value, list):
                sanitized["office_tokens"] = [self._hash_value(str(item)) for item in value]
                sanitized["office_token_count"] = len(value)
            else:
                sanitized[key] = value
        return sanitized

    def cleanup_old_entries(self) -> None:
        """Remove audit log entries older than RETENTION_DAYS.

        Reads the audit log, filters out entries older than the retention period,
        and rewrites the log with only valid entries.
        """
        from datetime import datetime, timedelta

        if not self.audit_file.exists():
            return

        cutoff_date = datetime.now(UTC) - timedelta(days=self.RETENTION_DAYS)

        # Read all entries
        try:
            with self._lock:
                with self.audit_file.open("r", encoding="utf-8") as f:
                    lines = f.readlines()

                # Filter entries newer than cutoff
                valid_entries = []
                for line in lines:
                    try:
                        entry = json.loads(line)
                        entry_time = datetime.fromisoformat(entry["timestamp"])
                        # Make timezone-aware if needed (for old entries)
                        if entry_time.tzinfo is None:
                            entry_time = entry_time.replace(tzinfo=UTC)
                        if entry_time >= cutoff_date:
                            valid_entries.append(line)
                    except (json.JSONDecodeError, KeyError, ValueError):
                        # Keep malformed entries (don't delete data we can't parse)
                        valid_entries.append(line)

                # Rewrite file with valid entries only
                with self.audit_file.open("w", encoding="utf-8") as f:
                    f.writelines(valid_entries)

                logger.debug(
                    "Cleaned up %s old audit entries",
                    len(lines) - len(valid_entries),
                )

        except OSError as e:
            logger.error(f"Failed to cleanup old audit entries: {e}")

    @staticmethod
    def _resolve_ip_address(hostname: str) -> str | None:
        """Best-effort resolution of host IP address."""
        try:
            return socket.gethostbyname(hostname)
        except Exception:
            return None
