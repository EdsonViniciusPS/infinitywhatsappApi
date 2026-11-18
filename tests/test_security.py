"""Unit tests for security helpers."""

from app.core.security import (
    API_KEY_PREFIX,
    create_access_token,
    decode_access_token,
    generate_api_key,
    hash_api_key,
    verify_constant_time,
)


def test_generate_and_hash_api_key() -> None:
    raw_key, prefix, key_hash = generate_api_key()
    assert raw_key.startswith(API_KEY_PREFIX)
    assert prefix == raw_key[:12]
    assert len(key_hash) == 64
    assert hash_api_key(raw_key) == key_hash


def test_jwt_roundtrip() -> None:
    token = create_access_token("tenant-123", extra_claims={"is_admin": False})
    claims = decode_access_token(token)
    assert claims["sub"] == "tenant-123"
    assert claims["is_admin"] is False


def test_constant_time_compare() -> None:
    assert verify_constant_time("secret", "secret") is True
    assert verify_constant_time("secret", "other") is False
