"""Google OAuth 2.0 authentication service."""

from __future__ import annotations

import uuid
from datetime import UTC
from typing import Any

import structlog
from google.auth.transport.requests import Request as GoogleAuthRequest
from google.oauth2 import id_token as google_id_token
from google_auth_oauthlib.flow import Flow

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    encrypt_token,
)
from app.domain.entities.user import UserEntity
from app.domain.exceptions import InvalidTokenError, OAuthError
from app.domain.interfaces.repositories import IUserRepository

logger = structlog.get_logger(__name__)

GOOGLE_SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/gmail.send",
]


class AuthService:
    def __init__(self, user_repo: IUserRepository) -> None:
        self._user_repo = user_repo

    def _make_flow(self, redirect_uri: str | None = None) -> Flow:
        if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
            raise OAuthError("Google OAuth credentials are not configured")
        effective_redirect = redirect_uri or settings.GOOGLE_REDIRECT_URI
        client_config: dict[str, Any] = {
            "web": {
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [effective_redirect],
            }
        }
        return Flow.from_client_config(
            client_config,
            scopes=GOOGLE_SCOPES,
            redirect_uri=effective_redirect,
        )

    def get_google_auth_url(
        self, redirect_uri: str | None = None, code_challenge: str | None = None
    ) -> str:
        flow = self._make_flow(redirect_uri)
        kwargs: dict[str, str] = {
            "access_type": "offline",
            "include_granted_scopes": "true",
            "prompt": "consent",
        }
        if code_challenge:
            kwargs["code_challenge"] = code_challenge
            kwargs["code_challenge_method"] = "S256"
        auth_url, _ = flow.authorization_url(**kwargs)
        return auth_url

    async def handle_google_callback(
        self, code: str, redirect_uri: str | None = None, code_verifier: str | None = None
    ) -> tuple[UserEntity, str, str]:
        """Exchange authorization code and return (user, access_token, refresh_token)."""
        try:
            flow = self._make_flow(redirect_uri)
            fetch_kwargs: dict[str, str] = {"code": code}
            if code_verifier:
                fetch_kwargs["code_verifier"] = code_verifier
            flow.fetch_token(**fetch_kwargs)
            credentials = flow.credentials
        except OAuthError:
            raise
        except Exception as exc:
            logger.warning("google oauth token exchange failed", error=str(exc))
            raise OAuthError("Failed to exchange authorization code") from exc

        try:
            request = GoogleAuthRequest()
            id_info: dict[str, Any] = google_id_token.verify_oauth2_token(
                credentials.id_token,
                request,
                settings.GOOGLE_CLIENT_ID,
            )
        except Exception as exc:
            logger.warning("google id token verification failed", error=str(exc))
            raise OAuthError("Failed to verify Google identity") from exc

        google_id: str = id_info["sub"]
        email: str = id_info["email"]
        name: str | None = id_info.get("name")
        picture_url: str | None = id_info.get("picture")

        gmail_access_enc = encrypt_token(credentials.token) if credentials.token else None
        gmail_refresh_enc = (
            encrypt_token(credentials.refresh_token) if credentials.refresh_token else None
        )
        gmail_expiry = credentials.expiry
        if gmail_expiry and gmail_expiry.tzinfo is None:
            gmail_expiry = gmail_expiry.replace(tzinfo=UTC)

        existing = await self._user_repo.get_by_google_id(google_id)
        if existing is None:
            user = await self._user_repo.create(
                google_id=google_id,
                email=email,
                name=name,
                picture_url=picture_url,
                gmail_access_token=gmail_access_enc,
                gmail_refresh_token=gmail_refresh_enc,
                gmail_token_expiry=gmail_expiry,
                is_active=True,
            )
            logger.info("new user created via google oauth", user_id=str(user.id))
        else:
            update_data: dict[str, Any] = {
                "email": email,
                "name": name,
                "picture_url": picture_url,
                "gmail_access_token": gmail_access_enc,
                "gmail_token_expiry": gmail_expiry,
                "is_active": True,
            }
            # Only overwrite stored refresh token when Google issues a new one
            if gmail_refresh_enc:
                update_data["gmail_refresh_token"] = gmail_refresh_enc

            updated = await self._user_repo.update(existing.id, **update_data)
            if updated is None:
                raise OAuthError("Failed to update user record")
            user = updated
            logger.info("existing user signed in via google oauth", user_id=str(user.id))

        access_token = create_access_token(str(user.id), user.email)
        refresh_token = create_refresh_token(str(user.id))
        return user, access_token, refresh_token

    async def refresh_access_token(self, refresh_token: str) -> str:
        payload = decode_token(refresh_token)
        if payload.get("type") != "refresh":
            raise InvalidTokenError("Not a refresh token")
        user = await self._user_repo.get_by_id(uuid.UUID(payload["sub"]))
        if user is None or not user.is_active:
            raise InvalidTokenError("User not found or inactive")
        return create_access_token(str(user.id), user.email)

    async def get_current_user(self, token: str) -> UserEntity:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise InvalidTokenError("Not an access token")
        user = await self._user_repo.get_by_id(uuid.UUID(payload["sub"]))
        if user is None or not user.is_active:
            raise InvalidTokenError("User not found or inactive")
        return user
