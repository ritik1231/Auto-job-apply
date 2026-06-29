"""Add candidate profile fields to users table.

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-29
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("current_ctc", sa.String(100), nullable=True))
    op.add_column("users", sa.Column("expected_ctc", sa.String(100), nullable=True))
    op.add_column("users", sa.Column("notice_period", sa.String(100), nullable=True))
    op.add_column("users", sa.Column("current_location", sa.String(255), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "current_location")
    op.drop_column("users", "notice_period")
    op.drop_column("users", "expected_ctc")
    op.drop_column("users", "current_ctc")
