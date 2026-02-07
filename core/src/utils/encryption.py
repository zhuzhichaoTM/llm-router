"""
Encryption utilities for LLM Router.
Handles API key encryption and token signing.
"""
import hashlib
import secrets
from typing import Optional
from functools import lru_cache

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64

from src.config.settings import settings


class EncryptionManager:
    """Manages encryption operations for the application."""

    _fernet: Optional[Fernet] = None

    @classmethod
    def get_fernet(cls) -> Fernet:
        """Get or create Fernet instance for encryption."""
        if cls._fernet is None:
            # Derive key from secret key
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=settings.api_key_salt.encode(),
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(settings.secret_key.encode()))
            cls._fernet = Fernet(key)
        return cls._fernet

    @classmethod
    def encrypt(cls, data: str) -> str:
        """
        Encrypt a string.

        Args:
            data: String to encrypt

        Returns:
            Encrypted string (Base64 encoded)
        """
        fernet = cls.get_fernet()
        encrypted = fernet.encrypt(data.encode())
        return base64.urlsafe_b64encode(encrypted).decode()

    @classmethod
    def decrypt(cls, encrypted_data: str) -> str:
        """
        Decrypt an encrypted string.

        Args:
            encrypted_data: Encrypted string (Base64 encoded)

        Returns:
            Decrypted string
        """
        fernet = cls.get_fernet()
        encrypted_bytes = base64.urlsafe_b64decode(encrypted_data.encode())
        decrypted = fernet.decrypt(encrypted_bytes)
        return decrypted.decode()


def hash_api_key(api_key: str, salt: Optional[str] = None) -> str:
    """
    Hash an API key for storage.

    Args:
        api_key: The API key to hash
        salt: Optional salt for hashing (defaults to configured salt)

    Returns:
        Hashed API key
    """
    if salt is None:
        salt = settings.api_key_salt
    return hashlib.sha256((api_key + salt).encode()).hexdigest()


def generate_api_key(prefix: str = "llm") -> str:
    """
    Generate a new API key.

    Args:
        prefix: Prefix for the API key

    Returns:
        Generated API key
    """
    random_bytes = secrets.token_bytes(24)
    random_part = secrets.token_urlsafe(32)
    return f"{prefix}_{random_part}"


def hash_content(content: str) -> str:
    """
    Hash content for caching purposes.

    Args:
        content: Content to hash

    Returns:
        Hashed content
    """
    return hashlib.sha256(content.encode()).hexdigest()


def generate_session_id() -> str:
    """
    Generate a unique session ID.

    Returns:
        Unique session ID
    """
    return secrets.token_urlsafe(16)


def sanitize_for_logging(data: str, mask: str = "*****") -> str:
    """
    Sanitize sensitive data for logging.

    Args:
        data: Data that may contain sensitive information
        mask: Mask string to replace sensitive parts

    Returns:
        Sanitized data
    """
    # Mask API keys (pattern: llm_*** or sk-***)
    if "api_key" in data.lower() or data.startswith("llm_") or data.startswith("sk-"):
        if len(data) > 8:
            return data[:4] + mask + data[-4:]
        return mask
    return data
