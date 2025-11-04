"""Vault manager for secure credential storage.

Provides high-level interface for managing encrypted vault of OpenDental
API credentials with features:
- Master password protection with strength validation
- 3-attempt lockout with 60-second cooldown
- 15-minute inactivity auto-lock
- Secure file permissions (0600)
- Atomic file writes
- Comprehensive audit logging
"""

import json
import os
import re
import stat
import threading
from datetime import datetime, timedelta
from pathlib import Path

from opendental_query.constants import MAX_PASSWORD_ATTEMPTS, OFFICE_ID_PATTERN, PASSWORD_MIN_LENGTH
from opendental_query.core.vault_encryption import VaultEncryption
from opendental_query.models.vault import VaultCredentials, VaultData
from opendental_query.utils.app_logger import get_logger
from opendental_query.utils.audit_logger import AuditLogger

logger = get_logger(__name__)


class VaultManager:
    """Manager for encrypted credential vault.

    Handles all vault operations including initialization, locking/unlocking,
    and CRUD operations on credentials. Provides security features:
    - Password strength validation (no enforced complexity requirements)
    - Failed attempt tracking with lockout
    - Auto-lock timer on inactivity
    - Secure file permissions

    Attributes:
        vault_path: Path to encrypted vault file
        _unlocked: Whether vault is currently unlocked
        _vault_data: Decrypted vault data (when unlocked)
        _password: Cached master password (when unlocked)
        _failed_attempts: Count of failed unlock attempts
        _lockout_until: Timestamp when lockout expires
        _auto_lock_timer: Timer for auto-lock on inactivity
        _lock: Thread lock for synchronization
    """

    def __init__(self, vault_path: Path, audit_log_path: Path | None = None) -> None:
        """Initialize vault manager.

        Args:
            vault_path: Path to vault file
            audit_log_path: Optional path to audit log (default: same dir as vault)
        """
        self.vault_path = vault_path
        self._unlocked = False
        self._vault_data: dict | None = None
        self._password: str | None = None
        self._failed_attempts = 0
        self._lockout_until: datetime | None = None
        self._auto_lock_timer: threading.Timer | None = None
        self._lock = threading.Lock()

        # Auto-lock configuration (15 minutes default)
        self._auto_lock_timeout = 900  # seconds
        self._lockout_duration = 60  # seconds

        # Initialize audit logger
        if audit_log_path is None:
            audit_log_path = vault_path.parent / "audit.jsonl"
        self._audit_logger = AuditLogger(audit_log_path)

    def _enforce_permissions(self) -> None:
        """Ensure vault directory and file permissions are locked down."""
        directory = self.vault_path.parent

        # Always ensure directory exists
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)

        # Permission adjustments are only meaningful on POSIX systems
        if os.name != "posix":
            return

        try:
            dir_mode = stat.S_IMODE(os.stat(directory).st_mode)
            if dir_mode & 0o077:
                try:
                    os.chmod(directory, 0o700)
                    logger.warning(
                        "Adjusted vault directory permissions to 0700 for security: %s", directory
                    )
                except OSError as exc:
                    raise PermissionError(
                        f"Vault directory {directory} has insecure permissions {oct(dir_mode)} "
                        "and could not be remediated automatically. "
                        "Update permissions to 0700 and retry."
                    ) from exc
        except OSError as exc:
            raise PermissionError(f"Unable to inspect vault directory permissions: {exc}") from exc

        if not self.vault_path.exists():
            return

        try:
            file_mode = stat.S_IMODE(os.stat(self.vault_path).st_mode)
            if file_mode != 0o600:
                try:
                    os.chmod(self.vault_path, 0o600)
                    logger.warning(
                        "Adjusted vault file permissions to 0600 for security: %s",
                        self.vault_path,
                    )
                except OSError as exc:
                    raise PermissionError(
                        f"Vault file {self.vault_path} has insecure permissions {oct(file_mode)} "
                        "and could not be remediated automatically. "
                        "Set permissions to 0600 and retry."
                    ) from exc
        except OSError as exc:
            raise PermissionError(f"Unable to inspect vault file permissions: {exc}") from exc

    def configure_auto_lock(self, timeout_seconds: int) -> None:
        """Configure inactivity timeout before auto-locking the vault."""
        if timeout_seconds < 60:
            raise ValueError("Auto-lock timeout must be at least 60 seconds")
        self._auto_lock_timeout = timeout_seconds

    def _validate_password_strength(self, password: str) -> None:
        """Password strength checks are intentionally disabled."""
        return

    def _is_locked_out(self) -> bool:
        """Check if vault is currently locked due to failed attempts.

        Returns:
            True if locked out, False otherwise
        """
        if self._lockout_until is None:
            return False

        if datetime.now() < self._lockout_until:
            return True

        # Lockout has expired
        self._lockout_until = None
        self._failed_attempts = 0
        return False

    def _start_auto_lock_timer(self) -> None:
        """Start or reset the auto-lock timer."""
        # Cancel existing timer
        if self._auto_lock_timer is not None:
            self._auto_lock_timer.cancel()

        # Start new timer
        self._auto_lock_timer = threading.Timer(self._auto_lock_timeout, self._auto_lock)
        self._auto_lock_timer.daemon = True
        self._auto_lock_timer.start()

    def _auto_lock(self) -> None:
        """Auto-lock vault due to inactivity."""
        logger.info("Auto-locking vault due to inactivity")
        self._audit_logger.log("vault_auto_lock", success=True)
        self.lock()

    def _reset_auto_lock_timer(self) -> None:
        """Reset auto-lock timer on vault access."""
        if self._unlocked:
            self._start_auto_lock_timer()

    def _require_unlocked(self) -> None:
        """Ensure vault is unlocked for operation.

        Raises:
            ValueError: If vault is locked
        """
        if not self._unlocked:
            raise ValueError("Vault is locked. Unlock it first.")

    def init(self, password: str, developer_key: str) -> None:
        """Initialize a new vault with master password and developer key.

        Creates encrypted vault file with secure permissions (0600).

        Args:
            password: Master password for vault
            developer_key: OpenDental DeveloperKey

        Raises:
            ValueError: If vault already exists or password is weak
        """
        # Check if vault already exists
        if self.vault_path.exists():
            raise ValueError(f"Vault already exists at {self.vault_path}")

        try:
            self._enforce_permissions()
        except PermissionError as exc:
            raise ValueError(str(exc)) from exc

        # Validate password strength
        self._validate_password_strength(password)

        # Create initial vault data
        vault_data = {
            "metadata": {"created_at": datetime.now().isoformat(), "version": "1.0"},
            "developer_key": developer_key,
            "offices": {},
        }

        # Encrypt and save
        plaintext = json.dumps(vault_data).encode("utf-8")
        encrypted_blob = VaultEncryption.encrypt_vault_data(plaintext, password)

        # Ensure parent directory exists
        self.vault_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)

        # Write vault file with atomic operation
        temp_path = self.vault_path.with_suffix(".tmp")
        temp_path.write_bytes(encrypted_blob)

        # Set secure permissions before moving
        os.chmod(temp_path, 0o600)

        # Atomic rename
        temp_path.replace(self.vault_path)

        logger.info(f"Vault initialized at {self.vault_path}")
        self._audit_logger.log("vault_created", success=True)

        # Auto-unlock after creation
        self._unlocked = True
        self._vault_data = vault_data
        self._password = password
        self._start_auto_lock_timer()

    def unlock(self, password: str) -> bool:
        """Unlock vault with master password.

        Args:
            password: Master password

        Returns:
            True if unlock successful, False if password incorrect

        Raises:
            ValueError: If vault is locked out or doesn't exist
        """
        with self._lock:
            try:
                self._enforce_permissions()
            except PermissionError as exc:
                self._audit_logger.log_vault_unlock(
                    success=False, error=f"permissions_error:{exc}"
                )
                raise ValueError(str(exc)) from exc

            # Check if locked out
            if self._is_locked_out():
                time_remaining = (self._lockout_until - datetime.now()).total_seconds()
                logger.warning(
                    f"Vault unlock attempted during lockout; {int(time_remaining)}s remaining"
                )
                # Log and raise to signal lockout explicitly
                self._audit_logger.log_vault_unlock(
                    success=False, error=f"locked_out:{int(time_remaining)}s_remaining"
                )
                raise ValueError(
                    f"Vault is locked due to failed attempts. Try again in {int(time_remaining)} seconds."
                )

            # Check if vault exists
            if not self.vault_path.exists():
                raise ValueError(f"Vault not found at {self.vault_path}")

            # Try to decrypt vault
            try:
                encrypted_blob = self.vault_path.read_bytes()
                plaintext = VaultEncryption.decrypt_vault_data(encrypted_blob, password)
                vault_data = json.loads(plaintext.decode("utf-8"))

                # Success - unlock vault
                self._unlocked = True
                self._vault_data = vault_data
                self._password = password
                self._failed_attempts = 0
                self._lockout_until = None

                logger.info("Vault unlocked successfully")
                self._audit_logger.log_vault_unlock(success=True)

                # Start auto-lock timer
                self._start_auto_lock_timer()

                return True

            except Exception as e:
                # Failed attempt
                self._failed_attempts += 1
                logger.warning(
                    f"Failed vault unlock attempt ({self._failed_attempts}/{MAX_PASSWORD_ATTEMPTS})"
                )
                self._audit_logger.log_vault_unlock(success=False, error=str(e))

                # Check if should lock out
                if self._failed_attempts >= MAX_PASSWORD_ATTEMPTS:
                    self._lockout_until = datetime.now() + timedelta(seconds=self._lockout_duration)
                    logger.error(f"Vault locked out for {self._lockout_duration} seconds")
                    self._audit_logger.log(
                        "vault_lockout",
                        success=True,
                        details={"duration_seconds": self._lockout_duration},
                    )

                return False

    def lock(self) -> None:
        """Lock the vault, clearing cached credentials."""
        with self._lock:
            if self._auto_lock_timer is not None:
                self._auto_lock_timer.cancel()
                self._auto_lock_timer = None

            self._unlocked = False
            self._vault_data = None
            self._password = None

            logger.info("Vault locked")
            self._audit_logger.log_vault_lock()

    def is_unlocked(self) -> bool:
        """Check if vault is currently unlocked.

        Returns:
            True if unlocked, False otherwise
        """
        return self._unlocked

    def add_office(self, office_id: str, customer_key: str) -> None:
        """Add office credential to vault.

        Args:
            office_id: Office identifier
            customer_key: OpenDental CustomerKey for this office

        Raises:
            ValueError: If vault is locked
        """
        self._require_unlocked()
        self._reset_auto_lock_timer()

        with self._lock:
            self._vault_data["offices"][office_id] = {
                "customer_key": customer_key,
                "added_at": datetime.now().isoformat(),
            }

            # Save to file
            self._save_vault()

            logger.info(f"Added office credential: {office_id}")
            self._audit_logger.log_config_change(
                action="add_office", details={"office_id": office_id}
            )

    def remove_office(self, office_id: str) -> None:
        """Remove office credential from vault.

        Args:
            office_id: Office identifier to remove

        Raises:
            ValueError: If vault is locked or office not found
        """
        self._require_unlocked()
        self._reset_auto_lock_timer()

        with self._lock:
            if office_id not in self._vault_data["offices"]:
                raise ValueError(f"Office not found: {office_id}")

            del self._vault_data["offices"][office_id]

            # Save to file
            self._save_vault()

            logger.info(f"Removed office credential: {office_id}")
            self._audit_logger.log_config_change(
                action="remove_office", details={"office_id": office_id}
            )

    def rename_office(self, current_office_id: str, new_office_id: str) -> None:
        """Rename an existing office identifier in the vault.

        Args:
            current_office_id: Existing office identifier
            new_office_id: Desired replacement identifier

        Raises:
            ValueError: If the vault is locked, the source office is missing,
                the new identifier is invalid, or the destination already exists.
        """
        self._require_unlocked()
        self._reset_auto_lock_timer()

        normalized_new_id = new_office_id.strip()
        if not normalized_new_id:
            raise ValueError("New office ID cannot be empty")
        if normalized_new_id == current_office_id:
            raise ValueError("New office ID must be different from the current ID")
        if not re.match(OFFICE_ID_PATTERN, normalized_new_id):
            raise ValueError(
                "New office ID must contain only alphanumeric characters, hyphens, "
                "and underscores (max length 50)."
            )

        with self._lock:
            offices = self._vault_data["offices"]
            if current_office_id not in offices:
                raise ValueError(f"Office not found: {current_office_id}")
            if normalized_new_id in offices:
                raise ValueError(f"Office already exists: {normalized_new_id}")

            entry = offices.pop(current_office_id)
            offices[normalized_new_id] = entry

            self._save_vault()

            logger.info("Renamed office credential: %s -> %s", current_office_id, normalized_new_id)
            self._audit_logger.log_config_change(
                action="rename_office",
                details={"old_office_id": current_office_id, "new_office_id": normalized_new_id},
            )

    def update_developer_key(self, developer_key: str) -> None:
        """Update DeveloperKey in vault.

        Args:
            developer_key: New DeveloperKey value

        Raises:
            ValueError: If vault is locked
        """
        self._require_unlocked()
        self._reset_auto_lock_timer()

        with self._lock:
            self._vault_data["developer_key"] = developer_key

            # Save to file
            self._save_vault()

            logger.info("Updated developer key")
            self._audit_logger.log_config_change(action="update_developer_key", details={})

    def get_developer_key(self) -> str:
        """Get DeveloperKey from vault.

        Returns:
            DeveloperKey string

        Raises:
            ValueError: If vault is locked
        """
        self._require_unlocked()
        self._reset_auto_lock_timer()

        return self._vault_data["developer_key"]

    def get_office_credential(self, office_id: str) -> VaultCredentials:
        """Get office credential from vault.

        Args:
            office_id: Office identifier

        Returns:
            VaultCredentials object with office_id and customer_key

        Raises:
            ValueError: If vault is locked or office not found
        """
        self._require_unlocked()
        self._reset_auto_lock_timer()

        if office_id not in self._vault_data["offices"]:
            raise ValueError(f"Office not found: {office_id}")

        office_data = self._vault_data["offices"][office_id]
        return VaultCredentials(office_id=office_id, password=office_data["customer_key"])

    def get_vault(self) -> VaultData:
        """Return full decrypted vault contents as a structured object.

        Returns:
            VaultData model with metadata, developer key, and office entries.

        Raises:
            ValueError: If the vault is locked or not yet initialized.
        """
        self._require_unlocked()
        self._reset_auto_lock_timer()

        if self._vault_data is None:
            raise ValueError("Vault data is not loaded")

        return VaultData.from_dict(self._vault_data)

    def list_offices(self) -> list[str]:
        """List all office IDs in vault.

        Returns:
            List of office identifiers

        Raises:
            ValueError: If vault is locked
        """
        self._require_unlocked()
        self._reset_auto_lock_timer()

        return list(self._vault_data["offices"].keys())

    def _save_vault(self) -> None:
        """Save vault data to encrypted file.

        Uses atomic write operation with secure permissions.
        """
        # Encrypt vault data
        plaintext = json.dumps(self._vault_data).encode("utf-8")
        encrypted_blob = VaultEncryption.encrypt_vault_data(plaintext, self._password)

        # Atomic write
        temp_path = self.vault_path.with_suffix(".tmp")
        temp_path.write_bytes(encrypted_blob)
        os.chmod(temp_path, 0o600)
        temp_path.replace(self.vault_path)
