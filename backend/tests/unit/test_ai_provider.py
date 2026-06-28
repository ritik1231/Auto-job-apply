"""Unit tests for the AI provider abstraction layer.

These tests cover prompt loading and JSON response parsing.
No real Gemini API calls are made — the network layer is mocked.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.domain.exceptions import AIResponseParseError
from app.domain.interfaces.ai_provider import (
    EmailGenerationResult,
    JobExtractionResult,
    ResumeMatchResult,
)
from app.infrastructure.ai import prompt_loader

# ── Prompt loader ─────────────────────────────────────────────────────────────


@pytest.mark.unit
def test_prompt_loader_returns_system_and_user():
    system, user = prompt_loader.render("job_extraction_v1", post_text="Software Engineer role")
    assert len(system) > 0
    assert "Software Engineer role" in user


@pytest.mark.unit
def test_prompt_loader_user_has_user_input_delimiters():
    _, user = prompt_loader.render("job_extraction_v1", post_text="anything")
    assert "<USER_INPUT>" in user
    assert "</USER_INPUT>" in user


@pytest.mark.unit
def test_prompt_loader_resume_match_substitution():
    _, user = prompt_loader.render(
        "resume_match_v1",
        job_title="Backend Engineer",
        skills="Python, FastAPI",
        experience_required="3 years",
        job_summary="Build APIs",
        resume_text="5 years Python experience",
    )
    assert "Backend Engineer" in user
    assert "Python, FastAPI" in user
    assert "5 years Python experience" in user


@pytest.mark.unit
def test_prompt_loader_email_generation_substitution():
    _, user = prompt_loader.render(
        "email_generation_v1",
        job_title="Data Engineer",
        company="Acme Corp",
        recruiter_name="Alice",
        skills="SQL, Spark",
        job_summary="Process data at scale",
        match_score="80%",
        matching_skills="SQL",
        missing_skills="Spark",
        resume_text="Led ETL pipelines",
    )
    assert "Acme Corp" in user
    assert "Alice" in user
    assert "Led ETL pipelines" in user


@pytest.mark.unit
def test_prompt_loader_missing_template_raises():
    with pytest.raises(FileNotFoundError):
        prompt_loader.render("nonexistent_prompt_v99")


# ── GeminiProvider._parse ─────────────────────────────────────────────────────


@pytest.fixture
def provider():
    """GeminiProvider with a dummy API key — no real network calls."""
    with patch("app.infrastructure.ai.gemini_provider.genai.Client"):
        from app.infrastructure.ai.gemini_provider import GeminiProvider

        return GeminiProvider(api_key="fake-key", model_name="gemini-1.5-flash")


@pytest.mark.unit
def test_parse_job_extraction_valid(provider):
    payload = {
        "company": "TechCorp",
        "recruiter_name": "Bob",
        "recruiter_email": "bob@techcorp.com",
        "job_title": "Senior Engineer",
        "skills": ["Python", "Docker"],
        "experience_required": "4+ years",
        "responsibilities": ["Build APIs", "Code review"],
        "location": "Remote",
        "employment_type": "Full-time",
        "seniority": "Senior",
        "job_summary": "Build backend systems",
    }
    result = provider._parse(JobExtractionResult, json.dumps(payload))
    assert result.company == "TechCorp"
    assert "Python" in result.skills


@pytest.mark.unit
def test_parse_job_extraction_partial_fields(provider):
    """All optional fields — parser should accept nulls gracefully."""
    payload = {"skills": [], "responsibilities": []}
    result = provider._parse(JobExtractionResult, json.dumps(payload))
    assert result.company is None
    assert result.skills == []


@pytest.mark.unit
def test_parse_invalid_json_raises(provider):
    with pytest.raises(AIResponseParseError, match="Invalid JSON"):
        provider._parse(JobExtractionResult, "not json at all")


@pytest.mark.unit
def test_parse_schema_mismatch_raises(provider):
    # match_score is required and must be 0.0-1.0; passing a string breaks it
    payload = {"match_score": "high", "matching_skills": [], "missing_skills": []}
    with pytest.raises(AIResponseParseError, match="schema mismatch"):
        provider._parse(ResumeMatchResult, json.dumps(payload))


@pytest.mark.unit
def test_parse_resume_match_valid(provider):
    payload = {
        "match_score": 0.75,
        "matching_skills": ["Python", "FastAPI"],
        "missing_skills": ["Kubernetes"],
        "fit_summary": "Strong backend match",
    }
    result = provider._parse(ResumeMatchResult, json.dumps(payload))
    assert result.match_score == 0.75
    assert "Kubernetes" in result.missing_skills


@pytest.mark.unit
def test_parse_email_generation_valid(provider):
    payload = {
        "subject": "Application for Backend Engineer",
        "body": "Dear Alice,\n\nI am excited to apply...",
    }
    result = provider._parse(EmailGenerationResult, json.dumps(payload))
    assert result.subject.startswith("Application")
    assert "Alice" in result.body


# ── _call_with_retry (mocked network) ─────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.unit
async def test_call_with_retry_succeeds_first_attempt(provider):
    mock_response = MagicMock()
    mock_response.text = '{"company": "X"}'
    provider._client.aio.models.generate_content = AsyncMock(return_value=mock_response)

    result = await provider._call_with_retry("system", "user")
    assert result == '{"company": "X"}'
    assert provider._client.aio.models.generate_content.call_count == 1


@pytest.mark.asyncio
@pytest.mark.unit
async def test_call_with_retry_retries_on_exception(provider):
    mock_response = MagicMock()
    mock_response.text = '{"ok": true}'
    provider._client.aio.models.generate_content = AsyncMock(
        side_effect=[RuntimeError("network"), RuntimeError("timeout"), mock_response]
    )

    with patch("asyncio.sleep", new_callable=AsyncMock):
        result = await provider._call_with_retry("system", "user")
    assert result == '{"ok": true}'
    assert provider._client.aio.models.generate_content.call_count == 3


@pytest.mark.asyncio
@pytest.mark.unit
async def test_call_with_retry_raises_after_max_attempts(provider):
    from app.domain.exceptions import AIProviderError

    provider._client.aio.models.generate_content = AsyncMock(
        side_effect=RuntimeError("permanent failure")
    )
    with (
        patch("asyncio.sleep", new_callable=AsyncMock),
        pytest.raises(AIProviderError, match="failed after"),
    ):
        await provider._call_with_retry("system", "user")
