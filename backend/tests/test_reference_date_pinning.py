"""BUG-04: a pinned reference_date must persist, and must actually anchor ageing."""

import httpx
import pytest
import respx
from httpx import AsyncClient

from tests.test_prioritized_endpoint import _mock_openrouter


def _params(**overrides: object) -> dict[str, object]:
    body: dict[str, object] = {
        "seed": 42,
        "sector": "retail",
        "client_count": 25,
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
    assert stored["client_count"] == 25


@pytest.mark.anyio
@respx.mock
async def test_omitted_reference_date_still_works(client: AsyncClient) -> None:
    _mock_openrouter()

    resp = await client.post("/api/v1/scenarios/generate", json=_params())
    assert resp.status_code == 201, resp.text[:300]
    sid = resp.json()["id"]

    detail = await client.get(f"/api/v1/scenarios/{sid}")
    assert detail.json()["parameters"]["reference_date"] is None


@pytest.mark.anyio
@respx.mock
async def test_pinned_reference_date_actually_anchors_ageing(client: AsyncClient) -> None:
    """A parameter that persists but changes nothing would pass the tests above and still
    be useless. Ageing must move with the pin, and must not move without it."""
    _mock_openrouter()

    june_a = await _ageing(client, reference_date="2026-06-01")
    june_b = await _ageing(client, reference_date="2026-06-01")
    march = await _ageing(client, reference_date="2026-03-01")

    assert june_a, "no cases produced — the comparison would be vacuous"
    assert june_a == june_b, "same seed and same pin produced different ageing"
    assert june_a != march, (
        "a three-month difference in the anchor produced identical ageing — "
        "reference_date is persisted but not honoured"
    )
