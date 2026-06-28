"""Root conftest — shared fixtures and pytest plugins go here."""

import pytest


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"
