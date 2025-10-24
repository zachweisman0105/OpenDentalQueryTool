"""Unit tests for VaultManager class."""

import time
from pathlib import Path

import pytest

from opendental_query.core.vault import VaultManager


class TestVaultInit:
    """Tests for vault initialization."""

    def test_init_creates_vault_file(self, tmp_config_dir: Path) -> None:
        """Test that init creates vault file."""
        vault_path = tmp_config_dir / "test.vault"
        password = "SecurePassword123!"
        developer_key = "dev_key_abc123"

        manager = VaultManager(vault_path)
        manager.init(password, developer_key)

        assert vault_path.exists()

    def test_init_sets_secure_permissions(self, tmp_config_dir: Path) -> None:
        """Test that vault file has 0600 permissions."""
        import stat
        import sys

        vault_path = tmp_config_dir / "test.vault"
        password = "SecurePassword123!"
        developer_key = "dev_key_abc123"

        manager = VaultManager(vault_path)
        manager.init(password, developer_key)

        # Check permissions (on Unix-like systems only)
        if sys.platform != "win32" and hasattr(stat, "S_IMODE"):
            mode = stat.S_IMODE(vault_path.stat().st_mode)
            # Owner read/write only
            assert mode & 0o600 == 0o600
            # No group/other permissions
            assert mode & 0o077 == 0
        else:
            # On Windows, just verify file was created
            assert vault_path.exists()

    def test_init_already_exists_raises_error(self, tmp_config_dir: Path) -> None:
        """Test that initializing existing vault raises error."""
        vault_path = tmp_config_dir / "test.vault"
        password = "SecurePassword123!"
        developer_key = "dev_key_abc123"

        manager = VaultManager(vault_path)
        manager.init(password, developer_key)

        with pytest.raises(ValueError, match="already exists"):
            manager.init(password, developer_key)


class TestPasswordStrength:
    """Tests for password strength validation."""

    def test_valid_strong_password(self, tmp_config_dir: Path) -> None:
        """Test that strong password is accepted."""
        vault_path = tmp_config_dir / "test.vault"
        password = "MySecureP@ssw0rd123"
        developer_key = "dev_key_abc123"

        manager = VaultManager(vault_path)
        manager.init(password, developer_key)  # Should not raise

    def test_password_too_short(self, tmp_config_dir: Path) -> None:
        """Test that password < 12 chars is rejected."""
        vault_path = tmp_config_dir / "test.vault"
        password = "Short1@"  # Only 7 chars
        developer_key = "dev_key_abc123"

        manager = VaultManager(vault_path)

        with pytest.raises(ValueError, match="at least 12 characters"):
            manager.init(password, developer_key)

    def test_password_no_uppercase(self, tmp_config_dir: Path) -> None:
        """Test that password without uppercase is rejected."""
        vault_path = tmp_config_dir / "test.vault"
        password = "lowercase123!@#"  # No uppercase
        developer_key = "dev_key_abc123"

        manager = VaultManager(vault_path)

        with pytest.raises(ValueError, match="uppercase"):
            manager.init(password, developer_key)

    def test_password_no_lowercase(self, tmp_config_dir: Path) -> None:
        """Test that password without lowercase is rejected."""
        vault_path = tmp_config_dir / "test.vault"
        password = "UPPERCASE123!@#"  # No lowercase
        developer_key = "dev_key_abc123"

        manager = VaultManager(vault_path)

        with pytest.raises(ValueError, match="lowercase"):
            manager.init(password, developer_key)

    def test_password_no_digit(self, tmp_config_dir: Path) -> None:
        """Test that password without digit is rejected."""
        vault_path = tmp_config_dir / "test.vault"
        password = "NoDigitsHere!@#"  # No digits
        developer_key = "dev_key_abc123"

        manager = VaultManager(vault_path)

        with pytest.raises(ValueError, match="digit"):
            manager.init(password, developer_key)

    def test_password_no_special_char(self, tmp_config_dir: Path) -> None:
        """Test that password without special character is rejected."""
        vault_path = tmp_config_dir / "test.vault"
        password = "NoSpecialChar123"  # No special chars
        developer_key = "dev_key_abc123"

        manager = VaultManager(vault_path)

        with pytest.raises(ValueError, match="special character"):
            manager.init(password, developer_key)


class TestVaultLockout:
    """Tests for 3-attempt lockout mechanism."""

    def test_three_failed_attempts_locks_vault(self, tmp_config_dir: Path) -> None:
        """Test that 3 failed unlock attempts lock the vault."""
        vault_path = tmp_config_dir / "test.vault"
        correct_password = "CorrectPassword123!"
        wrong_password = "WrongPassword123!"
        developer_key = "dev_key_abc123"

        manager = VaultManager(vault_path)
        manager.init(correct_password, developer_key)
        manager.lock()

        # First failed attempt
        assert not manager.unlock(wrong_password)

        # Second failed attempt
        assert not manager.unlock(wrong_password)

        # Third failed attempt
        assert not manager.unlock(wrong_password)

        # Vault should now be locked
        # Even correct password should fail due to lockout
        with pytest.raises(ValueError, match="locked"):
            manager.unlock(correct_password)

    def test_lockout_cooldown_60_seconds(self, tmp_config_dir: Path) -> None:
        """Test that lockout lasts 60 seconds."""
        vault_path = tmp_config_dir / "test.vault"
        correct_password = "CorrectPassword123!"
        wrong_password = "WrongPassword123!"
        developer_key = "dev_key_abc123"

        # Set shorter timeout for testing BEFORE initialization
        manager = VaultManager(vault_path)
        manager._lockout_duration = 1  # 1 second for testing

        manager.init(correct_password, developer_key)
        manager.lock()

        # Trigger 3 failed attempts
        for _ in range(3):
            manager.unlock(wrong_password)

        # Should be locked
        with pytest.raises(ValueError, match="locked"):
            manager.unlock(correct_password)

        # Wait for lockout to expire
        time.sleep(1.5)

        # Should be unlocked after cooldown
        assert manager.unlock(correct_password)

    def test_successful_unlock_resets_failed_attempts(self, tmp_config_dir: Path) -> None:
        """Test that successful unlock resets failed attempt counter."""
        vault_path = tmp_config_dir / "test.vault"
        correct_password = "CorrectPassword123!"
        wrong_password = "WrongPassword123!"
        developer_key = "dev_key_abc123"

        manager = VaultManager(vault_path)
        manager.init(correct_password, developer_key)
        manager.lock()

        # Two failed attempts
        manager.unlock(wrong_password)
        manager.unlock(wrong_password)

        # Successful unlock
        assert manager.unlock(correct_password)
        manager.lock()

        # Should be able to try 3 more times
        manager.unlock(wrong_password)
        manager.unlock(wrong_password)
        manager.unlock(wrong_password)

        # Now locked again
        with pytest.raises(ValueError, match="locked"):
            manager.unlock(correct_password)


class TestVaultAutoLock:
    """Tests for 15-minute inactivity auto-lock."""

    def test_auto_lock_after_15_minutes(self, tmp_config_dir: Path) -> None:
        """Test that vault auto-locks after 15 minutes of inactivity."""
        vault_path = tmp_config_dir / "test.vault"
        password = "SecurePassword123!"
        developer_key = "dev_key_abc123"

        manager = VaultManager(vault_path)
        manager.init(password, developer_key)

        # Vault should be unlocked
        assert manager.is_unlocked()

        # Set shorter timeout for testing (1 second)
        manager._auto_lock_timeout = 1
        manager._start_auto_lock_timer()

        # Wait for auto-lock
        time.sleep(1.5)

        # Vault should now be locked
        assert not manager.is_unlocked()

    def test_vault_access_resets_auto_lock_timer(self, tmp_config_dir: Path) -> None:
        """Test that accessing vault resets the auto-lock timer."""
        vault_path = tmp_config_dir / "test.vault"
        password = "SecurePassword123!"
        developer_key = "dev_key_abc123"

        manager = VaultManager(vault_path)
        manager.init(password, developer_key)
        manager._auto_lock_timeout = 2  # 2 seconds

        # Access vault multiple times
        time.sleep(1)
        manager.get_developer_key()  # Reset timer

        time.sleep(1)
        manager.list_offices()  # Reset timer

        time.sleep(1)
        # Should still be unlocked (timer kept resetting)
        assert manager.is_unlocked()


class TestVaultOperations:
    """Tests for vault CRUD operations."""

    def test_add_office_credential(self, tmp_config_dir: Path) -> None:
        """Test adding office credential to vault."""
        vault_path = tmp_config_dir / "test.vault"
        password = "SecurePassword123!"
        developer_key = "dev_key_abc123"

        manager = VaultManager(vault_path)
        manager.init(password, developer_key)

        manager.add_office("office1", "customer_key_xyz789")

        # Verify credential was added
        offices = manager.list_offices()
        assert "office1" in offices

    def test_remove_office_credential(self, tmp_config_dir: Path) -> None:
        """Test removing office credential from vault."""
        vault_path = tmp_config_dir / "test.vault"
        password = "SecurePassword123!"
        developer_key = "dev_key_abc123"

        manager = VaultManager(vault_path)
        manager.init(password, developer_key)
        manager.add_office("office1", "customer_key_xyz789")

        manager.remove_office("office1")

        # Verify credential was removed
        offices = manager.list_offices()
        assert "office1" not in offices

    def test_update_developer_key(self, tmp_config_dir: Path) -> None:
        """Test updating developer key in vault."""
        vault_path = tmp_config_dir / "test.vault"
        password = "SecurePassword123!"
        old_key = "old_dev_key_123"
        new_key = "new_dev_key_456"

        manager = VaultManager(vault_path)
        manager.init(password, old_key)

        manager.update_developer_key(new_key)

        # Verify key was updated
        assert manager.get_developer_key() == new_key

    def test_get_office_credential(self, tmp_config_dir: Path) -> None:
        """Test retrieving office credential from vault."""
        vault_path = tmp_config_dir / "test.vault"
        password = "SecurePassword123!"
        developer_key = "dev_key_abc123"

        manager = VaultManager(vault_path)
        manager.init(password, developer_key)
        manager.add_office("office1", "customer_key_xyz789")

        credential = manager.get_office_credential("office1")

        assert credential.office_id == "office1"
        assert credential.password == "customer_key_xyz789"

    def test_operations_require_unlocked_vault(self, tmp_config_dir: Path) -> None:
        """Test that operations fail on locked vault."""
        vault_path = tmp_config_dir / "test.vault"
        password = "SecurePassword123!"
        developer_key = "dev_key_abc123"

        manager = VaultManager(vault_path)
        manager.init(password, developer_key)
        manager.lock()

        with pytest.raises(ValueError, match="locked"):
            manager.add_office("office1", "key123")

        with pytest.raises(ValueError, match="locked"):
            manager.get_developer_key()
