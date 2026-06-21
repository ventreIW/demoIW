from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.infrastructure.database import get_session
from app.main import app

# SQLite in-memory URL for CI/testing (working DB)
TEST_DATABASE_URL = "sqlite+aiosqlite://"

# Bad URL that will fail on connect — used for DB-unavailable tests
BAD_DATABASE_URL = "sqlite+aiosqlite:///nonexistent/path/to/db.sqlite"


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Create an async test client with SQLite in-memory database."""
    test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    test_session_maker = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async def override_get_session() -> AsyncGenerator[AsyncSession, None]:
        async with test_session_maker() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    await test_engine.dispose()
    app.dependency_overrides.clear()


@pytest.fixture
async def client_unavailable() -> AsyncGenerator[AsyncClient, None]:
    """Create a test client with a DB that will fail on execute."""
    bad_engine = create_async_engine(BAD_DATABASE_URL, echo=False)
    bad_session_maker = async_sessionmaker(
        bad_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async def override_get_session() -> AsyncGenerator[AsyncSession, None]:
        async with bad_session_maker() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    await bad_engine.dispose()
    app.dependency_overrides.clear()
