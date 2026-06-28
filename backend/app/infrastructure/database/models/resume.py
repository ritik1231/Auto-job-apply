import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.base import TimestampedBase


class Resume(TimestampedBase):
    __tablename__ = "resumes"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    parsed_text: Mapped[str | None] = mapped_column(Text)
    parsed_metadata: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )

    user: Mapped["User"] = relationship(back_populates="resumes", lazy="noload")  # type: ignore[name-defined]  # noqa: F821
    applications: Mapped[list["Application"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        back_populates="resume", lazy="noload"
    )

    def __repr__(self) -> str:
        return f"<Resume id={self.id} file_name={self.file_name!r}>"
