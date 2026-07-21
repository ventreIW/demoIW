"""Integration tests for E3's acceptance gate.

These cover two commitments in `work/epics/e3-synthetic-dataset-generator/scope.md`
that no existing test verified:

1. "POST /api/scenarios/generate with seed=42 called twice returns the same
   client_count and total outstanding"
2. "Generated scenario appears in /scenarios and can be activated"

`tests/adapters/test_procedural_generator.py::test_determinism` proves the
*generator* is deterministic, but not the endpoint path — which additionally
involves LLM enrichment and persistence. Determinism could be lost in either
without that test failing.
"""

from collections.abc import AsyncGenerator

import httpx
import pytest
import respx
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.infrastructure.database import Base, get_session
from app.main import app

_PAYLOAD = {
    "seed": 42,
    "sector": "retail",
    "client_count": 5,
    "invoice_volume": 4.0,
    "amount_mean": 1000.0,
    "amount_std": 200.0,
}


def _mock_llm(client_count: int) -> None:
    """Mock OpenRouter with a deterministic, correctly-sized enrichment response."""
    enriched = [
        {"name": f"Enriched Client {i}", "sector_description": "A retail company in Mexico."}
        for i in range(client_count)
    ]
    respx.post("https://openrouter.ai/api/v1/chat/completions").mock(
        return_value=httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": str(enriched).replace("'", '"')}}],
                "usage": {"prompt_tokens": 100, "completion_tokens": 50},
            },
        )
    )


@pytest.fixture
async def client_with_db() -> (
    AsyncGenerator[tuple[AsyncClient, async_sessionmaker[AsyncSession]], None]
):
    """Like the shared `client` fixture, but also yields the session maker.

    The shared fixture keeps its engine private, so a test cannot inspect
    persisted rows. Total outstanding is not exposed by any endpoint, so
    verifying it requires reading the database directly.
    """
    from app.adapters.persistence import models as _  # noqa: F401

    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_session() -> AsyncGenerator[AsyncSession, None]:
        async with session_maker() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac, session_maker

    await engine.dispose()
    app.dependency_overrides.clear()


async def _total_outstanding(
    session_maker: async_sessionmaker[AsyncSession], scenario_id: str
) -> tuple[int, float]:
    """Return (invoice count, summed invoice amount) for a scenario."""
    from app.adapters.persistence.models import ClientORM, InvoiceORM

    async with session_maker() as session:
        result = await session.execute(
            select(InvoiceORM.amount)
            .join(ClientORM, InvoiceORM.client_id == ClientORM.id)
            .where(ClientORM.scenario_id == scenario_id)
        )
        amounts = [row[0] for row in result.all()]

    return len(amounts), round(sum(amounts), 6)


@pytest.mark.anyio
@respx.mock
async def test_same_seed_produces_identical_client_count_and_total_outstanding(
    client_with_db: tuple[AsyncClient, async_sessionmaker[AsyncSession]],
) -> None:
    """E3 acceptance gate: seed=42 twice → same client_count and total outstanding."""
    client, session_maker = client_with_db
    _mock_llm(_PAYLOAD["client_count"])  # type: ignore[arg-type]

    first = await client.post("/api/v1/scenarios/generate", json=_PAYLOAD)
    second = await client.post("/api/v1/scenarios/generate", json=_PAYLOAD)

    assert first.status_code == 201
    assert second.status_code == 201

    first_body, second_body = first.json(), second.json()

    # Distinct scenarios — determinism is about content, not identity.
    assert first_body["id"] != second_body["id"]

    assert first_body["client_count"] == second_body["client_count"] == _PAYLOAD["client_count"]

    first_invoices, first_total = await _total_outstanding(session_maker, first_body["id"])
    second_invoices, second_total = await _total_outstanding(session_maker, second_body["id"])

    assert first_invoices > 0, "no invoices persisted — nothing to compare"
    assert first_invoices == second_invoices
    assert first_total == second_total


@pytest.mark.anyio
@respx.mock
async def test_different_seed_produces_different_total_outstanding(
    client_with_db: tuple[AsyncClient, async_sessionmaker[AsyncSession]],
) -> None:
    """Guards the test above: equal totals must reflect the seed, not a constant."""
    client, session_maker = client_with_db
    _mock_llm(_PAYLOAD["client_count"])  # type: ignore[arg-type]

    first = await client.post("/api/v1/scenarios/generate", json=_PAYLOAD)
    second = await client.post("/api/v1/scenarios/generate", json={**_PAYLOAD, "seed": 1337})

    _, first_total = await _total_outstanding(session_maker, first.json()["id"])
    _, second_total = await _total_outstanding(session_maker, second.json()["id"])

    assert first_total != second_total


@pytest.mark.anyio
@respx.mock
async def test_generated_scenario_is_listed_and_can_be_activated(
    client_with_db: tuple[AsyncClient, async_sessionmaker[AsyncSession]],
) -> None:
    """E3 acceptance gate: generated scenario appears in /scenarios and can be activated."""
    client, _ = client_with_db
    _mock_llm(_PAYLOAD["client_count"])  # type: ignore[arg-type]

    first = await client.post("/api/v1/scenarios/generate", json=_PAYLOAD)
    second = await client.post("/api/v1/scenarios/generate", json=_PAYLOAD)
    first_id, second_id = first.json()["id"], second.json()["id"]

    # Both appear in the list backing the /scenarios page.
    listing = await client.get("/api/v1/scenarios")
    assert listing.status_code == 200
    listed_ids = [s["id"] for s in listing.json()]
    assert first_id in listed_ids
    assert second_id in listed_ids

    # Generating activates the newest scenario, so the first is now inactive.
    active = await client.get("/api/v1/scenarios/active")
    assert active.json()["id"] == second_id

    # Activating the older one switches it back — the operation the UI performs.
    activated = await client.patch(f"/api/v1/scenarios/{first_id}/activate")
    assert activated.status_code == 200
    assert activated.json()["id"] == first_id
    assert activated.json()["status"] == "active"

    active_after = await client.get("/api/v1/scenarios/active")
    assert active_after.json()["id"] == first_id
