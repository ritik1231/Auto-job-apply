"""Integration tests for BaseRepository — requires a live PostgreSQL database.

Run with:
    DATABASE_URL=postgresql+asyncpg://... pytest -m integration
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.infrastructure.database.base import Base

# Registers all models with Base.metadata
from app.infrastructure.database.models import User
from app.infrastructure.database.repositories.base import BaseRepository


@pytest.fixture(scope="module")
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(scope="module")
async def test_engine():
    if not settings.DATABASE_URL:
        pytest.skip("DATABASE_URL not configured — skipping integration tests")
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def db_session(test_engine):
    factory = async_sessionmaker(test_engine, expire_on_commit=False, autoflush=False)
    async with factory() as session:
        yield session
        await session.rollback()


@pytest.mark.integration
async def test_create_returns_persisted_instance(db_session: AsyncSession) -> None:
    repo: BaseRepository[User] = BaseRepository(db_session, User)
    user = await repo.create(
        google_id="g-test-001",
        email="create@example.com",
        name="Create Test",
    )
    assert user.id is not None
    assert user.email == "create@example.com"


@pytest.mark.integration
async def test_get_by_id_returns_correct_row(db_session: AsyncSession) -> None:
    repo: BaseRepository[User] = BaseRepository(db_session, User)
    created = await repo.create(
        google_id="g-test-002",
        email="getbyid@example.com",
        name="GetById Test",
    )
    fetched = await repo.get_by_id(created.id)
    assert fetched is not None
    assert fetched.id == created.id
    assert fetched.email == "getbyid@example.com"


@pytest.mark.integration
async def test_get_by_id_returns_none_for_missing(db_session: AsyncSession) -> None:
    import uuid

    repo: BaseRepository[User] = BaseRepository(db_session, User)
    result = await repo.get_by_id(uuid.uuid4())
    assert result is None


@pytest.mark.integration
async def test_update_modifies_fields(db_session: AsyncSession) -> None:
    repo: BaseRepository[User] = BaseRepository(db_session, User)
    created = await repo.create(
        google_id="g-test-003",
        email="update@example.com",
        name="Before Update",
    )
    updated = await repo.update(created.id, name="After Update")
    assert updated is not None
    assert updated.name == "After Update"


@pytest.mark.integration
async def test_delete_removes_row(db_session: AsyncSession) -> None:
    repo: BaseRepository[User] = BaseRepository(db_session, User)
    created = await repo.create(
        google_id="g-test-004",
        email="delete@example.com",
        name="To Delete",
    )
    deleted = await repo.delete(created.id)
    assert deleted is True
    assert await repo.get_by_id(created.id) is None
