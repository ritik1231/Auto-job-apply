"""Google OAuth 2.0 authentication endpoints."""

from __future__ import annotations

import re
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.application.services.auth_service import AuthService
from app.dependencies import get_auth_service, get_current_user
from app.domain.entities.user import UserEntity

router = APIRouter()

_CHROMIUM_REDIRECT_RE = re.compile(r"^https://[a-z0-9]+\.chromiumapp\.org/")


def _require_chromium_redirect(redirect_uri: str) -> str:
    if not _CHROMIUM_REDIRECT_RE.match(redirect_uri):
        raise HTTPException(status_code=400, detail="redirect_uri must be a chromiumapp.org URL")
    return redirect_uri


class AuthorizeResponse(BaseModel):
    auth_url: str


class CallbackResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class ExchangeRequest(BaseModel):
    code: str
    redirect_uri: str
    code_verifier: str | None = None


class ExchangeResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    name: str | None
    picture_url: str | None


ExchangeResponse.model_rebuild()


@router.get("/google/authorize", response_model=AuthorizeResponse)
async def google_authorize(
    redirect_uri: str | None = Query(None),
    code_challenge: str | None = Query(None),
    service: AuthService = Depends(get_auth_service),
) -> AuthorizeResponse:
    """Return the Google OAuth authorization URL.

    Pass ``redirect_uri`` (a chromiumapp.org URL) and ``code_challenge`` (PKCE S256)
    when calling from the Chrome extension.
    """
    effective_redirect: str | None = None
    if redirect_uri:
        effective_redirect = _require_chromium_redirect(redirect_uri)
    return AuthorizeResponse(
        auth_url=service.get_google_auth_url(effective_redirect, code_challenge)
    )


@router.get("/google/callback", response_model=CallbackResponse)
async def google_callback(
    code: str,
    service: AuthService = Depends(get_auth_service),
) -> CallbackResponse:
    """Exchange the Google authorization code for app tokens (web flow)."""
    _, access_token, refresh_token = await service.handle_google_callback(code)
    return CallbackResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/exchange", response_model=ExchangeResponse)
async def exchange_code(
    body: ExchangeRequest,
    service: AuthService = Depends(get_auth_service),
) -> ExchangeResponse:
    """Exchange a Google authorization code captured by the Chrome extension for tokens."""
    _require_chromium_redirect(body.redirect_uri)
    user, access_token, refresh_token = await service.handle_google_callback(
        body.code, body.redirect_uri, body.code_verifier
    )
    return ExchangeResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserResponse(
            id=user.id,
            email=user.email,
            name=user.name,
            picture_url=user.picture_url,
        ),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    body: RefreshRequest,
    service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    """Issue a new access token using a valid refresh token."""
    access_token = await service.refresh_access_token(body.refresh_token)
    return TokenResponse(access_token=access_token)


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: UserEntity = Depends(get_current_user),
) -> UserResponse:
    """Return the authenticated user's profile."""
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        name=current_user.name,
        picture_url=current_user.picture_url,
    )


@router.post("/logout")
async def logout() -> dict[str, str]:
    """Signal logout — client must discard stored tokens."""
    return {"message": "logged out"}
