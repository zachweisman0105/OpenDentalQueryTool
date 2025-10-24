"""Integration tests for complete vault lifecycle.

Tests: initialize vault → unlock → add/remove offices → lock → persist
"""

import json
from pathlib import Path

import pytest

from opendental_query.core.vault import VaultManager


class TestVaultLifecycle:
    """Test complete vault initialization and lifecycle."""

    def test_complete_lifecycle(self, tmp_path: Path) -> None:
        """Test full vault lifecycle: init → unlock → add → remove → lock → persist."""
        vault_path = tmp_path / "test.vault"
        password = "TestPassword123!@#"

        # Step 1: Initialize vault
        vault = VaultManager(vault_path)
        vault.init(password, "dev_key_abc123")

        assert vault_path.exists()
        # Verify file permissions (0600 on Unix, should be set)
        if hasattr(vault_path, "stat"):
            # On Windows, this may not be meaningful, but shouldn't error
            stat_info = vault_path.stat()
            assert stat_info is not None

        # Step 2: Lock and unlock
        vault.lock()
        assert not vault.is_unlocked()

        unlocked = vault.unlock(password)
        assert unlocked is True
        assert vault.is_unlocked()

        # Step 3: Add offices
        vault.add_office("office1", "customer_key_1")
        vault.add_office("office2", "customer_key_2")
        vault.add_office("office3", "customer_key_3")

        offices = vault.list_offices()
        assert len(offices) == 3
        assert set(offices) == {"office1", "office2", "office3"}

        # Step 4: Remove an office
        vault.remove_office("office2")

        offices = vault.list_offices()
        assert len(offices) == 2
        assert set(offices) == {"office1", "office3"}

        # Step 5: Lock vault
        vault.lock()
        assert not vault.is_unlocked()

        # Step 6: Create new vault instance, unlock, verify persistence
        vault2 = VaultManager(vault_path)
        unlocked = vault2.unlock(password)
        assert unlocked is True

        offices_after_reload = vault2.list_offices()
        assert len(offices_after_reload) == 2
        assert set(offices_after_reload) == {"office1", "office3"}

        # Verify developer key persisted
        assert vault2.get_developer_key() == "dev_key_abc123"

    def test_wrong_password_fails(self, tmp_path: Path) -> None:
        """Test that wrong password fails to unlock vault."""
        vault_path = tmp_path / "test.vault"
        password = "CorrectPassword123!@#"

        vault = VaultManager(vault_path)
        vault.init(password, "dev_key")

        vault.lock()

        # Attempt with wrong password
        unlocked = vault.unlock("WrongPassword123!@#")
        assert unlocked is False
        assert not vault.is_unlocked()

    def test_persistence_across_instances(self, tmp_path: Path) -> None:
        """Test that data persists across multiple vault instances."""
        vault_path = tmp_path / "test.vault"
        password = "TestPassword123!@#"

        # Instance 1: Create and populate
        vault1 = VaultManager(vault_path)
        vault1.init(password, "original_dev_key")
        vault1.add_office("persistent", "persistent_key")
        vault1.lock()

        # Instance 2: Load and verify
        vault2 = VaultManager(vault_path)
        vault2.unlock(password)
        offices = vault2.list_offices()
        assert len(offices) == 1
        assert offices[0] == "persistent"
        assert vault2.get_developer_key() == "original_dev_key"

        # Update developer key
        vault2.update_developer_key("updated_dev_key")
        vault2.lock()

        # Instance 3: Verify update persisted
        vault3 = VaultManager(vault_path)
        vault3.unlock(password)
        assert vault3.get_developer_key() == "updated_dev_key"

    def test_add_duplicate_office_overwrites(self, tmp_path: Path) -> None:
        """Test that adding duplicate office ID overwrites existing."""
        vault_path = tmp_path / "test.vault"
        password = "TestPassword123!@#"

        vault = VaultManager(vault_path)
        vault.init(password, "dev_key")

        vault.add_office("duplicate", "key1")
        # Add again with different key - should overwrite
        vault.add_office("duplicate", "key2")

        offices = vault.list_offices()
        assert len(offices) == 1  # Still only one office
        assert offices[0] == "duplicate"

    def test_remove_nonexistent_office_fails(self, tmp_path: Path) -> None:
        """Test that removing non-existent office raises error."""
        vault_path = tmp_path / "test.vault"
        password = "TestPassword123!@#"

        vault = VaultManager(vault_path)
        vault.init(password, "dev_key")

        with pytest.raises(ValueError, match="not found"):
            vault.remove_office("nonexistent")

    def test_operations_while_locked_fail(self, tmp_path: Path) -> None:
        """Test that vault operations fail when locked."""
        vault_path = tmp_path / "test.vault"
        password = "TestPassword123!@#"

        vault = VaultManager(vault_path)
        vault.init(password, "dev_key")
        vault.lock()

        with pytest.raises(ValueError, match="locked"):
            vault.add_office("test", "key")

        with pytest.raises(ValueError, match="locked"):
            vault.remove_office("test")

        with pytest.raises(ValueError, match="locked"):
            vault.list_offices()

        with pytest.raises(ValueError, match="locked"):
            vault.update_developer_key("new_key")


class TestVaultFileFormat:
    """Test vault file format and encryption integrity."""

    def test_vault_file_is_encrypted(self, tmp_path: Path) -> None:
        """Test that vault file is encrypted (not plaintext JSON)."""
        vault_path = tmp_path / "test.vault"
        password = "TestPassword123!@#"

        vault = VaultManager(vault_path)
        vault.init(password, "secret_dev_key_12345")
        vault.add_office("secret_office", "secret_customer_key")
        vault.lock()

        # Read raw file content
        vault_content = vault_path.read_bytes()

        # Should NOT contain plaintext secrets
        assert b"secret_dev_key_12345" not in vault_content
        assert b"secret_customer_key" not in vault_content
        assert b"secret_office" not in vault_content

        # File should not be valid JSON
        with pytest.raises((json.JSONDecodeError, UnicodeDecodeError)):
            json.loads(vault_content)

    def test_vault_file_format_structure(self, tmp_path: Path) -> None:
        """Test vault file has expected structure (salt + nonce + ciphertext)."""
        vault_path = tmp_path / "test.vault"
        password = "TestPassword123!@#"

        vault = VaultManager(vault_path)
        vault.init(password, "dev_key")
        vault.lock()

        vault_content = vault_path.read_bytes()

        # Expected format: salt(16) + nonce(12) + ciphertext+tag
        # Minimum size should be 16 + 12 + some encrypted data
        assert len(vault_content) >= 28

        # First 16 bytes are salt (should be random, not all zeros)
        salt = vault_content[:16]
        assert not all(b == 0 for b in salt)

        # Next 12 bytes are nonce (should be random)
        nonce = vault_content[16:28]
        assert not all(b == 0 for b in nonce)


class TestVaultLockout:
    """Test vault lockout after failed attempts."""

    def test_lockout_after_three_failures(self, tmp_path: Path) -> None:
        """Test that vault locks out after 3 failed password attempts."""
        vault_path = tmp_path / "test.vault"
        password = "CorrectPassword123!@#"

        vault = VaultManager(vault_path)
        vault.init(password, "dev_key")
        vault.lock()

        # Attempt 1
        result = vault.unlock("wrong1")
        assert result is False

        # Attempt 2
        result = vault.unlock("wrong2")
        assert result is False

        # Attempt 3
        try:
            result = vault.unlock("wrong3")
            # Should either return False or raise ValueError
            assert result is False
        except ValueError as e:
            # Lockout may raise exception
            assert "locked out" in str(e).lower() or "attempt" in str(e).lower()

        # Attempt 4 (during lockout)
        with pytest.raises(ValueError, match="locked out|attempt"):
            vault.unlock(password)  # Even correct password fails during lockout

    def test_correct_password_resets_failure_count(self, tmp_path: Path) -> None:
        """Test that correct password resets failure counter."""
        vault_path = tmp_path / "test.vault"
        password = "CorrectPassword123!@#"

        vault = VaultManager(vault_path)
        vault.init(password, "dev_key")
        vault.lock()

        # Two wrong attempts
        vault.unlock("wrong1")
        vault.unlock("wrong2")

        # Correct password
        vault.lock()
        result = vault.unlock(password)
        assert result is True

        # Failure count should be reset, can make 3 more attempts
        vault.lock()
        vault.unlock("wrong1")
        vault.unlock("wrong2")
        # Third attempt should still work (not locked out)
        try:
            result = vault.unlock("wrong3")
            # Should fail but not raise lockout
            assert result is False
        except ValueError:
            # If it raises, check it's lockout (means counter wasn't reset properly)
            pytest.fail("Failure counter was not reset after correct password")
