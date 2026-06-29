"""Google OAuth 2.0 authentication endpoints."""

from __future__ import annotations

import re
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.application.services.auth_service import AuthService
from app.dependencies import get_auth_service, get_current_user, get_user_repo
from app.domain.entities.user import UserEntity
from app.domain.interfaces.repositories import IUserRepository

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
    current_ctc: str | None = None
    expected_ctc: str | None = None
    notice_period: str | None = None
    current_location: str | None = None
    total_experience: str | None = None
    linkedin_url: str | None = None


class UserProfileUpdateRequest(BaseModel):
    current_ctc: str | None = None
    expected_ctc: str | None = None
    notice_period: str | None = None
    current_location: str | None = None
    total_experience: str | None = None
    linkedin_url: str | None = None


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
        user=_user_response(user),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    body: RefreshRequest,
    service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    """Issue a new access token using a valid refresh token."""
    access_token = await service.refresh_access_token(body.refresh_token)
    return TokenResponse(access_token=access_token)


def _user_response(user: UserEntity) -> UserResponse:
    return UserResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        picture_url=user.picture_url,
        current_ctc=user.current_ctc,
        expected_ctc=user.expected_ctc,
        notice_period=user.notice_period,
        current_location=user.current_location,
        total_experience=user.total_experience,
        linkedin_url=user.linkedin_url,
    )


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: UserEntity = Depends(get_current_user),
) -> UserResponse:
    """Return the authenticated user's profile."""
    return _user_response(current_user)


@router.patch("/me", response_model=UserResponse)
async def update_me(
    body: UserProfileUpdateRequest,
    current_user: UserEntity = Depends(get_current_user),
    user_repo: IUserRepository = Depends(get_user_repo),
) -> UserResponse:
    """Update editable candidate profile fields."""
    updated = await user_repo.update(current_user.id, **body.model_dump())
    return _user_response(updated or current_user)


@router.post("/logout")
async def logout() -> dict[str, str]:
    """Signal logout — client must discard stored tokens."""
    return {"message": "logged out"}
