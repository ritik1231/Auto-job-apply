import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.base import TimestampedBase

# Valid values: draft | sent | failed
APPLICATION_STATUS_DRAFT = "draft"
APPLICATION_STATUS_SENT = "sent"
APPLICATION_STATUS_FAILED = "failed"


class Application(TimestampedBase):
    __tablename__ = "applications"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    job_post_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("job_posts.id"),
        nullable=False,
    )
    resume_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("resumes.id"),
        nullable=False,
    )

    match_score: Mapped[float | None] = mapped_column(Float)
    missing_skills: Mapped[list] = mapped_column(JSONB, nullable=False, server_default="[]")
    matching_skills: Mapped[list] = mapped_column(JSONB, nullable=False, server_default="[]")

    generated_subject: Mapped[str | None] = mapped_column(String(500))
    generated_email: Mapped[str | None] = mapped_column(Text)

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=APPLICATION_STATUS_DRAFT,
        server_default=APPLICATION_STATUS_DRAFT,
        index=True,
    )
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    gmail_message_id: Mapped[str | None] = mapped_column(String(255))
    error_message: Mapped[str | None] = mapped_column(Text)

    user: Mapped["User"] = relationship(back_populates="applications", lazy="noload")  # type: ignore[name-defined]  # noqa: F821
    job_post: Mapped["JobPost"] = relationship(back_populates="applications", lazy="noload")  # type: ignore[name-defined]  # noqa: F821
    resume: Mapped["Resume"] = relationship(back_populates="applications", lazy="noload")  # type: ignore[name-defined]  # noqa: F821

    def __repr__(self) -> str:
        return f"<Application id={self.id} status={self.status!r}>"
