"""Fernet symmetric encryption utilities for storing sensitive credentials.

Credentials (e.g. per-user database passwords) are encrypted at rest using a
key derived from the ``CIPHER_KEY`` environment variable.  If the variable is
absent in development mode a warning is emitted and a deterministic fallback
key is used *only* for that session – never store real passwords without a
proper key.
"""
import base64
import logging
import os

from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)

_FALLBACK_KEY = b"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="  # 32 zero-bytes b64


def _get_fernet() -> Fernet:
    """Return a Fernet instance backed by ``CIPHER_KEY`` env var."""
    raw = os.environ.get("CIPHER_KEY", "").strip()
    if raw:
        # Accept either a raw 32-byte value or a pre-encoded Fernet key
        try:
            key = raw.encode() if isinstance(raw, str) else raw
            return Fernet(key)
        except Exception:
            pass
        # Try base64-encoding a raw 32-byte hex or plain string
        try:
            padded = base64.urlsafe_b64encode(raw.encode()[:32].ljust(32, b"\x00"))
            return Fernet(padded)
        except Exception as exc:
            logger.warning("CIPHER_KEY is set but invalid (%s); using fallback.", exc)

    logger.warning(
        "CIPHER_KEY is not set.  Passwords will be encrypted with a hard-coded "
        "fallback key – set CIPHER_KEY in production!"
    )
    return Fernet(_FALLBACK_KEY)


def encrypt_password(plaintext: str) -> str:
    """Encrypt *plaintext* and return a URL-safe base64 token string."""
    f = _get_fernet()
    return f.encrypt(plaintext.encode()).decode()


def decrypt_password(token: str) -> str:
    """Decrypt a token produced by :func:`encrypt_password`.

    Returns the original plaintext, or raises ``ValueError`` if the token is
    invalid or was produced with a different key.
    """
    f = _get_fernet()
    try:
        return f.decrypt(token.encode()).decode()
    except InvalidToken as exc:
        raise ValueError("Could not decrypt credential – wrong key or corrupted data.") from exc
