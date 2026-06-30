"""Add github_url and website_url to users table.

Revision ID: 0007
Revises: 0006
Create Date: 2026-06-30
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("github_url", sa.String(500), nullable=True))
    op.add_column("users", sa.Column("website_url", sa.String(500), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "website_url")
    op.drop_column("users", "github_url")
