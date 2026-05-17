"""Unit tests for API key security helpers."""

import pytest

from app.core.security import generate_api_key, hash_api_key, verify_api_key


def test_generate_api_key_uses_expected_prefix() -> None:
    """Generated API keys should use the service prefix."""

    generated = generate_api_key()

    assert generated.startswith("grd_")
    assert len(generated) > 20


def test_hash_api_key_is_stable_and_normalized() -> None:
    """Hashing should be deterministic and ignore surrounding whitespace."""

    expected = hash_api_key("sample-key", "test-salt")

    assert hash_api_key("  sample-key  ", "test-salt") == expected
    assert len(expected) == 64


def test_verify_api_key_matches_expected_hash() -> None:
    """Verification should succeed only for the matching raw API key."""

    stored_hash = hash_api_key("sample-key", "test-salt")

    assert verify_api_key("sample-key", stored_hash, "test-salt")
    assert not verify_api_key("wrong-key", stored_hash, "test-salt")


def test_hash_api_key_rejects_blank_inputs() -> None:
    """Hashing should fail fast for blank API keys or salts."""

    with pytest.raises(ValueError):
        hash_api_key("", "test-salt")

    with pytest.raises(ValueError):
        hash_api_key("sample-key", "   ")
