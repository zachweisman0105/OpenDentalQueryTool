"""Vault encryption primitives using Argon2id + AES-256-GCM.

This module provides low-level cryptographic functions for securing vault data:
- Argon2id key derivation for password-based encryption
- AES-256-GCM authenticated encryption
- Secure random salt generation

All cryptographic operations follow OWASP best practices for password storage
and data encryption.
"""

import os

from argon2.low_level import Type, hash_secret_raw
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from opendental_query.constants import (
    ARGON2_MEMORY_COST,
    ARGON2_PARALLELISM,
    ARGON2_TIME_COST,
)


def generate_salt() -> bytes:
    """Generate a cryptographically secure random salt.

    Returns:
        16 bytes of random data suitable for use as a salt
    """
    return os.urandom(16)


def derive_key(password: str, salt: bytes) -> bytes:
    """Derive a 256-bit encryption key from password using Argon2id.

    Uses memory-hard Argon2id algorithm with the following parameters:
    - Time cost: 3 iterations
    - Memory cost: 64 MB (65536 KB)
    - Parallelism: 4 threads
    - Hash length: 32 bytes (256 bits) for AES-256

    Args:
        password: Master password string
        salt: 16-byte salt for key derivation

    Returns:
        32-byte derived key suitable for AES-256 encryption
    """
    # Use Argon2id (type 2) for key derivation
    key = hash_secret_raw(
        secret=password.encode("utf-8"),
        salt=salt,
        time_cost=ARGON2_TIME_COST,
        memory_cost=ARGON2_MEMORY_COST,
        parallelism=ARGON2_PARALLELISM,
        hash_len=32,  # 256 bits for AES-256
        type=Type.ID,  # Argon2id
    )
    return key


def encrypt_data(plaintext: bytes, key: bytes) -> tuple[bytes, bytes]:
    """Encrypt data using AES-256-GCM.

    AES-GCM provides authenticated encryption with associated data (AEAD),
    ensuring both confidentiality and integrity. The authentication tag
    is automatically appended to the ciphertext.

    Args:
        plaintext: Data to encrypt
        key: 32-byte AES-256 key

    Returns:
        Tuple of (ciphertext with auth tag, nonce)
        - ciphertext: Encrypted data with 16-byte GCM tag appended
        - nonce: 12-byte random nonce (must be stored with ciphertext)
    """
    # Generate random 12-byte nonce (96 bits, recommended for GCM)
    nonce = os.urandom(12)

    # Create AES-GCM cipher
    aesgcm = AESGCM(key)

    # Encrypt and authenticate (tag is appended to ciphertext)
    ciphertext = aesgcm.encrypt(nonce, plaintext, None)

    return ciphertext, nonce


def decrypt_data(ciphertext: bytes, nonce: bytes, key: bytes) -> bytes:
    """Decrypt data using AES-256-GCM.

    Decrypts ciphertext and verifies the authentication tag to ensure
    data integrity. Raises exception if authentication fails.

    Args:
        ciphertext: Encrypted data with 16-byte GCM tag appended
        nonce: 12-byte nonce used during encryption
        key: 32-byte AES-256 key

    Returns:
        Decrypted plaintext

    Raises:
        cryptography.exceptions.InvalidTag: If authentication fails
    """
    aesgcm = AESGCM(key)
    plaintext = aesgcm.decrypt(nonce, ciphertext, None)
    return plaintext


class VaultEncryption:
    """High-level vault encryption interface.

    Provides complete encryption/decryption for vault files combining
    Argon2id key derivation with AES-256-GCM encryption.

    Vault file format:
        [salt: 16 bytes][nonce: 12 bytes][ciphertext + tag: variable]
    """

    @staticmethod
    def encrypt_vault_data(plaintext: bytes, password: str) -> bytes:
        """Encrypt vault data with password.

        Generates a random salt, derives an encryption key using Argon2id,
        and encrypts the data using AES-256-GCM. Returns a complete vault
        blob containing salt, nonce, and ciphertext.

        Args:
            plaintext: Vault data to encrypt (typically JSON)
            password: Master password for encryption

        Returns:
            Complete encrypted vault blob: salt + nonce + ciphertext
        """
        # Generate random salt
        salt = generate_salt()

        # Derive encryption key from password
        key = derive_key(password, salt)

        # Encrypt data
        ciphertext, nonce = encrypt_data(plaintext, key)

        # Combine into vault blob: salt || nonce || ciphertext
        vault_blob = salt + nonce + ciphertext

        return vault_blob

    @staticmethod
    def decrypt_vault_data(vault_blob: bytes, password: str) -> bytes:
        """Decrypt vault data with password.

        Extracts salt and nonce from vault blob, derives encryption key,
        and decrypts the ciphertext.

        Args:
            vault_blob: Complete encrypted vault blob
            password: Master password for decryption

        Returns:
            Decrypted plaintext vault data

        Raises:
            ValueError: If vault blob is malformed
            cryptography.exceptions.InvalidTag: If authentication fails (wrong password)
        """
        # Validate minimum size: salt(16) + nonce(12) + ciphertext+tag(>=16)
        if len(vault_blob) < 16 + 12 + 16:
            raise ValueError("Invalid vault blob: too small")

        # Extract components
        salt = vault_blob[:16]
        nonce = vault_blob[16:28]
        ciphertext = vault_blob[28:]

        # Derive decryption key from password
        key = derive_key(password, salt)

        # Decrypt data
        plaintext = decrypt_data(ciphertext, nonce, key)

        return plaintext
