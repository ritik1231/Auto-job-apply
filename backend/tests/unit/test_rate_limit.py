"""Unit tests for app.core.rate_limit.get_user_key."""

from __future__ import annotations

import uuid
from unittest.mock import patch

import pytest
from starlette.requests import Request

from app.core.rate_limit import get_user_key

# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_request(auth_header: str | None = None, client_host: str = "1.2.3.4") -> Request:
    headers: list[tuple[bytes, bytes]] = []
    if auth_header is not None:
        headers.append((b"authorization", auth_header.encode()))
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "query_string": b"",
        "headers": headers,
        "client": (client_host, 12345),
    }
    return Request(scope)


# ── Tests ─────────────────────────────────────────────────────────────────────


@pytest.mark.unit
def test_valid_bearer_token_returns_user_key():
    user_id = str(uuid.uuid4())
    request = _make_request(auth_header="Bearer sometoken")
    with patch("app.core.security.decode_token", return_value={"sub": user_id}):
        key = get_user_key(request)
    assert key == f"user:{user_id}"


@pytest.mark.unit
def test_valid_bearer_token_without_sub_falls_back_to_ip():
    request = _make_request(auth_header="Bearer sometoken", client_host="10.0.0.1")
    with patch("app.core.security.decode_token", return_value={}):
        key = get_user_key(request)
    assert key == "10.0.0.1"


@pytest.mark.unit
def test_invalid_bearer_token_falls_back_to_ip():
    request = _make_request(auth_header="Bearer badtoken", client_host="10.0.0.2")
    with patch("app.core.security.decode_token", side_effect=Exception("invalid signature")):
        key = get_user_key(request)
    assert key == "10.0.0.2"


@pytest.mark.unit
def test_no_auth_header_falls_back_to_ip():
    request = _make_request(auth_header=None, client_host="192.168.1.1")
    key = get_user_key(request)
    assert key == "192.168.1.1"


@pytest.mark.unit
def test_non_bearer_scheme_falls_back_to_ip():
    request = _make_request(auth_header="Basic dXNlcjpwYXNz", client_host="172.16.0.1")
    key = get_user_key(request)
    assert key == "172.16.0.1"


@pytest.mark.unit
def test_bearer_prefix_only_no_token_falls_back_to_ip():
    """'Bearer ' with nothing after the space — decode_token called with empty string."""
    request = _make_request(auth_header="Bearer ", client_host="10.10.10.10")
    with patch("app.core.security.decode_token", side_effect=Exception("empty token")):
        key = get_user_key(request)
    assert key == "10.10.10.10"
