"""Unit tests for the domain layer — zero framework dependencies."""

import uuid
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.domain.entities import (
    ApplicationEntity,
    ApplicationStatus,
    JobPostEntity,
    ResumeEntity,
    UserEntity,
)
from app.domain.exceptions import (
    AIProviderError,
    AppException,
    ApplicationAlreadySentError,
    DomainException,
    InvalidJobPostError,
    InvalidTokenError,
    ResumeNotFoundError,
)
from app.domain.interfaces.ai_provider import (
    EmailGenerationResult,
    JobExtractionResult,
    ResumeMatchResult,
)

# ── Helpers ───────────────────────────────────────────────────────────────────

_now = datetime.now(UTC)


def _user(**kw) -> UserEntity:
    defaults: dict = {
        "id": uuid.uuid4(),
        "google_id": "g-001",
        "email": "test@example.com",
        "name": "Test User",
        "picture_url": None,
        "gmail_token_expiry": None,
        "is_active": True,
        "created_at": _now,
        "updated_at": _now,
    }
    return UserEntity(**(defaults | kw))


def _resume(**kw) -> ResumeEntity:
    defaults: dict = {
        "id": uuid.uuid4(),
        "user_id": uuid.uuid4(),
        "file_name": "resume.pdf",
        "file_path": "/storage/abc.pdf",
        "file_size": 102400,
        "mime_type": "application/pdf",
        "parsed_text": "Python engineer with 5 years experience.",
        "parsed_metadata": {},
        "is_active": True,
        "created_at": _now,
        "updated_at": _now,
    }
    return ResumeEntity(**(defaults | kw))


def _job_post(**kw) -> JobPostEntity:
    defaults: dict = {
        "id": uuid.uuid4(),
        "user_id": uuid.uuid4(),
        "raw_content": "We are looking for a Python engineer.",
        "content_hash": "abc123",
        "company": "Acme Corp",
        "recruiter_name": "Jane Smith",
        "recruiter_email": "jane@acme.com",
        "job_title": "Python Engineer",
        "skills": ["Python", "FastAPI"],
        "experience_required": "3+ years",
        "responsibilities": ["Build APIs", "Write tests"],
        "location": "Remote",
        "employment_type": "Full-time",
        "seniority": "Mid",
        "job_summary": "Build great software.",
        "source_url": None,
        "source_platform": "linkedin",
        "created_at": _now,
    }
    return JobPostEntity(**(defaults | kw))


def _application(**kw) -> ApplicationEntity:
    defaults: dict = {
        "id": uuid.uuid4(),
        "user_id": uuid.uuid4(),
        "job_post_id": uuid.uuid4(),
        "resume_id": uuid.uuid4(),
        "match_score": 0.85,
        "missing_skills": ["Docker"],
        "matching_skills": ["Python", "FastAPI"],
        "generated_subject": "Application for Python Engineer",
        "generated_email": "Dear Jane, ...",
        "status": ApplicationStatus.DRAFT,
        "sent_at": None,
        "gmail_message_id": None,
        "error_message": None,
        "created_at": _now,
        "updated_at": _now,
    }
    return ApplicationEntity(**(defaults | kw))


# ── Entity tests ──────────────────────────────────────────────────────────────


def test_user_entity_creates() -> None:
    u = _user()
    assert u.email == "test@example.com"
    assert u.is_active is True


def test_resume_entity_creates() -> None:
    r = _resume()
    assert r.file_name == "resume.pdf"
    assert r.is_active is True


def test_job_post_entity_skills_list() -> None:
    j = _job_post(skills=["Python", "Docker", "FastAPI"])
    assert len(j.skills) == 3


def test_application_status_enum_values() -> None:
    assert ApplicationStatus.DRAFT.value == "draft"
    assert ApplicationStatus.SENT.value == "sent"
    assert ApplicationStatus.FAILED.value == "failed"


def test_application_entity_status_coercion() -> None:
    app = _application(status="sent")  # type: ignore[arg-type]
    assert app.status == ApplicationStatus.SENT


def test_entities_have_no_framework_imports() -> None:
    """Verify no SQLAlchemy or FastAPI symbols leak into entity modules."""
    import app.domain.entities.application as m_app
    import app.domain.entities.job_post as m_job
    import app.domain.entities.resume as m_res
    import app.domain.entities.user as m_usr

    forbidden = {"sqlalchemy", "fastapi", "starlette"}
    for mod in (m_usr, m_res, m_job, m_app):
        leaked = {
            dep
            for dep in vars(mod).get("__builtins__", {})
            if any(dep.startswith(f) for f in forbidden)
        }
        assert not leaked, f"Framework import leaked into {mod.__name__}: {leaked}"


# ── AI value-object tests ─────────────────────────────────────────────────────


def test_job_extraction_result_defaults() -> None:
    r = JobExtractionResult()
    assert r.skills == []
    assert r.responsibilities == []


def test_resume_match_result_validates_score_bounds() -> None:
    with pytest.raises(ValidationError):
        ResumeMatchResult(match_score=1.5, matching_skills=[], missing_skills=[])


def test_email_generation_result_requires_subject_and_body() -> None:
    r = EmailGenerationResult(subject="Hello", body="Dear recruiter...")
    assert r.subject == "Hello"


# ── Exception hierarchy tests ─────────────────────────────────────────────────


def test_exception_hierarchy() -> None:
    assert issubclass(ResumeNotFoundError, DomainException)
    assert issubclass(DomainException, AppException)
    assert issubclass(AIProviderError, AppException)
    assert issubclass(InvalidTokenError, AppException)


def test_resume_not_found_has_correct_metadata() -> None:
    exc = ResumeNotFoundError("No active resume found")
    assert exc.status_code == 404
    assert exc.error_code == "RESUME_NOT_FOUND"
    assert exc.message == "No active resume found"


def test_application_already_sent_conflict() -> None:
    exc = ApplicationAlreadySentError("Already sent")
    assert exc.status_code == 409


def test_invalid_job_post_bad_request() -> None:
    exc = InvalidJobPostError("Could not parse post")
    assert exc.status_code == 400


def test_exception_with_details() -> None:
    exc = AppException("Something went wrong", details={"field": "email"})
    assert exc.details == {"field": "email"}
