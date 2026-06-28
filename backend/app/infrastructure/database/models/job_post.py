import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.base import Base


class JobPost(Base):
    """Job posts are immutable once extracted — no updated_at column."""

    __tablename__ = "job_posts"
    __table_args__ = (UniqueConstraint("user_id", "content_hash", name="uq_job_posts_user_hash"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    raw_content: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    company: Mapped[str | None] = mapped_column(String(255))
    recruiter_name: Mapped[str | None] = mapped_column(String(255))
    recruiter_email: Mapped[str | None] = mapped_column(String(255))
    job_title: Mapped[str | None] = mapped_column(String(255))
    skills: Mapped[list] = mapped_column(JSONB, nullable=False, server_default="[]")
    experience_required: Mapped[str | None] = mapped_column(String(100))
    responsibilities: Mapped[list] = mapped_column(JSONB, nullable=False, server_default="[]")
    location: Mapped[str | None] = mapped_column(String(255))
    employment_type: Mapped[str | None] = mapped_column(String(100))
    seniority: Mapped[str | None] = mapped_column(String(100))
    job_summary: Mapped[str | None] = mapped_column(Text)
    source_url: Mapped[str | None] = mapped_column(Text)
    source_platform: Mapped[str] = mapped_column(
        String(50), nullable=False, server_default="linkedin"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="job_posts", lazy="noload")  # type: ignore[name-defined]  # noqa: F821
    applications: Mapped[list["Application"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        back_populates="job_post", lazy="noload"
    )

    def __repr__(self) -> str:
        return f"<JobPost id={self.id} company={self.company!r} title={self.job_title!r}>"
