"""Unit tests for ApplicationSendRequest.validate_email field validator."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.application.dto.application_dto import ApplicationSendRequest


@pytest.mark.unit
def test_valid_email_passes():
    req = ApplicationSendRequest(to_address="recruiter@company.com")
    assert req.to_address == "recruiter@company.com"


@pytest.mark.unit
def test_none_passes_through():
    req = ApplicationSendRequest(to_address=None)
    assert req.to_address is None


@pytest.mark.unit
def test_missing_field_defaults_to_none():
    req = ApplicationSendRequest()
    assert req.to_address is None


@pytest.mark.unit
def test_empty_string_becomes_none():
    req = ApplicationSendRequest(to_address="")
    assert req.to_address is None


@pytest.mark.unit
def test_whitespace_only_becomes_none():
    req = ApplicationSendRequest(to_address="   ")
    assert req.to_address is None


@pytest.mark.unit
def test_whitespace_trimmed_around_valid_email():
    req = ApplicationSendRequest(to_address="  user@example.com  ")
    assert req.to_address == "user@example.com"


@pytest.mark.unit
def test_invalid_email_raises_validation_error():
    with pytest.raises(ValidationError) as exc_info:
        ApplicationSendRequest(to_address="not-an-email")
    assert "Invalid email address format" in str(exc_info.value)


@pytest.mark.unit
def test_email_missing_at_raises():
    with pytest.raises(ValidationError):
        ApplicationSendRequest(to_address="userexample.com")


@pytest.mark.unit
def test_email_missing_tld_raises():
    with pytest.raises(ValidationError):
        ApplicationSendRequest(to_address="user@example")


@pytest.mark.unit
def test_plus_addressing_valid():
    req = ApplicationSendRequest(to_address="user+filter@example.com")
    assert req.to_address == "user+filter@example.com"
