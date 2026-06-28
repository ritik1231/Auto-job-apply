"""Unit tests for JobService — hashing, deduplication, AI orchestration."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.application.services.job_service import JobService, compute_content_hash
from app.domain.entities.job_post import JobPostEntity
from app.domain.exceptions import InvalidJobPostError
from app.domain.interfaces.ai_provider import JobExtractionResult

# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_job_entity(**overrides) -> JobPostEntity:
    defaults = {
        "id": uuid.uuid4(),
        "user_id": uuid.uuid4(),
        "raw_content": "We are hiring a Python engineer...",
        "content_hash": "abc123",
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
        "job_summary": "Build backend services",
        "source_url": None,
        "source_platform": "linkedin",
        "created_at": datetime.now(tz=UTC),
    }
    defaults.update(overrides)
    return JobPostEntity(**defaults)


def _make_service(
    cached_job: JobPostEntity | None = None,
    extraction_result: JobExtractionResult | None = None,
) -> tuple[JobService, MagicMock, MagicMock]:
    repo = MagicMock()
    repo.get_by_user_and_hash = AsyncMock(return_value=cached_job)
    repo.create = AsyncMock(return_value=_make_job_entity())

    ai = MagicMock()
    ai.extract_job_details = AsyncMock(
        return_value=extraction_result
        or JobExtractionResult(
            company="Acme",
            recruiter_email="bob@acme.com",
            job_title="Engineer",
            skills=["Python"],
            responsibilities=[],
        )
    )
    return JobService(repo, ai), repo, ai


# ── Content hashing ───────────────────────────────────────────────────────────


@pytest.mark.unit
def test_hash_is_deterministic():
    text = "We are hiring a senior Python engineer at Acme Corp."
    assert compute_content_hash(text) == compute_content_hash(text)


@pytest.mark.unit
def test_hash_normalises_whitespace():
    a = "Senior  Python  engineer"
    b = "Senior Python engineer"
    assert compute_content_hash(a) == compute_content_hash(b)


@pytest.mark.unit
def test_hash_normalises_case():
    assert compute_content_hash("Python ENGINEER") == compute_content_hash("python engineer")


@pytest.mark.unit
def test_different_text_different_hash():
    assert compute_content_hash("role A description") != compute_content_hash("role B description")


@pytest.mark.unit
def test_hash_is_64_hex_chars():
    h = compute_content_hash("any post text here")
    assert len(h) == 64
    assert all(c in "0123456789abcdef" for c in h)


# ── Short post validation ─────────────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.unit
async def test_short_post_raises_invalid_job_post():
    service, _, _ = _make_service()
    with pytest.raises(InvalidJobPostError):
        await service.process_post(uuid.uuid4(), "too short")


@pytest.mark.asyncio
@pytest.mark.unit
async def test_empty_post_raises_invalid_job_post():
    service, _, _ = _make_service()
    with pytest.raises(InvalidJobPostError):
        await service.process_post(uuid.uuid4(), "   ")


# ── Cache hit ─────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.unit
async def test_cache_hit_skips_ai_and_returns_true(monkeypatch):
    cached = _make_job_entity()
    service, repo, ai = _make_service(cached_job=cached)

    long_text = "We are hiring a senior Python engineer. " * 5
    result, from_cache = await service.process_post(uuid.uuid4(), long_text)

    assert from_cache is True
    assert result.id == cached.id
    ai.extract_job_details.assert_not_called()


# ── Cache miss → AI call ──────────────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.unit
async def test_cache_miss_calls_ai_and_persists():
    service, repo, ai = _make_service(cached_job=None)

    long_text = "We are hiring a senior Python engineer at Acme Corp. " * 3
    result, from_cache = await service.process_post(uuid.uuid4(), long_text)

    assert from_cache is False
    ai.extract_job_details.assert_called_once()
    repo.create.assert_called_once()


# ── List / get ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.unit
async def test_list_job_posts_delegates_to_repo():
    service, repo, _ = _make_service()
    jobs = [_make_job_entity()]
    repo.list_for_user = AsyncMock(return_value=jobs)

    result = await service.list_job_posts(uuid.uuid4())
    assert result == jobs
    repo.list_for_user.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.unit
async def test_get_job_post_not_found_raises():
    service, repo, _ = _make_service()
    repo.get_by_id = AsyncMock(return_value=None)

    with pytest.raises(InvalidJobPostError):
        await service.get_job_post(uuid.uuid4(), uuid.uuid4())


@pytest.mark.asyncio
@pytest.mark.unit
async def test_get_job_post_wrong_user_raises():
    user_a = uuid.uuid4()
    user_b = uuid.uuid4()
    job = _make_job_entity(user_id=user_a)

    service, repo, _ = _make_service()
    repo.get_by_id = AsyncMock(return_value=job)

    with pytest.raises(InvalidJobPostError):
        await service.get_job_post(user_b, job.id)
