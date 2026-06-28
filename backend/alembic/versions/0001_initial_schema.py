"""Initial schema — users, resumes, job_posts, applications.

Revision ID: 0001
Revises:
Create Date: 2026-06-27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── users ────────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("google_id", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("name", sa.String(255), nullable=True),
        sa.Column("picture_url", sa.Text, nullable=True),
        sa.Column("gmail_access_token", sa.Text, nullable=True),
        sa.Column("gmail_refresh_token", sa.Text, nullable=True),
        sa.Column("gmail_token_expiry", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.UniqueConstraint("google_id", name="uq_users_google_id"),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )

    # ── resumes ──────────────────────────────────────────────────────────────
    op.create_table(
        "resumes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("file_name", sa.String(255), nullable=False),
        sa.Column("file_path", sa.String(500), nullable=False),
        sa.Column("file_size", sa.Integer, nullable=False),
        sa.Column("mime_type", sa.String(100), nullable=False),
        sa.Column("parsed_text", sa.Text, nullable=True),
        sa.Column(
            "parsed_metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
    )
    op.create_index("idx_resumes_user_id", "resumes", ["user_id"])
    op.create_index("idx_resumes_user_active", "resumes", ["user_id", "is_active"])

    # ── job_posts ────────────────────────────────────────────────────────────
    op.create_table(
        "job_posts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("raw_content", sa.Text, nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("company", sa.String(255), nullable=True),
        sa.Column("recruiter_name", sa.String(255), nullable=True),
        sa.Column("recruiter_email", sa.String(255), nullable=True),
        sa.Column("job_title", sa.String(255), nullable=True),
        sa.Column(
            "skills",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'"),
            nullable=False,
        ),
        sa.Column("experience_required", sa.String(100), nullable=True),
        sa.Column(
            "responsibilities",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'"),
            nullable=False,
        ),
        sa.Column("location", sa.String(255), nullable=True),
        sa.Column("employment_type", sa.String(100), nullable=True),
        sa.Column("seniority", sa.String(100), nullable=True),
        sa.Column("job_summary", sa.Text, nullable=True),
        sa.Column("source_url", sa.Text, nullable=True),
        sa.Column(
            "source_platform",
            sa.String(50),
            server_default=sa.text("'linkedin'"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.UniqueConstraint("user_id", "content_hash", name="uq_job_posts_user_hash"),
    )
    op.create_index("idx_job_posts_user_id", "job_posts", ["user_id"])

    # ── applications ─────────────────────────────────────────────────────────
    op.create_table(
        "applications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "job_post_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("job_posts.id"),
            nullable=False,
        ),
        sa.Column(
            "resume_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("resumes.id"),
            nullable=False,
        ),
        sa.Column("match_score", sa.Float, nullable=True),
        sa.Column(
            "missing_skills",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'"),
            nullable=False,
        ),
        sa.Column(
            "matching_skills",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'"),
            nullable=False,
        ),
        sa.Column("generated_subject", sa.String(500), nullable=True),
        sa.Column("generated_email", sa.Text, nullable=True),
        sa.Column(
            "status",
            sa.String(20),
            server_default=sa.text("'draft'"),
            nullable=False,
        ),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("gmail_message_id", sa.String(255), nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
    )
    op.create_index("idx_applications_user_id", "applications", ["user_id"])
    op.create_index("idx_applications_status", "applications", ["user_id", "status"])


def downgrade() -> None:
    # Drop in reverse FK dependency order.
    op.drop_index("idx_applications_status", table_name="applications")
    op.drop_index("idx_applications_user_id", table_name="applications")
    op.drop_table("applications")

    op.drop_index("idx_job_posts_user_id", table_name="job_posts")
    op.drop_table("job_posts")

    op.drop_index("idx_resumes_user_active", table_name="resumes")
    op.drop_index("idx_resumes_user_id", table_name="resumes")
    op.drop_table("resumes")

    op.drop_table("users")
