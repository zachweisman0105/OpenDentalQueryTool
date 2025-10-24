"""Unit tests for vault encryption primitives (Argon2id + AES-GCM)."""

import os

import pytest
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from opendental_query.core.vault_encryption import (
    VaultEncryption,
    decrypt_data,
    derive_key,
    encrypt_data,
    generate_salt,
)


class TestArgon2KeyDerivation:
    """Tests for Argon2id key derivation."""

    def test_derive_key_produces_32_bytes(self) -> None:
        """Test that derived key is 32 bytes (256 bits) for AES-256."""
        password = "test_password_123"
        salt = os.urandom(16)

        key = derive_key(password, salt)

        assert len(key) == 32

    def test_derive_key_deterministic(self) -> None:
        """Test that same password and salt produce same key."""
        password = "test_password_123"
        salt = os.urandom(16)

        key1 = derive_key(password, salt)
        key2 = derive_key(password, salt)

        assert key1 == key2

    def test_derive_key_different_salts(self) -> None:
        """Test that different salts produce different keys."""
        password = "test_password_123"
        salt1 = os.urandom(16)
        salt2 = os.urandom(16)

        key1 = derive_key(password, salt1)
        key2 = derive_key(password, salt2)

        assert key1 != key2

    def test_derive_key_different_passwords(self) -> None:
        """Test that different passwords produce different keys."""
        salt = os.urandom(16)

        key1 = derive_key("password1", salt)
        key2 = derive_key("password2", salt)

        assert key1 != key2

    def test_argon2_parameters(self) -> None:
        """Test Argon2id uses correct parameters (64MB, 3 iterations, 4 parallelism)."""
        from argon2.low_level import Type

        # PasswordHasher should be configured with our security parameters
        hasher = PasswordHasher(
            time_cost=3,
            memory_cost=65536,  # 64MB
            parallelism=4,
            hash_len=32,
            type=Type.ID,  # Argon2id
        )

        password = "test_password_123"
        hash_result = hasher.hash(password)

        # Verify hash can be validated
        hasher.verify(hash_result, password)

        # Wrong password should fail
        with pytest.raises(VerifyMismatchError):
            hasher.verify(hash_result, "wrong_password")


class TestAESGCMEncryption:
    """Tests for AES-256-GCM encryption/decryption."""

    def test_encrypt_decrypt_roundtrip(self) -> None:
        """Test encryption and decryption produce original plaintext."""
        key = os.urandom(32)  # 256-bit key
        plaintext = b"Secret data to encrypt"

        ciphertext, nonce = encrypt_data(plaintext, key)
        decrypted = decrypt_data(ciphertext, nonce, key)

        assert decrypted == plaintext

    def test_encrypt_produces_different_output(self) -> None:
        """Test that encrypting same plaintext twice produces different ciphertext (due to random nonce)."""
        key = os.urandom(32)
        plaintext = b"Secret data"

        ciphertext1, nonce1 = encrypt_data(plaintext, key)
        ciphertext2, nonce2 = encrypt_data(plaintext, key)

        # Nonces should be different
        assert nonce1 != nonce2
        # Ciphertexts should be different
        assert ciphertext1 != ciphertext2

    def test_decrypt_with_wrong_key_fails(self) -> None:
        """Test that decryption with wrong key raises exception."""
        key1 = os.urandom(32)
        key2 = os.urandom(32)
        plaintext = b"Secret data"

        ciphertext, nonce = encrypt_data(plaintext, key1)

        with pytest.raises(Exception):  # cryptography raises InvalidTag
            decrypt_data(ciphertext, nonce, key2)

    def test_decrypt_with_wrong_nonce_fails(self) -> None:
        """Test that decryption with wrong nonce raises exception."""
        key = os.urandom(32)
        plaintext = b"Secret data"

        ciphertext, nonce = encrypt_data(plaintext, key)
        wrong_nonce = os.urandom(12)

        with pytest.raises(Exception):
            decrypt_data(ciphertext, wrong_nonce, key)

    def test_nonce_is_12_bytes(self) -> None:
        """Test that nonce is 12 bytes (96 bits) as per AES-GCM standard."""
        key = os.urandom(32)
        plaintext = b"Test data"

        _, nonce = encrypt_data(plaintext, key)

        assert len(nonce) == 12

    def test_ciphertext_includes_auth_tag(self) -> None:
        """Test that ciphertext includes 16-byte authentication tag."""
        key = os.urandom(32)
        plaintext = b"Test"

        ciphertext, _ = encrypt_data(plaintext, key)

        # Ciphertext should be plaintext length + 16 bytes (GCM tag)
        assert len(ciphertext) == len(plaintext) + 16


class TestVaultEncryptionClass:
    """Tests for VaultEncryption high-level class."""

    def test_encrypt_vault_data(self) -> None:
        """Test encrypting vault data with password."""
        password = "secure_password_123"
        plaintext = b'{"offices": {"office1": {"key": "secret123"}}}'

        encrypted_blob = VaultEncryption.encrypt_vault_data(plaintext, password)

        # Blob format: salt(16) + nonce(12) + ciphertext+tag
        assert len(encrypted_blob) >= 16 + 12 + len(plaintext) + 16

    def test_decrypt_vault_data(self) -> None:
        """Test decrypting vault data with password."""
        password = "secure_password_123"
        plaintext = b'{"offices": {"office1": {"key": "secret123"}}}'

        encrypted_blob = VaultEncryption.encrypt_vault_data(plaintext, password)
        decrypted = VaultEncryption.decrypt_vault_data(encrypted_blob, password)

        assert decrypted == plaintext

    def test_decrypt_with_wrong_password_fails(self) -> None:
        """Test that decryption with wrong password raises exception."""
        password1 = "password123"
        password2 = "wrong_password"
        plaintext = b'{"data": "secret"}'

        encrypted_blob = VaultEncryption.encrypt_vault_data(plaintext, password1)

        with pytest.raises(Exception):
            VaultEncryption.decrypt_vault_data(encrypted_blob, password2)

    def test_roundtrip_with_json_data(self) -> None:
        """Test encryption/decryption with realistic JSON vault data."""
        import json

        password = "MySecurePassword123!"
        vault_data = {
            "developer_key": "dev_key_abc123",
            "offices": {
                "main-office": {"customer_key": "cust_key_xyz789"},
                "branch-office": {"customer_key": "cust_key_def456"},
            },
        }

        plaintext = json.dumps(vault_data).encode("utf-8")
        encrypted_blob = VaultEncryption.encrypt_vault_data(plaintext, password)
        decrypted = VaultEncryption.decrypt_vault_data(encrypted_blob, password)
        decrypted_data = json.loads(decrypted.decode("utf-8"))

        assert decrypted_data == vault_data


class TestGenerateSalt:
    """Tests for salt generation."""

    def test_generate_salt_length(self) -> None:
        """Test that generated salt is 16 bytes."""
        salt = generate_salt()
        assert len(salt) == 16

    def test_generate_salt_randomness(self) -> None:
        """Test that generated salts are different."""
        salt1 = generate_salt()
        salt2 = generate_salt()

        assert salt1 != salt2
