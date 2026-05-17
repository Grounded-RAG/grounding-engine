"""Security helpers for API key handling."""

from __future__ import annotations

import hashlib
import hmac
import secrets


API_KEY_PREFIX = "grd_"


def generate_api_key() -> str:
    """Generate a new API key value for future issuance flows."""

    return f"{API_KEY_PREFIX}{secrets.token_urlsafe(32)}"


def hash_api_key(raw_api_key: str, salt: str) -> str:
    """Hash an API key with a stable application salt."""

    normalized_api_key = raw_api_key.strip()
    normalized_salt = salt.strip()
    if not normalized_api_key:
        raise ValueError("API key must not be empty.")
    if not normalized_salt:
        raise ValueError("API key salt must not be empty.")

    material = f"{normalized_salt}:{normalized_api_key}".encode("utf-8")
    return hashlib.sha256(material).hexdigest()


def verify_api_key(raw_api_key: str, stored_hash: str, salt: str) -> bool:
    """Compare a raw API key against a stored hash in constant time."""

    computed_hash = hash_api_key(raw_api_key, salt)
    return hmac.compare_digest(computed_hash, stored_hash)
