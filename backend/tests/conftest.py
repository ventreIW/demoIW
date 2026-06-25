from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.infrastructure.database import Base, get_session
from app.main import app

# SQLite in-memory URL for CI/testing (working DB)
TEST_DATABASE_URL = "sqlite+aiosqlite://"

# Bad URL that will fail on connect — used for DB-unavailable tests
BAD_DATABASE_URL = "sqlite+aiosqlite:///nonexistent/path/to/db.sqlite"


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Create an async test client with SQLite in-memory database.

    Tables are created before the client is yielded so integration tests
    can query domain tables. Seed data is NOT inserted — each test seeds
    what it needs.
    """
    # Import models so they register with Base.metadata before create_all
    from app.adapters.persistence import models as _  # noqa: F401

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

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

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


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """SQLite in-memory session with all ORM tables created. For unit-level mapper tests."""
    # Import models so they register with Base.metadata before create_all
    import app.adapters.persistence.models  # noqa: F401

    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_maker() as session:
        yield session
    await engine.dispose()
