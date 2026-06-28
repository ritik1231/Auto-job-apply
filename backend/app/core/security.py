"""JWT handling (RS256) and symmetric encryption for stored Gmail OAuth tokens."""

from __future__ import annotations

import base64
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from cryptography.fernet import Fernet, InvalidToken
from jose import ExpiredSignatureError, JWTError, jwt

from app.core.config import settings
from app.domain.exceptions import InvalidTokenError, TokenExpiredError

# ── RSA key loading ────────────────────────────────────────────────────────────
# Priority: inline base64 env var (production) → PEM file (local dev)


def _load_private_key() -> str:
    if settings.JWT_PRIVATE_KEY:
        return base64.b64decode(settings.JWT_PRIVATE_KEY).decode()
    path = Path(settings.JWT_PRIVATE_KEY_PATH)
    if not path.exists():
        raise RuntimeError(
            "JWT private key not found. Set JWT_PRIVATE_KEY (base64 PEM) or "
            "generate files: openssl genrsa -out secrets/private.pem 2048 && "
            "openssl rsa -in secrets/private.pem -pubout -out secrets/public.pem"
        )
    return path.read_text()


def _load_public_key() -> str:
    if settings.JWT_PUBLIC_KEY:
        return base64.b64decode(settings.JWT_PUBLIC_KEY).decode()
    path = Path(settings.JWT_PUBLIC_KEY_PATH)
    if not path.exists():
        raise RuntimeError(
            "JWT public key not found. Set JWT_PUBLIC_KEY (base64 PEM) or "
            "generate: openssl rsa -in secrets/private.pem -pubout -out secrets/public.pem"
        )
    return path.read_text()


# ── JWT ────────────────────────────────────────────────────────────────────────


def create_access_token(user_id: str, email: str) -> str:
    expire = datetime.now(tz=UTC) + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    payload: dict[str, Any] = {
        "sub": user_id,
        "email": email,
        "type": "access",
        "exp": expire,
    }
    return jwt.encode(payload, _load_private_key(), algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(user_id: str) -> str:
    expire = datetime.now(tz=UTC) + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    payload: dict[str, Any] = {
        "sub": user_id,
        "type": "refresh",
        "exp": expire,
    }
    return jwt.encode(payload, _load_private_key(), algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict[str, Any]:
    try:
        payload: dict[str, Any] = jwt.decode(
            token, _load_public_key(), algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except ExpiredSignatureError as err:
        raise TokenExpiredError("Token has expired") from err
    except JWTError as err:
        raise InvalidTokenError("Invalid token") from err


# ── Gmail token encryption (Fernet / AES-128-CBC + HMAC-SHA256) ───────────────


def _get_fernet() -> Fernet:
    key = settings.GMAIL_TOKEN_ENCRYPTION_KEY
    if not key:
        raise RuntimeError(
            "GMAIL_TOKEN_ENCRYPTION_KEY is not set. "
            'Generate with: python -c "from cryptography.fernet import Fernet; '
            'print(Fernet.generate_key().decode())"'
        )
    return Fernet(key.encode())


def encrypt_token(plaintext: str) -> str:
    return _get_fernet().encrypt(plaintext.encode()).decode()


def decrypt_token(ciphertext: str) -> str:
    try:
        return _get_fernet().decrypt(ciphertext.encode()).decode()
    except InvalidToken as exc:
        raise InvalidTokenError("Failed to decrypt stored token") from exc
