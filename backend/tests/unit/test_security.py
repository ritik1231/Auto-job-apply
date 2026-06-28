"""Unit tests for app/core/security.py — JWT encode/decode roundtrip and token encryption."""

from __future__ import annotations

import uuid
from datetime import UTC
from unittest.mock import patch

import pytest
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from app.domain.exceptions import InvalidTokenError, TokenExpiredError

# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def rsa_key_pair(tmp_path_factory: pytest.TempPathFactory) -> tuple[str, str]:
    """Generate a temporary RSA-2048 key pair; return (private_pem, public_pem) paths."""
    tmp = tmp_path_factory.mktemp("secrets")
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    public_pem = (
        private_key.public_key()
        .public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode()
    )
    priv_path = tmp / "private.pem"
    pub_path = tmp / "public.pem"
    priv_path.write_text(private_pem)
    pub_path.write_text(public_pem)
    return str(priv_path), str(pub_path)


@pytest.fixture
def patch_jwt_keys(rsa_key_pair: tuple[str, str]):
    priv_path, pub_path = rsa_key_pair
    with patch("app.core.security.settings") as mock_settings:
        mock_settings.JWT_PRIVATE_KEY = None  # use file path, not inline base64
        mock_settings.JWT_PUBLIC_KEY = None
        mock_settings.JWT_PRIVATE_KEY_PATH = priv_path
        mock_settings.JWT_PUBLIC_KEY_PATH = pub_path
        mock_settings.JWT_ALGORITHM = "RS256"
        mock_settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 60
        mock_settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS = 30
        yield mock_settings


@pytest.fixture
def fernet_key() -> str:
    return Fernet.generate_key().decode()


# ── JWT tests ─────────────────────────────────────────────────────────────────


@pytest.mark.unit
def test_access_token_roundtrip(patch_jwt_keys):
    from app.core.security import create_access_token, decode_token

    user_id = str(uuid.uuid4())
    email = "test@example.com"

    token = create_access_token(user_id, email)
    payload = decode_token(token)

    assert payload["sub"] == user_id
    assert payload["email"] == email
    assert payload["type"] == "access"


@pytest.mark.unit
def test_refresh_token_roundtrip(patch_jwt_keys):
    from app.core.security import create_refresh_token, decode_token

    user_id = str(uuid.uuid4())

    token = create_refresh_token(user_id)
    payload = decode_token(token)

    assert payload["sub"] == user_id
    assert payload["type"] == "refresh"


@pytest.mark.unit
def test_invalid_token_raises(patch_jwt_keys):
    from app.core.security import decode_token

    with pytest.raises(InvalidTokenError):
        decode_token("not.a.valid.token")


@pytest.mark.unit
def test_expired_token_raises(patch_jwt_keys):
    from datetime import datetime, timedelta

    from jose import jwt as jose_jwt

    from app.core.security import _load_private_key, decode_token

    expired_payload = {
        "sub": str(uuid.uuid4()),
        "email": "x@example.com",
        "type": "access",
        "exp": datetime.now(tz=UTC) - timedelta(seconds=1),
    }
    token = jose_jwt.encode(expired_payload, _load_private_key(), algorithm="RS256")

    with pytest.raises(TokenExpiredError):
        decode_token(token)


# ── Encryption tests ──────────────────────────────────────────────────────────


@pytest.mark.unit
def test_encrypt_decrypt_roundtrip(fernet_key: str):
    with patch("app.core.security.settings") as mock_settings:
        mock_settings.GMAIL_TOKEN_ENCRYPTION_KEY = fernet_key
        from app.core.security import decrypt_token, encrypt_token

        plaintext = "ya29.some-google-oauth-token"
        encrypted = encrypt_token(plaintext)
        assert encrypted != plaintext
        assert decrypt_token(encrypted) == plaintext


@pytest.mark.unit
def test_decrypt_invalid_ciphertext_raises(fernet_key: str):
    with patch("app.core.security.settings") as mock_settings:
        mock_settings.GMAIL_TOKEN_ENCRYPTION_KEY = fernet_key
        from app.core.security import decrypt_token

        with pytest.raises(InvalidTokenError):
            decrypt_token("not-valid-ciphertext")
