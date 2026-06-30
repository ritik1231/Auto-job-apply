"""Application preparation service — resume match + email generation."""

from __future__ import annotations

import uuid

import structlog

from app.application.dto.application_dto import ApplicationHistoryItem
from app.application.services.quota_service import QuotaService
from app.domain.entities.application import ApplicationEntity, ApplicationStatus
from app.domain.entities.job_post import JobPostEntity
from app.domain.exceptions import InvalidJobPostError, ResumeNotFoundError
from app.domain.interfaces.ai_provider import IAIProvider, UserProfileInfo
from app.domain.interfaces.repositories import (
    IApplicationRepository,
    IJobPostRepository,
    IResumeRepository,
)

logger = structlog.get_logger(__name__)


class ApplicationService:
    def __init__(
        self,
        application_repo: IApplicationRepository,
        job_repo: IJobPostRepository,
        resume_repo: IResumeRepository,
        ai_provider: IAIProvider,
        quota_service: QuotaService,
    ) -> None:
        self._app_repo = application_repo
        self._job_repo = job_repo
        self._resume_repo = resume_repo
        self._ai = ai_provider
        self._quota = quota_service

    async def prepare_application(
        self,
        user_id: uuid.UUID,
        job_post_id: uuid.UUID,
        candidate_name: str = "",
        profile: UserProfileInfo | None = None,
    ) -> ApplicationEntity:
        job = await self._job_repo.get_by_id(job_post_id)
        if job is None or job.user_id != user_id:
            raise InvalidJobPostError("Job post not found")

        resume = await self._resume_repo.get_active_for_user(user_id)
        if resume is None:
            raise ResumeNotFoundError("No active resume found — please upload one first")

        resume_text = resume.parsed_text or ""
        if not resume_text:
            logger.warning(
                "resume has no parsed text; AI match quality will be low", resume_id=str(resume.id)
            )

        await self._quota.enforce(user_id)

        match, usage1 = await self._ai.analyze_resume_match(job, resume_text)
        email_result, usage2 = await self._ai.generate_application_email(
            job, resume_text, match, candidate_name, profile
        )

        application = await self._app_repo.create(
            user_id=user_id,
            job_post_id=job_post_id,
            resume_id=resume.id,
            match_score=match.match_score,
            matching_skills=match.matching_skills,
            missing_skills=match.missing_skills,
            generated_subject=email_result.subject,
            generated_email=email_result.body,
            status=ApplicationStatus.DRAFT,
        )

        total_input = usage1.input_tokens + usage2.input_tokens
        total_output = usage1.output_tokens + usage2.output_tokens
        await self._quota.record_usage(user_id, total_input, total_output)

        logger.info(
            "application draft prepared",
            user_id=str(user_id),
            application_id=str(application.id),
            match_score=match.match_score,
            provider=usage1.provider,
            input_tokens=total_input,
            output_tokens=total_output,
        )
        return application

    async def get_application(
        self, user_id: uuid.UUID, application_id: uuid.UUID
    ) -> ApplicationEntity:
        app = await self._app_repo.get_by_id(application_id)
        if app is None or app.user_id != user_id:
            raise InvalidJobPostError("Application not found")
        return app

    async def list_applications(
        self, user_id: uuid.UUID, *, limit: int = 20, offset: int = 0
    ) -> list[ApplicationEntity]:
        return await self._app_repo.list_for_user(user_id, limit=limit, offset=offset)

    async def list_applications_with_job_info(
        self, user_id: uuid.UUID, *, limit: int = 20, offset: int = 0
    ) -> list[ApplicationHistoryItem]:
        all_apps = await self._app_repo.list_for_user(user_id, limit=limit, offset=offset)
        apps = [a for a in all_apps if a.status == ApplicationStatus.SENT]

        seen_ids: set[uuid.UUID] = set()
        job_ids: list[uuid.UUID] = []
        for app in apps:
            if app.job_post_id not in seen_ids:
                seen_ids.add(app.job_post_id)
                job_ids.append(app.job_post_id)
        jobs: dict[uuid.UUID, JobPostEntity] = {}
        for jid in job_ids:
            job = await self._job_repo.get_by_id(jid)
            if job:
                jobs[jid] = job

        return [
            ApplicationHistoryItem(
                id=app.id,
                job_title=jobs[app.job_post_id].job_title if app.job_post_id in jobs else None,
                company=jobs[app.job_post_id].company if app.job_post_id in jobs else None,
                status=app.status,
                match_score=app.match_score,
                sent_at=app.sent_at,
                created_at=app.created_at,
            )
            for app in apps
        ]
