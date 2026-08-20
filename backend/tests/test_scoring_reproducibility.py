"""BUG-05: identical generation parameters must produce an identical portfolio.

`GenerationParams` documents itself as fully determining the output. This asserts it.
Client ids are random surrogate keys by design, so the comparison is over the *content*
of the portfolio — the multiset of scores and the category tally — not over identity.
"""

import pytest
import respx

from httpx import AsyncClient

from tests.test_prioritized_endpoint import _mock_openrouter

_PARAMS = {
    "seed": 42,
    "sector": "retail",
    "client_count": 100,
    "invoice_volume": 5.0,
    "amount_mean": 10000.0,
    "amount_std": 3000.0,
    "reference_date": "2026-06-01",  # pin the calendar too (BUG-04), so only identity varies
}


async def _portfolio(client: AsyncClient) -> tuple[list[float], dict[str, int]]:
    """Generate a scenario and return (sorted scores, category tally)."""
    resp = await client.post("/api/v1/scenarios/generate", json=_PARAMS)
    assert resp.status_code == 201, f"generate failed: {resp.status_code} {resp.text[:300]}"
    sid = resp.json()["id"]

    pri = await client.get(f"/api/v1/scenarios/{sid}/prioritized")
    assert pri.status_code == 200, pri.text[:300]
    cases = pri.json()["cases"]

    assert cases, "empty portfolio — the comparison would be vacuous"

    tally: dict[str, int] = {}
    for case in cases:
        tally[case["category"]] = tally.get(case["category"], 0) + 1
    return sorted(round(case["score"], 9) for case in cases), tally


@pytest.mark.anyio
@respx.mock
async def test_same_params_produce_the_same_portfolio(client: AsyncClient) -> None:
    _mock_openrouter()

    scores_a, tally_a = await _portfolio(client)
    scores_b, tally_b = await _portfolio(client)

    assert tally_a == tally_b, (
        f"same seed produced different category distributions: {tally_a} vs {tally_b}"
    )
    assert len(scores_a) == len(scores_b), (
        f"same seed produced portfolios of different sizes: "
        f"{len(scores_a)} vs {len(scores_b)}"
    )
    assert scores_a == scores_b, "same seed produced different scores"
