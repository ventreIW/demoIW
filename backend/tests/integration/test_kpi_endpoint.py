"""Integration tests for the executive KPI endpoint (s6.1 T3).

Seeded with **direct SQLAlchemy inserts**, not by driving ``POST /generate`` —
that path needs an OpenRouter key and spends free-tier quota on every run, which
is why ``test_case_detail_endpoint.py`` could only ever assert 404s (PAT-R-10,
filed at E5 close). The composition path is genuinely exercised here.

The portfolio is the worked example from ``s6.1-story.md`` §Examples, so the
figures below are the ones computed by hand there.
"""

import uuid
from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.adapters.persistence.models import (
    ClientORM,
    InvoiceORM,
    PaymentORM,
    ScenarioORM,
    ScoreORM,
)

_SCORED_AT = datetime(2026, 8, 4, 18, 22, 41, tzinfo=UTC)


async def _seed_portfolio(
    session_maker: async_sessionmaker[AsyncSession],
    *,
    with_scores: bool = True,
) -> str:
    """A — 10,000 open with 4,000 paid · B — 20,000 open · C — 5,000 settled."""
    scenario_id = str(uuid.uuid4())
    a, b, c = (str(uuid.uuid4()) for _ in range(3))
    i1, i2, i3 = (str(uuid.uuid4()) for _ in range(3))

    async with session_maker() as session:
        session.add(
            ScenarioORM(
                id=scenario_id,
                name="Retail Q3",
                sector="retail",
                seed=42,
                parameters={},
                source="generated",
                status="active",
                created_at=datetime(2026, 8, 1, tzinfo=UTC),
            )
        )
        for client_id, name in ((a, "Acme"), (b, "Borges"), (c, "Cielo")):
            session.add(
                ClientORM(
                    id=client_id,
                    scenario_id=scenario_id,
                    name=name,
                    sector_description=None,
                    payment_history_pattern="on_time",
                )
            )
        for invoice_id, client_id, amount, status, days in (
            (i1, a, 10_000.0, "overdue", 95),
            (i2, b, 20_000.0, "overdue", 20),
            (i3, c, 5_000.0, "paid", 0),
        ):
            session.add(
                InvoiceORM(
                    id=invoice_id,
                    client_id=client_id,
                    folio=f"F-{invoice_id[:4]}",
                    amount=amount,
                    issue_date=datetime(2026, 4, 1, tzinfo=UTC),
                    due_date=datetime(2026, 5, 1, tzinfo=UTC),
                    days_overdue=days,
                    status=status,
                )
            )
        # A's 4,000 is a partial payment against an invoice that is still open;
        # C's 5,000 settles its invoice.
        session.add(
            PaymentORM(
                id=str(uuid.uuid4()),
                invoice_id=i1,
                amount=4_000.0,
                payment_date=datetime(2026, 6, 1, tzinfo=UTC),
                method="transfer",
            )
        )
        session.add(
            PaymentORM(
                id=str(uuid.uuid4()),
                invoice_id=i3,
                amount=5_000.0,
                payment_date=datetime(2026, 6, 10, tzinfo=UTC),
                method="transfer",
            )
        )
        if with_scores:
            for client_id, value, category in (
                (a, 80.0, "high"),
                (b, 40.0, "low"),
                (c, 90.0, "high"),
            ):
                session.add(
                    ScoreORM(
                        id=str(uuid.uuid4()),
                        client_id=client_id,
                        scenario_id=scenario_id,
                        score_value=value,
                        category=category,
                        explanation="—",
                        scored_at=_SCORED_AT,
                    )
                )
        await session.commit()

    return scenario_id


@pytest.mark.anyio
async def test_kpis_404_unknown_scenario(client: AsyncClient) -> None:
    response = await client.get(f"/api/v1/scenarios/{uuid.uuid4()}/kpis")

    assert response.status_code == 404


@pytest.mark.anyio
async def test_kpis_409_when_scenario_has_no_scores(
    client_with_db: tuple[AsyncClient, async_sessionmaker[AsyncSession]],
) -> None:
    """ADR-009 — an unscored book must not be answered with a book of zeros."""
    client, session_maker = client_with_db
    scenario_id = await _seed_portfolio(session_maker, with_scores=False)

    response = await client.get(f"/api/v1/scenarios/{scenario_id}/kpis")

    assert response.status_code == 409
    detail = response.json()["detail"]
    assert "/score" in detail, "the 409 must name the action that fixes it"
    assert scenario_id in detail


@pytest.mark.anyio
async def test_kpis_200_returns_the_hand_computed_figures(
    client_with_db: tuple[AsyncClient, async_sessionmaker[AsyncSession]],
) -> None:
    client, session_maker = client_with_db
    scenario_id = await _seed_portfolio(session_maker)

    response = await client.get(f"/api/v1/scenarios/{scenario_id}/kpis")

    assert response.status_code == 200
    body = response.json()
    assert body["scenario"]["name"] == "Retail Q3"
    assert body["scenario"]["sector"] == "retail"
    assert body["client_count"] == 3
    assert body["unscored_client_count"] == 0
    assert body["total_outstanding"] == pytest.approx(26_000.0)
    assert body["total_expected_recoverable"] == pytest.approx(12_800.0)
    assert body["collected_to_date"] == pytest.approx(5_000.0)
    assert body["recovery_rate_actual"] == pytest.approx(0.16129, rel=1e-4)
    assert body["recovery_rate_expected"] == pytest.approx(0.49231, rel=1e-4)
    assert body["cases_by_category"] == {"high": 2, "medium": 0, "low": 1}


@pytest.mark.anyio
async def test_kpis_200_segmentation_counts_sum_to_client_count(
    client_with_db: tuple[AsyncClient, async_sessionmaker[AsyncSession]],
) -> None:
    """Over the wire, not only in the domain — serialisation must not lose a bucket."""
    client, session_maker = client_with_db
    scenario_id = await _seed_portfolio(session_maker)

    body = (await client.get(f"/api/v1/scenarios/{scenario_id}/kpis")).json()

    segmentation = body["segmentation"]
    assert set(segmentation) == {"days_overdue_bucket", "amount_range", "score_category"}
    for dimension, buckets in segmentation.items():
        assert sum(b["client_count"] for b in buckets) == body["client_count"], dimension
        assert sum(b["outstanding"] for b in buckets) == pytest.approx(
            body["total_outstanding"]
        ), dimension


@pytest.mark.anyio
async def test_kpis_200_carries_scored_at_for_staleness(
    client_with_db: tuple[AsyncClient, async_sessionmaker[AsyncSession]],
) -> None:
    client, session_maker = client_with_db
    scenario_id = await _seed_portfolio(session_maker)

    body = (await client.get(f"/api/v1/scenarios/{scenario_id}/kpis")).json()

    assert body["scored_at"].startswith("2026-08-04T18:22:41")


@pytest.mark.anyio
async def test_kpis_path_is_published_in_the_openapi_schema(client: AsyncClient) -> None:
    schema = (await client.get("/api/v1/openapi.json")).json()

    assert "/api/v1/scenarios/{scenario_id}/kpis" in schema["paths"]
