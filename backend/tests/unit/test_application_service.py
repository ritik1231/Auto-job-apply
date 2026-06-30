"""Unit tests for ApplicationService — prepare flow, guard conditions."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.application.services.application_service import ApplicationService
from app.domain.entities.application import ApplicationEntity, ApplicationStatus
from app.domain.entities.job_post import JobPostEntity
from app.domain.entities.resume import ResumeEntity
from app.domain.exceptions import InvalidJobPostError, ResumeNotFoundError
from app.domain.interfaces.ai_provider import (
    EmailGenerationResult,
    ResumeMatchResult,
    TokenUsage,
)

# ── Fixtures ──────────────────────────────────────────────────────────────────

_UID = uuid.uuid4()
_JOB_ID = uuid.uuid4()
_RESUME_ID = uuid.uuid4()
_APP_ID = uuid.uuid4()
_NOW = datetime.now(tz=UTC)


def _job(**ov) -> JobPostEntity:
    d = {
        "id": _JOB_ID,
        "user_id": _UID,
        "raw_content": "We are hiring a Python engineer.",
        "content_hash": "abc",
        "company": "Acme",
        "recruiter_name": "Bob",
        "recruiter_email": "bob@acme.com",
        "job_title": "Python Engineer",
        "skills": ["Python", "FastAPI"],
        "experience_required": "3 years",
        "responsibilities": ["Build APIs"],
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
        "parsed_text": "5 years of Python and FastAPI experience.",
        "parsed_metadata": {"char_count": 40, "extraction_successful": True},
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
        "matching_skills": ["Python", "FastAPI"],
        "missing_skills": [],
        "generated_subject": "Application for Python Engineer",
        "generated_email": "Dear Bob,\n\nI am excited to apply...",
        "status": ApplicationStatus.DRAFT,
        "sent_at": None,
        "gmail_message_id": None,
        "error_message": None,
        "created_at": _NOW,
        "updated_at": _NOW,
    }
    d.update(ov)
    return ApplicationEntity(**d)


def _match() -> ResumeMatchResult:
    return ResumeMatchResult(
        match_score=0.8,
        matching_skills=["Python", "FastAPI"],
        missing_skills=[],
        fit_summary="Strong match",
    )


def _email() -> EmailGenerationResult:
    return EmailGenerationResult(
        subject="Application for Python Engineer",
        body="Dear Bob,\n\nI am excited to apply...",
    )


def _make_service(
    job=None,
    resume=None,
    existing_app=None,
) -> tuple[ApplicationService, MagicMock, MagicMock, MagicMock, MagicMock]:
    app_repo = MagicMock()
    app_repo.create = AsyncMock(return_value=_app())
    app_repo.get_by_id = AsyncMock(return_value=existing_app)
    app_repo.get_by_user_and_job_post = AsyncMock(return_value=None)
    app_repo.list_for_user = AsyncMock(return_value=[])

    job_repo = MagicMock()
    job_repo.get_by_id = AsyncMock(return_value=job)

    resume_repo = MagicMock()
    resume_repo.get_active_for_user = AsyncMock(return_value=resume)

    ai = MagicMock()
    ai.analyze_resume_match = AsyncMock(return_value=(_match(), TokenUsage()))
    ai.generate_application_email = AsyncMock(return_value=(_email(), TokenUsage()))

    quota = MagicMock()
    quota.enforce = AsyncMock(return_value=None)
    quota.record_usage = AsyncMock(return_value=None)

    return (
        ApplicationService(app_repo, job_repo, resume_repo, ai, quota),
        app_repo,
        job_repo,
        resume_repo,
        ai,
    )


# ── prepare_application ───────────────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.unit
async def test_prepare_happy_path_calls_both_ai_methods():
    service, app_repo, _, _, ai = _make_service(job=_job(), resume=_resume())
    result = await service.prepare_application(_UID, _JOB_ID)

    ai.analyze_resume_match.assert_called_once()
    ai.generate_application_email.assert_called_once()
    app_repo.create.assert_called_once()
    assert result.status == ApplicationStatus.DRAFT


@pytest.mark.asyncio
@pytest.mark.unit
async def test_prepare_persists_match_and_email_data():
    service, app_repo, _, _, _ = _make_service(job=_job(), resume=_resume())
    await service.prepare_application(_UID, _JOB_ID)

    kwargs = app_repo.create.call_args.kwargs
    assert kwargs["match_score"] == 0.8
    assert kwargs["matching_skills"] == ["Python", "FastAPI"]
    assert kwargs["generated_subject"] == "Application for Python Engineer"
    assert kwargs["status"] == ApplicationStatus.DRAFT


@pytest.mark.asyncio
@pytest.mark.unit
async def test_prepare_job_not_found_raises():
    service, *_ = _make_service(job=None, resume=_resume())
    with pytest.raises(InvalidJobPostError):
        await service.prepare_application(_UID, _JOB_ID)


@pytest.mark.asyncio
@pytest.mark.unit
async def test_prepare_job_wrong_user_raises():
    wrong_user_job = _job(user_id=uuid.uuid4())
    service, *_ = _make_service(job=wrong_user_job, resume=_resume())
    with pytest.raises(InvalidJobPostError):
        await service.prepare_application(_UID, _JOB_ID)


@pytest.mark.asyncio
@pytest.mark.unit
async def test_prepare_no_active_resume_raises():
    service, *_ = _make_service(job=_job(), resume=None)
    with pytest.raises(ResumeNotFoundError):
        await service.prepare_application(_UID, _JOB_ID)


@pytest.mark.asyncio
@pytest.mark.unit
async def test_prepare_resume_with_no_parsed_text_still_proceeds():
    """Empty parsed_text is a degraded state but should not block the flow."""
    resume_no_text = _resume(parsed_text=None)
    service, app_repo, _, _, ai = _make_service(job=_job(), resume=resume_no_text)

    await service.prepare_application(_UID, _JOB_ID)

    # AI is still called with an empty string
    call_args = ai.analyze_resume_match.call_args
    assert call_args.args[1] == "" or call_args.kwargs.get("resume_text") == ""


@pytest.mark.asyncio
@pytest.mark.unit
async def test_prepare_match_score_stored_in_create_call():
    service, app_repo, _, _, ai = _make_service(job=_job(), resume=_resume())
    ai.analyze_resume_match = AsyncMock(
        return_value=(
            ResumeMatchResult(
                match_score=0.55, matching_skills=["Python"], missing_skills=["Docker"]
            ),
            TokenUsage(),
        )
    )
    await service.prepare_application(_UID, _JOB_ID)
    assert app_repo.create.call_args.kwargs["match_score"] == 0.55


# ── get / list ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.unit
async def test_get_application_not_found_raises():
    service, app_repo, *_ = _make_service(job=_job(), resume=_resume())
    app_repo.get_by_id = AsyncMock(return_value=None)
    with pytest.raises(InvalidJobPostError):
        await service.get_application(_UID, uuid.uuid4())


@pytest.mark.asyncio
@pytest.mark.unit
async def test_get_application_wrong_user_raises():
    other_user_app = _app(user_id=uuid.uuid4())
    service, app_repo, *_ = _make_service(job=_job(), resume=_resume())
    app_repo.get_by_id = AsyncMock(return_value=other_user_app)
    with pytest.raises(InvalidJobPostError):
        await service.get_application(_UID, _APP_ID)


@pytest.mark.asyncio
@pytest.mark.unit
async def test_list_applications_delegates_to_repo():
    service, app_repo, *_ = _make_service(job=_job(), resume=_resume())
    apps = [_app()]
    app_repo.list_for_user = AsyncMock(return_value=apps)
    result = await service.list_applications(_UID)
    assert result == apps
    app_repo.list_for_user.assert_called_once_with(_UID, limit=20, offset=0)


# ── list_applications_with_job_info ───────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.unit
async def test_history_returns_correct_job_info():
    service, app_repo, job_repo, *_ = _make_service(job=_job(), resume=_resume())
    app_repo.list_for_user = AsyncMock(return_value=[_app(status=ApplicationStatus.SENT)])
    job_repo.get_by_id = AsyncMock(return_value=_job())

    result = await service.list_applications_with_job_info(_UID)

    assert len(result) == 1
    assert result[0].id == _APP_ID
    assert result[0].job_title == "Python Engineer"
    assert result[0].company == "Acme"
    assert result[0].match_score == 0.8
    assert result[0].status == ApplicationStatus.SENT


@pytest.mark.asyncio
@pytest.mark.unit
async def test_history_missing_job_gives_none_title_and_company():
    """If the job row was deleted after the application was created, fields are None."""
    service, app_repo, job_repo, *_ = _make_service(job=_job(), resume=_resume())
    app_repo.list_for_user = AsyncMock(return_value=[_app(status=ApplicationStatus.SENT)])
    job_repo.get_by_id = AsyncMock(return_value=None)

    result = await service.list_applications_with_job_info(_UID)

    assert len(result) == 1
    assert result[0].job_title is None
    assert result[0].company is None


@pytest.mark.asyncio
@pytest.mark.unit
async def test_history_deduplicates_job_fetches():
    """Two applications for the same job should trigger only one repo call."""
    service, app_repo, job_repo, *_ = _make_service(job=_job(), resume=_resume())
    app1 = _app(id=uuid.uuid4(), status=ApplicationStatus.SENT)
    app2 = _app(
        id=uuid.uuid4(), status=ApplicationStatus.SENT
    )  # same job_post_id (_JOB_ID) by default
    app_repo.list_for_user = AsyncMock(return_value=[app1, app2])
    job_repo.get_by_id = AsyncMock(return_value=_job())

    await service.list_applications_with_job_info(_UID)

    assert job_repo.get_by_id.call_count == 1


@pytest.mark.asyncio
@pytest.mark.unit
async def test_history_empty_list_returns_empty():
    service, app_repo, job_repo, *_ = _make_service()
    app_repo.list_for_user = AsyncMock(return_value=[])

    result = await service.list_applications_with_job_info(_UID)

    assert result == []
    job_repo.get_by_id.assert_not_called()
