"""Add daily_quota_override to users table.

Revision ID: 0005
Revises: 0004
Create Date: 2026-06-29
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("daily_quota_override", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "daily_quota_override")
