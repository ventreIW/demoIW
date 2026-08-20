import os
import pathlib
import subprocess
import sys
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


async def _test_client_with_session_maker() -> (
    AsyncGenerator[tuple[AsyncClient, async_sessionmaker[AsyncSession]], None]
):
    """Shared setup behind the ``client`` and ``client_with_db`` fixtures."""
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
        yield ac, test_session_maker

    await test_engine.dispose()
    app.dependency_overrides.clear()


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Create an async test client with SQLite in-memory database.

    Tables are created before the client is yielded so integration tests
    can query domain tables. Seed data is NOT inserted — each test seeds
    what it needs.
    """
    async for ac, _session_maker in _test_client_with_session_maker():
        yield ac


@pytest.fixture
async def client_with_db() -> (
    AsyncGenerator[tuple[AsyncClient, async_sessionmaker[AsyncSession]], None]
):
    """Test client **plus** a session maker onto the same in-memory database.

    Exists so integration tests can seed domain rows with direct SQLAlchemy
    inserts instead of driving the generate endpoint, which needs an OpenRouter
    key and spends free-tier quota (PAT-R-10). ``test_case_detail_endpoint.py``
    says in its own docstring that it could only assert 404s for want of this.
    """
    async for pair in _test_client_with_session_maker():
        yield pair


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


# ---------------------------------------------------------------------------
# s7.4 / E6 M4 — real PostgreSQL
#
# Every fixture above builds the schema with `Base.metadata.create_all` against SQLite, which
# means the Alembic migrations are executed by no test in this project. That is the concrete
# gap M4 exists to close, and it now matters more than before: migration 0004 (BUG-05) is new
# and its `ROW_NUMBER() OVER (PARTITION BY …)` backfill has never run anywhere.
#
# This fixture runs the migrations from zero against a real PostgreSQL, so asyncpg and the
# Postgres-specific DDL are exercised rather than assumed.
#
# It SKIPS LOUDLY when PostgreSQL is unreachable. It must never pass silently: M4 accumulated
# five stories of deferral precisely because "not verified" was indistinguishable from "fine".
# ---------------------------------------------------------------------------

#: Set to run the M4 suite, e.g.
#: postgresql+asyncpg://postgres:postgres@localhost:5432/demoiw_test
POSTGRES_URL_ENV = "DEMOIW_TEST_POSTGRES_URL"

M4_SKIP_REASON = (
    "E6 M4 NOT VERIFIED: no PostgreSQL reachable. "
    f"Set {POSTGRES_URL_ENV} to a live database to run the real-driver E2E "
    "(asyncpg + Alembic migrations from zero, including 0004). "
    "This suite has now been deferred across E4, E5, s6.2, s6.3, s6.4 and E7 — "
    "a skip here is an OPEN GATE, not a pass."
)


def _postgres_url() -> str:
    """Return the configured Postgres URL, or skip with an explicit M4 reason."""
    url = os.environ.get(POSTGRES_URL_ENV, "").strip()
    if not url:
        pytest.skip(M4_SKIP_REASON)
    return url


def _run_alembic(url: str, command: str) -> None:
    """Run an Alembic command against `url` in a subprocess.

    A subprocess rather than the Python API because `alembic/env.py` reads
    `settings.DATABASE_URL` at import time; overriding the env var for a child process is
    both simpler and closer to how migrations actually run in deployment.
    """
    env = {**os.environ, "DATABASE_URL": url}
    result = subprocess.run(
        [sys.executable, "-m", "alembic", *command.split()],
        cwd=pathlib.Path(__file__).resolve().parent.parent,
        env=env,
        capture_output=True,
        text=True,
        timeout=180,
    )
    if result.returncode != 0:
        raise AssertionError(
            f"alembic {command} failed against PostgreSQL:\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )


@pytest.fixture
async def postgres_client() -> AsyncGenerator[AsyncClient, None]:
    """An AsyncClient backed by real PostgreSQL with migrations applied from zero."""
    url = _postgres_url()

    from app.adapters.persistence import models as _  # noqa: F401

    try:
        engine = create_async_engine(url, echo=False)
        async with engine.begin() as conn:
            await conn.exec_driver_sql("SELECT 1")
    except Exception as exc:  # noqa: BLE001 — any connection failure is the same outcome
        pytest.skip(f"{M4_SKIP_REASON}\nConnection attempt failed: {exc}")

    # Migrations from zero — the whole point of this fixture.
    #
    # Reset by dropping the schema rather than by walking migrations down. `downgrade base`
    # over a populated database is not a reset: 0006 relaxes a NOT NULL that real rows now
    # violate, so its downgrade correctly refuses rather than destroying audit data. A test
    # reset wants an empty database; downgrade safety is a separate question, tested on its
    # own below.
    async with engine.begin() as conn:
        await conn.exec_driver_sql("DROP SCHEMA public CASCADE")
        await conn.exec_driver_sql("CREATE SCHEMA public")
    _run_alembic(url, "upgrade head")

    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_session() -> AsyncGenerator[AsyncSession, None]:
        async with session_maker() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    await engine.dispose()
    app.dependency_overrides.clear()
