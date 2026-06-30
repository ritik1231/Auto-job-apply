"""Add user_daily_usage table for per-user per-day token tracking.

Revision ID: 0006
Revises: 0005
Create Date: 2026-06-30
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "user_daily_usage",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("date", sa.Date, nullable=False),
        sa.Column("input_tokens", sa.Integer, nullable=False, server_default="0"),
        sa.Column("output_tokens", sa.Integer, nullable=False, server_default="0"),
        sa.Column("request_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_unique_constraint(
        "uq_user_daily_usage_user_date", "user_daily_usage", ["user_id", "date"]
    )
    op.create_index("idx_user_daily_usage_user_date", "user_daily_usage", ["user_id", "date"])


def downgrade() -> None:
    op.drop_index("idx_user_daily_usage_user_date", table_name="user_daily_usage")
    op.drop_constraint("uq_user_daily_usage_user_date", "user_daily_usage", type_="unique")
    op.drop_table("user_daily_usage")
