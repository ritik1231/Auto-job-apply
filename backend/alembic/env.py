"""Alembic migration environment — async SQLAlchemy variant."""

import asyncio
from logging.config import fileConfig

from sqlalchemy.ext.asyncio import create_async_engine

from alembic import context
from app.core.config import settings

# Register all models with Base.metadata before alembic inspects it.
from app.infrastructure.database.base import Base
from app.infrastructure.database.models import Application, JobPost, Resume, User  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Emit SQL to stdout without a live DB connection."""
    context.configure(
        url=settings.DATABASE_URL or config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def _do_migrations(connection: object) -> None:
    context.configure(
        connection=connection,  # type: ignore[arg-type]
        target_metadata=target_metadata,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Run migrations against a live database over an async connection."""
    db_url = settings.DATABASE_URL
    if not db_url:
        raise RuntimeError(
            "DATABASE_URL is not set. " "Configure it in your .env file before running migrations."
        )
    from app.infrastructure.database.session import _build_engine_args

    clean_url, connect_args = _build_engine_args(db_url)
    engine = create_async_engine(clean_url, echo=False, connect_args=connect_args)
    async with engine.connect() as conn:
        await conn.run_sync(_do_migrations)
    await engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
