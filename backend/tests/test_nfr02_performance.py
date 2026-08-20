"""E6 M4 — NFR-02 measured, not assumed.

    "The priority queue must load within 3 seconds for a scenario of up to 500 clients
     and 2,000 invoices."  — governance/prd.md, NFR-02

E6's M4 lists this as a mandatory line item and it was deferred at s6.2 ("AC3 (NFR-02 at 500
clients) unverified, no Postgres"). It does not actually need Postgres — it needs a scenario at
the stated size and a clock — so it is measured here.

The measurement is a test rather than a recorded number so it keeps being true. A performance
figure written into a retrospective is true on the day it was written; a test is true on every
run, and fails when it stops being.
"""

import time

import pytest
from httpx import AsyncClient

from app.container import get_llm_port
from app.main import app
from tests.test_e2e_demo_flow import _NoLLM

#: NFR-02, priority queue budget.
QUEUE_BUDGET_SECONDS = 3.0

#: The scenario size NFR-02 names. invoice_volume 4.0 over 500 clients targets ~2,000 invoices.
NFR_02_SCENARIO = {
    "seed": 42,
    "sector": "retail",
    "client_count": 500,
    "invoice_volume": 4.0,
    "amount_mean": 10000.0,
    "amount_std": 3000.0,
    "reference_date": "2026-06-01",
}


@pytest.fixture
def _stub_llm_nfr02():
    app.dependency_overrides[get_llm_port] = lambda: _NoLLM()
    yield
    app.dependency_overrides.pop(get_llm_port, None)


def test_nfr02_scenario_is_actually_at_the_stated_size() -> None:
    """Guard the measurement's premise.

    NFR-02 names 500 clients *and* 2,000 invoices. Asserting only the client count would let
    the invoice volume drift downward and quietly turn a 3s budget into an easier test.
    `invoice_volume` is a Poisson mean, so the count is not exact — the assertion is a band.
    """
    from datetime import date

    from app.adapters.dataset.procedural_generator import ProceduralGenerator
    from app.domain.value_objects.generation_params import GenerationParams

    params = GenerationParams(
        seed=NFR_02_SCENARIO["seed"],
        sector=NFR_02_SCENARIO["sector"],
        client_count=NFR_02_SCENARIO["client_count"],
        invoice_volume=NFR_02_SCENARIO["invoice_volume"],
        amount_mean=NFR_02_SCENARIO["amount_mean"],
        amount_std=NFR_02_SCENARIO["amount_std"],
        reference_date=date(2026, 6, 1),
    )
    dataset = ProceduralGenerator(params).generate()

    assert len(dataset.clients) == 500
    assert 1800 <= len(dataset.invoices) <= 2200, (
        f"the NFR-02 scenario produced {len(dataset.invoices)} invoices, outside the "
        "1800-2200 band around the 2,000 the requirement names — the timing tests would "
        "no longer be measuring NFR-02's scenario"
    )


@pytest.mark.anyio
async def test_priority_queue_meets_nfr02_at_500_clients(
    client: AsyncClient, _stub_llm_nfr02
) -> None:
    """The queue must load inside 3s at the size NFR-02 names."""
    generated = await client.post("/api/v1/scenarios/generate", json=NFR_02_SCENARIO)
    assert generated.status_code == 201, generated.text[:300]
    scenario_id = generated.json()["id"]
    assert generated.json()["client_count"] == 500, (
        f"expected 500 clients, got {generated.json()['client_count']} — "
        "the measurement would not be at the NFR-02 size"
    )

    await client.patch(f"/api/v1/scenarios/{scenario_id}/activate")
    scored = await client.post(f"/api/v1/scenarios/{scenario_id}/score")
    assert scored.status_code == 201, scored.text[:300]

    started = time.monotonic()
    queue = await client.get(f"/api/v1/scenarios/{scenario_id}/prioritized")
    elapsed = time.monotonic() - started

    assert queue.status_code == 200, queue.text[:300]
    cases = queue.json()["cases"]
    assert cases, "empty queue — the timing would be measuring nothing"

    assert elapsed < QUEUE_BUDGET_SECONDS, (
        f"priority queue took {elapsed:.2f}s at 500 clients, "
        f"over the NFR-02 budget of {QUEUE_BUDGET_SECONDS:.0f}s"
    )
    print(
        f"\n[E6 M4 · NFR-02] priority queue {elapsed:.3f}s at 500 clients "
        f"({len(cases)} cases) — budget {QUEUE_BUDGET_SECONDS:.0f}s"
    )


@pytest.mark.anyio
async def test_kpi_dashboard_responds_at_500_clients(
    client: AsyncClient, _stub_llm_nfr02
) -> None:
    """The executive dashboard reads persisted scores (ADR-009); it must stay responsive too.

    Not named by NFR-02, which speaks only of the priority queue, so it is held to the same
    budget as a reasonable proxy rather than to an invented one.
    """
    generated = await client.post("/api/v1/scenarios/generate", json=NFR_02_SCENARIO)
    scenario_id = generated.json()["id"]
    await client.patch(f"/api/v1/scenarios/{scenario_id}/activate")
    await client.post(f"/api/v1/scenarios/{scenario_id}/score")

    started = time.monotonic()
    kpis = await client.get(f"/api/v1/scenarios/{scenario_id}/kpis")
    elapsed = time.monotonic() - started

    assert kpis.status_code == 200, kpis.text[:300]
    assert kpis.json()["total_outstanding"] > 0
    assert elapsed < QUEUE_BUDGET_SECONDS, (
        f"KPI dashboard took {elapsed:.2f}s at 500 clients, over {QUEUE_BUDGET_SECONDS:.0f}s"
    )
    print(f"[E6 M4 · NFR-02] KPI dashboard {elapsed:.3f}s at 500 clients")
