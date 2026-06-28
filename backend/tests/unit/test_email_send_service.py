"""Unit tests for EmailSendService — send flow and guard conditions."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.application.services.email_send_service import EmailSendService
from app.domain.entities.application import ApplicationEntity, ApplicationStatus
from app.domain.entities.job_post import JobPostEntity
from app.domain.entities.resume import ResumeEntity
from app.domain.exceptions import (
    ApplicationAlreadySentError,
    GmailSendError,
    InvalidJobPostError,
    OAuthError,
)
from app.domain.interfaces.repositories import GmailTokenData

# ── Shared test data ──────────────────────────────────────────────────────────

_UID = uuid.uuid4()
_JOB_ID = uuid.uuid4()
_RESUME_ID = uuid.uuid4()
_APP_ID = uuid.uuid4()
_NOW = datetime.now(tz=UTC)

_TOKEN_DATA = GmailTokenData(
    access_token_enc="enc_access",
    refresh_token_enc="enc_refresh",
    expiry=_NOW,
)


def _job(**ov) -> JobPostEntity:
    d = {
        "id": _JOB_ID,
        "user_id": _UID,
        "raw_content": "Hiring Python engineer",
        "content_hash": "abc",
        "company": "Acme",
        "recruiter_name": "Bob",
        "recruiter_email": "bob@acme.com",
        "job_title": "Python Engineer",
        "skills": ["Python"],
        "experience_required": "3 years",
        "responsibilities": [],
        "location": "Remote",
        "employment_type": "Full-time",
        "seniority": "Mid",
        "job_summary": "Backend role",
        "source_url": None,
        "source_platform": "linkedin",
        "created_at": _NOW,
    }
    d.update(ov)
    return JobPostEntity(**d)


def _resume(**ov) -> ResumeEntity:
    d = {
        "id": _RESUME_ID,
        "user_id": _UID,
        "file_name": "resume.pdf",
        "file_path": "/storage/resume.pdf",
        "file_size": 12345,
        "mime_type": "application/pdf",
        "parsed_text": "5 years Python",
        "parsed_metadata": {},
        "is_active": True,
        "created_at": _NOW,
        "updated_at": _NOW,
    }
    d.update(ov)
    return ResumeEntity(**d)


def _app(**ov) -> ApplicationEntity:
    d = {
        "id": _APP_ID,
        "user_id": _UID,
        "job_post_id": _JOB_ID,
        "resume_id": _RESUME_ID,
        "match_score": 0.8,
        "matching_skills": ["Python"],
        "missing_skills": [],
        "generated_subject": "Application for Python Engineer",
        "generated_email": "Dear Bob,\n\nI want to apply.",
        "status": ApplicationStatus.DRAFT,
        "sent_at": None,
        "gmail_message_id": None,
        "error_message": None,
        "created_at": _NOW,
        "updated_at": _NOW,
    }
    d.update(ov)
    return ApplicationEntity(**d)


def _make_service(
    app=None,
    job=None,
    resume=None,
    token_data=_TOKEN_DATA,
    pdf_bytes=b"%PDF-fake",
) -> tuple[EmailSendService, MagicMock, MagicMock, MagicMock, MagicMock, MagicMock]:
    app_repo = MagicMock()
    app_repo.get_by_id = AsyncMock(return_value=app)
    app_repo.update = AsyncMock(return_value=app)

    job_repo = MagicMock()
    job_repo.get_by_id = AsyncMock(return_value=job)

    resume_repo = MagicMock()
    resume_repo.get_by_id = AsyncMock(return_value=resume)

    user_repo = MagicMock()
    user_repo.get_gmail_tokens = AsyncMock(return_value=token_data)
    user_repo.update_gmail_tokens = AsyncMock()

    storage = MagicMock()
    storage.get = AsyncMock(return_value=pdf_bytes)

    service = EmailSendService(app_repo, job_repo, resume_repo, user_repo, storage)
    return service, app_repo, job_repo, resume_repo, user_repo, storage


# ── Happy path ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.unit
async def test_send_happy_path_marks_sent():
    service, app_repo, *_ = _make_service(app=_app(), job=_job(), resume=_resume())

    with patch("app.application.services.email_send_service.GmailEmailSender") as mock_sender:
        instance = MagicMock()
        instance.send = AsyncMock(return_value="msg_123")
        instance.tokens_refreshed = False
        mock_sender.return_value = instance

        result = await service.send_application(_UID, _APP_ID)

    assert result.gmail_message_id == "msg_123"
    app_repo.update.assert_called_once_with(
        _APP_ID,
        status=ApplicationStatus.SENT,
        sent_at=result.sent_at,
        gmail_message_id="msg_123",
    )


@pytest.mark.asyncio
@pytest.mark.unit
async def test_send_happy_path_passes_pdf_attachment():
    service, *_ = _make_service(app=_app(), job=_job(), resume=_resume())

    with patch("app.application.services.email_send_service.GmailEmailSender") as mock_sender:
        instance = MagicMock()
        instance.send = AsyncMock(return_value="msg_456")
        instance.tokens_refreshed = False
        mock_sender.return_value = instance

        await service.send_application(_UID, _APP_ID)

    call_kwargs = instance.send.call_args.kwargs
    assert call_kwargs["attachment_content"] == b"%PDF-fake"
    assert call_kwargs["attachment_filename"] == "resume.pdf"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_send_uses_to_address_override():
    service, *_ = _make_service(app=_app(), job=_job(), resume=_resume())

    with patch("app.application.services.email_send_service.GmailEmailSender") as mock_sender:
        instance = MagicMock()
        instance.send = AsyncMock(return_value="msg_789")
        instance.tokens_refreshed = False
        mock_sender.return_value = instance

        await service.send_application(_UID, _APP_ID, to_address_override="other@example.com")

    call_kwargs = instance.send.call_args.kwargs
    assert call_kwargs["to_address"] == "other@example.com"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_send_persists_refreshed_tokens():
    service, _, _, _, user_repo, _ = _make_service(app=_app(), job=_job(), resume=_resume())

    with patch("app.application.services.email_send_service.GmailEmailSender") as mock_sender:
        instance = MagicMock()
        instance.send = AsyncMock(return_value="msg_999")
        instance.tokens_refreshed = True
        instance.new_access_token_enc = "new_enc"
        instance.new_expiry = _NOW
        mock_sender.return_value = instance

        await service.send_application(_UID, _APP_ID)

    user_repo.update_gmail_tokens.assert_called_once_with(_UID, "new_enc", _NOW)


# ── Guard conditions ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.unit
async def test_send_app_not_found_raises():
    service, *_ = _make_service(app=None, job=_job(), resume=_resume())
    with pytest.raises(InvalidJobPostError):
        await service.send_application(_UID, _APP_ID)


@pytest.mark.asyncio
@pytest.mark.unit
async def test_send_app_wrong_user_raises():
    other_user_app = _app(user_id=uuid.uuid4())
    service, *_ = _make_service(app=other_user_app, job=_job(), resume=_resume())
    with pytest.raises(InvalidJobPostError):
        await service.send_application(_UID, _APP_ID)


@pytest.mark.asyncio
@pytest.mark.unit
async def test_send_already_sent_raises():
    sent_app = _app(status=ApplicationStatus.SENT)
    service, *_ = _make_service(app=sent_app, job=_job(), resume=_resume())
    with pytest.raises(ApplicationAlreadySentError):
        await service.send_application(_UID, _APP_ID)


@pytest.mark.asyncio
@pytest.mark.unit
async def test_send_no_generated_content_raises():
    empty_app = _app(generated_subject=None, generated_email=None)
    service, *_ = _make_service(app=empty_app, job=_job(), resume=_resume())
    with pytest.raises(InvalidJobPostError):
        await service.send_application(_UID, _APP_ID)


@pytest.mark.asyncio
@pytest.mark.unit
async def test_send_no_recruiter_email_and_no_override_raises():
    job_no_email = _job(recruiter_email=None)
    service, *_ = _make_service(app=_app(), job=job_no_email, resume=_resume())
    with pytest.raises(InvalidJobPostError):
        await service.send_application(_UID, _APP_ID)


@pytest.mark.asyncio
@pytest.mark.unit
async def test_send_no_gmail_tokens_raises():
    service, *_ = _make_service(app=_app(), job=_job(), resume=_resume(), token_data=None)
    with pytest.raises(OAuthError):
        await service.send_application(_UID, _APP_ID)


@pytest.mark.asyncio
@pytest.mark.unit
async def test_send_empty_gmail_tokens_raises():
    empty_tokens = GmailTokenData(access_token_enc=None, refresh_token_enc=None, expiry=None)
    service, *_ = _make_service(app=_app(), job=_job(), resume=_resume(), token_data=empty_tokens)
    with pytest.raises(OAuthError):
        await service.send_application(_UID, _APP_ID)


@pytest.mark.asyncio
@pytest.mark.unit
async def test_send_gmail_failure_marks_failed_and_reraises():
    service, app_repo, *_ = _make_service(app=_app(), job=_job(), resume=_resume())

    with patch("app.application.services.email_send_service.GmailEmailSender") as mock_sender:
        instance = MagicMock()
        instance.send = AsyncMock(side_effect=GmailSendError("API error"))
        instance.tokens_refreshed = False
        mock_sender.return_value = instance

        with pytest.raises(GmailSendError):
            await service.send_application(_UID, _APP_ID)

    app_repo.update.assert_called_once_with(
        _APP_ID,
        status=ApplicationStatus.FAILED,
        error_message="Email delivery failed via Gmail API",
    )


@pytest.mark.asyncio
@pytest.mark.unit
async def test_send_no_tokens_not_refreshed_when_tokens_refreshed_false():
    service, _, _, _, user_repo, _ = _make_service(app=_app(), job=_job(), resume=_resume())

    with patch("app.application.services.email_send_service.GmailEmailSender") as mock_sender:
        instance = MagicMock()
        instance.send = AsyncMock(return_value="msg_ok")
        instance.tokens_refreshed = False
        mock_sender.return_value = instance

        await service.send_application(_UID, _APP_ID)

    user_repo.update_gmail_tokens.assert_not_called()
