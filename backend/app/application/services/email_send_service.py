"""Orchestrates sending a prepared application email via Gmail."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import structlog

from app.application.dto.application_dto import ApplicationSendResponse
from app.domain.entities.application import ApplicationStatus
from app.domain.exceptions import (
    ApplicationAlreadySentError,
    GmailSendError,
    InvalidJobPostError,
    OAuthError,
    StorageError,
)
from app.domain.interfaces.repositories import (
    IApplicationRepository,
    IJobPostRepository,
    IResumeRepository,
    IUserRepository,
)
from app.domain.interfaces.storage import IResumeStorage
from app.infrastructure.email.gmail_client import GmailEmailSender

logger = structlog.get_logger(__name__)


class EmailSendService:
    def __init__(
        self,
        app_repo: IApplicationRepository,
        job_repo: IJobPostRepository,
        resume_repo: IResumeRepository,
        user_repo: IUserRepository,
        storage: IResumeStorage,
    ) -> None:
        self._app_repo = app_repo
        self._job_repo = job_repo
        self._resume_repo = resume_repo
        self._user_repo = user_repo
        self._storage = storage

    async def send_application(
        self,
        user_id: uuid.UUID,
        application_id: uuid.UUID,
        to_address_override: str | None = None,
        subject_override: str | None = None,
        body_override: str | None = None,
    ) -> ApplicationSendResponse:
        """Send a DRAFT application via Gmail and mark it SENT."""
        # 1 — verify ownership and state
        app = await self._app_repo.get_by_id(application_id)
        if app is None or app.user_id != user_id:
            raise InvalidJobPostError("Application not found")

        if app.status == ApplicationStatus.SENT:
            raise ApplicationAlreadySentError("Application has already been sent")

        if not app.generated_subject or not app.generated_email:
            raise InvalidJobPostError("Application has no generated content — call /prepare first")

        # 2 — resolve recipient address
        job = await self._job_repo.get_by_id(app.job_post_id)
        if job is None:
            raise InvalidJobPostError("Associated job post not found")

        to_address = to_address_override or job.recruiter_email
        if not to_address:
            raise InvalidJobPostError(
                "Recruiter email is unknown — provide to_address in the request body"
            )

        # 3 — load resume PDF for attachment (best-effort)
        resume = await self._resume_repo.get_by_id(app.resume_id)
        pdf_bytes: bytes | None = None
        attachment_filename: str | None = None
        if resume and resume.file_path:
            try:
                pdf_bytes = await self._storage.get(resume.file_path)
                attachment_filename = resume.file_name
            except StorageError:
                logger.warning(
                    "resume PDF unreadable; sending without attachment",
                    resume_id=str(resume.id),
                )

        # 4 — retrieve encrypted Gmail credentials
        token_data = await self._user_repo.get_gmail_tokens(user_id)
        if token_data is None or (
            not token_data.access_token_enc and not token_data.refresh_token_enc
        ):
            raise OAuthError("Gmail access not granted — please sign in again to authorise sending")

        # 5 — send via Gmail
        sender = GmailEmailSender(
            access_token_enc=token_data.access_token_enc,
            refresh_token_enc=token_data.refresh_token_enc,
            expiry=token_data.expiry,
        )
        try:
            gmail_message_id = await sender.send(
                to_address=to_address,
                subject=subject_override or app.generated_subject,
                body=body_override or app.generated_email,
                attachment_content=pdf_bytes,
                attachment_filename=attachment_filename,
            )
        except (GmailSendError, OAuthError):
            await self._app_repo.update(
                application_id,
                status=ApplicationStatus.FAILED,
                error_message="Email delivery failed via Gmail API",
            )
            raise

        # 6 — persist SENT status
        now = datetime.now(tz=UTC)
        await self._app_repo.update(
            application_id,
            status=ApplicationStatus.SENT,
            sent_at=now,
            gmail_message_id=gmail_message_id,
        )

        # 7 — persist refreshed tokens if Google issued new ones
        if sender.tokens_refreshed and sender.new_access_token_enc and sender.new_expiry:
            await self._user_repo.update_gmail_tokens(
                user_id, sender.new_access_token_enc, sender.new_expiry
            )
            logger.info("refreshed gmail tokens persisted", user_id=str(user_id))

        logger.info(
            "application sent",
            user_id=str(user_id),
            application_id=str(application_id),
            gmail_message_id=gmail_message_id,
        )
        return ApplicationSendResponse(
            application_id=application_id,
            sent_at=now,
            gmail_message_id=gmail_message_id,
        )
