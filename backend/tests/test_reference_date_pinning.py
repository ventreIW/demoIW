"""BUG-04: a pinned reference_date must persist, and must actually anchor ageing."""

import pytest
import respx
from httpx import AsyncClient

from tests.test_prioritized_endpoint import _mock_openrouter


def _params(**overrides: object) -> dict[str, object]:
    body: dict[str, object] = {
        "seed": 42,
        "sector": "retail",
        "client_count": 60,
        "invoice_volume": 5.0,
        "amount_mean": 10000.0,
        "amount_std": 3000.0,
    }
    body.update(overrides)
    return body


async def _ageing(client: AsyncClient, **overrides: object) -> list[int]:
    """Generate a scenario and return its per-case ageing, sorted for comparability."""
    resp = await client.post("/api/v1/scenarios/generate", json=_params(**overrides))
    assert resp.status_code == 201, f"generate failed: {resp.status_code} {resp.text[:300]}"
    sid = resp.json()["id"]
    pri = await client.get(f"/api/v1/scenarios/{sid}/prioritized")
    assert pri.status_code == 200, pri.text[:300]
    return sorted(case["days_overdue"] for case in pri.json()["cases"])


@pytest.mark.anyio
@respx.mock
async def test_pinned_reference_date_persists_as_iso_string(client: AsyncClient) -> None:
    _mock_openrouter()

    resp = await client.post(
        "/api/v1/scenarios/generate", json=_params(reference_date="2026-06-01")
    )
    assert resp.status_code == 201, (
        f"pinning reference_date crashed persist: {resp.status_code} {resp.text[:300]}"
    )
    sid = resp.json()["id"]

    detail = await client.get(f"/api/v1/scenarios/{sid}")
    assert detail.status_code == 200
    stored = detail.json()["parameters"]
    assert stored["reference_date"] == "2026-06-01", (
        f"reference_date did not round-trip as an ISO string: {stored!r}"
    )
    # every other parameter must survive the mode change unharmed
    assert stored["seed"] == 42
    assert stored["sector"] == "retail"
    assert stored["client_count"] == 60


@pytest.mark.anyio
@respx.mock
async def test_omitted_reference_date_still_works(client: AsyncClient) -> None:
    _mock_openrouter()

    resp = await client.post("/api/v1/scenarios/generate", json=_params())
    assert resp.status_code == 201, resp.text[:300]
    sid = resp.json()["id"]

    detail = await client.get(f"/api/v1/scenarios/{sid}")
    assert detail.json()["parameters"]["reference_date"] is None


def test_pinned_reference_date_anchors_the_calendar() -> None:
    """A parameter that persists but changes nothing would pass the tests above and still be
    useless. This asserts what the pin is actually for.

    The generator draws `days_overdue` from the RNG first and derives `due_date` backwards
    from the anchor (`procedural_generator.py:119-120`). So the pin deliberately moves the
    *calendar* while holding the ageing distribution invariant — which is precisely what
    makes a dataset reproducible across days. Asserting "different pin, different ageing"
    would be asserting against the design.
    """
    from datetime import date

    from app.adapters.dataset.procedural_generator import ProceduralGenerator
    from app.domain.value_objects.generation_params import GenerationParams

    def build(reference: date) -> tuple[list[str], list[int]]:
        params = GenerationParams(
            seed=42,
            sector="retail",
            client_count=60,
            invoice_volume=5.0,
            amount_mean=10000.0,
            amount_std=3000.0,
            reference_date=reference,
        )
        dataset = ProceduralGenerator(params).generate()
        invoices = dataset.invoices.sort_values("id")
        return (
            [str(d) for d in invoices["due_date"]],
            [int(n) for n in invoices["days_overdue"]],
        )

    june_dates, june_ageing = build(date(2026, 6, 1))
    june_dates_again, june_ageing_again = build(date(2026, 6, 1))
    march_dates, march_ageing = build(date(2026, 3, 1))

    assert june_dates, "no invoices generated — the comparison would be vacuous"

    # Same seed, same pin: byte-identical. This is the reproducibility guarantee.
    assert june_dates == june_dates_again
    assert june_ageing == june_ageing_again

    # A different anchor shifts the calendar...
    assert june_dates != march_dates, (
        "a three-month difference in the anchor produced identical due dates — "
        "reference_date is persisted but not honoured"
    )
    # ...by exactly the offset between the two anchors, for every invoice.
    offset = (date(2026, 6, 1) - date(2026, 3, 1)).days
    assert all(
        (date.fromisoformat(j) - date.fromisoformat(m)).days == offset
        for j, m in zip(june_dates, march_dates, strict=True)
    )

    # ...while the ageing distribution is invariant, which is the point of drawing it first.
    assert june_ageing == march_ageing
