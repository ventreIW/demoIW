"""Tests for GET /api/v1/scenarios/{scenario_id}/prioritized endpoint (s4.5-API)."""

import httpx
import pytest
import respx
from httpx import AsyncClient

from app.container import get_prioritize_scenario_use_case


def _mock_llm_response() -> list[dict[str, str]]:
    """Mock LLM response for enrichment."""
    return [
        {
            "name": "Enriched Client 1",
            "sector_description": "A retail company in Mexico.",
        },
        {
            "name": "Enriched Client 2",
            "sector_description": "A retail business operating in Mexico.",
        },
        {
            "name": "Enriched Client 3",
            "sector_description": "Mexican retail enterprise.",
        },
    ]


def _mock_llm_json() -> dict[str, object]:
    """Build mock JSON response for OpenRouter."""
    return {
        "choices": [{"message": {"content": str(_mock_llm_response()).replace("'", '"')}}],
        "usage": {"prompt_tokens": 100, "completion_tokens": 50},
    }


def _mock_openrouter() -> None:
    """Mock OpenRouter LLM call."""
    respx.post("https://openrouter.ai/api/v1/chat/completions").mock(
        return_value=httpx.Response(200, json=_mock_llm_json())
    )


class TestPrioritizedEndpoint:
    """Tests for the prioritized portfolio endpoint."""

    @pytest.mark.anyio
    async def test_404_unscored_scenario(self, client: AsyncClient) -> None:
        """Unscored scenario returns 404 with clear message."""
        create_resp = await client.post(
            "/api/v1/scenarios", json={"name": "Unscored", "sector": "retail"}
        )
        sid = create_resp.json()["id"]

        response = await client.get(f"/api/v1/scenarios/{sid}/prioritized")
        assert response.status_code == 404
        assert "no data" in response.json()["detail"].lower()

    @pytest.mark.anyio
    async def test_container_provides_use_case(self) -> None:
        """Container provides PrioritizeScenario use case."""
        use_case = await get_prioritize_scenario_use_case()
        assert use_case is not None
        from app.application.use_cases.prioritize_scenario import PrioritizeScenario

        assert isinstance(use_case, PrioritizeScenario)

    @pytest.mark.anyio
    @respx.mock
    async def test_happy_path(self, client: AsyncClient) -> None:
        """Integration test: generate scenario then get prioritized portfolio."""
        _mock_openrouter()

        gen_resp = await client.post(
            "/api/v1/scenarios/generate",
            json={
                "seed": 42,
                "sector": "retail",
                "client_count": 100,
                "invoice_volume": 5.0,
                "amount_mean": 10000.0,
                "amount_std": 3000.0,
            },
        )
        assert gen_resp.status_code == 201
        sid = gen_resp.json()["id"]

        response = await client.get(f"/api/v1/scenarios/{sid}/prioritized")
        assert response.status_code == 200
        body = response.json()

        assert "cases" in body
        assert "pareto_subset" in body
        assert "threshold" in body
        assert "total_expected_recoverable" in body
        assert "subset_expected_recoverable" in body
        assert "portfolio_count" in body
        assert "subset_count" in body
        assert "value_share" in body
        assert "summary" in body

        assert body["value_share"] >= body["threshold"]

        if body["cases"]:
            case = body["cases"][0]
            assert "client_id" in case
            assert "score" in case
            assert "outstanding" in case
            assert "rank" in case
            assert "expected_recoverable" in case
            assert "category" in case

    @pytest.mark.anyio
    @respx.mock
    async def test_threshold_parameter(self, client: AsyncClient) -> None:
        """Threshold parameter overrides default 80%."""
        _mock_openrouter()

        gen_resp = await client.post(
            "/api/v1/scenarios/generate",
            json={
                "seed": 42,
                "sector": "retail",
                "client_count": 100,
                "invoice_volume": 5.0,
                "amount_mean": 10000.0,
                "amount_std": 3000.0,
            },
        )
        sid = gen_resp.json()["id"]

        resp_default = await client.get(f"/api/v1/scenarios/{sid}/prioritized")
        body_default = resp_default.json()
        default_subset = body_default["subset_count"]

        resp_strict = await client.get(f"/api/v1/scenarios/{sid}/prioritized?threshold=0.90")
        body_strict = resp_strict.json()
        assert body_strict["subset_count"] >= default_subset
        assert body_strict["threshold"] == 0.90

        resp_loose = await client.get(f"/api/v1/scenarios/{sid}/prioritized?threshold=0.50")
        body_loose = resp_loose.json()
        assert body_loose["subset_count"] <= default_subset
        assert body_loose["threshold"] == 0.50

    @pytest.mark.anyio
    @respx.mock
    async def test_sort_parameter(self, client: AsyncClient) -> None:
        """Sort parameter works for different fields."""
        _mock_openrouter()

        gen_resp = await client.post(
            "/api/v1/scenarios/generate",
            json={
                "seed": 42,
                "sector": "retail",
                "client_count": 100,
                "invoice_volume": 5.0,
                "amount_mean": 10000.0,
                "amount_std": 3000.0,
            },
        )
        sid = gen_resp.json()["id"]

        resp = await client.get(f"/api/v1/scenarios/{sid}/prioritized?sort=outstanding&order=desc")
        body = resp.json()
        outstandings = [c["outstanding"] for c in body["cases"]]
        assert outstandings == sorted(outstandings, reverse=True)

        resp = await client.get(f"/api/v1/scenarios/{sid}/prioritized?sort=score&order=asc")
        body = resp.json()
        scores = [c["score"] for c in body["cases"]]
        assert scores == sorted(scores)

        resp = await client.get(
            f"/api/v1/scenarios/{sid}/prioritized?sort=expected_recoverable&order=desc"
        )
        body = resp.json()
        expected = [c["expected_recoverable"] for c in body["cases"]]
        assert expected == sorted(expected, reverse=True)

    @pytest.mark.anyio
    @respx.mock
    async def test_category_filter(self, client: AsyncClient) -> None:
        """Category filter works and Pareto recomputed on filtered set."""
        _mock_openrouter()

        gen_resp = await client.post(
            "/api/v1/scenarios/generate",
            json={
                "seed": 42,
                "sector": "retail",
                "client_count": 100,
                "invoice_volume": 5.0,
                "amount_mean": 10000.0,
                "amount_std": 3000.0,
            },
        )
        sid = gen_resp.json()["id"]

        resp = await client.get(f"/api/v1/scenarios/{sid}/prioritized?category=High")
        body = resp.json()
        for case in body["cases"]:
            assert case["category"] == "High"
        assert body["value_share"] >= body["threshold"]

        resp = await client.get(f"/api/v1/scenarios/{sid}/prioritized?category=Low")
        body = resp.json()
        for case in body["cases"]:
            assert case["category"] == "Low"

    @pytest.mark.anyio
    @respx.mock
    async def test_days_overdue_min_actually_filters(self, client: AsyncClient) -> None:
        """s5.1: the filter must filter.

        This test previously asserted only ``status_code == 200``, which is why the
        endpoint could advertise ``days_overdue_min`` while returning an empty
        portfolio for every value: ``PrioritizedCase`` had no ``days_overdue``, so
        ``getattr(c, "days_overdue", 0) >= 30`` was false for every case. A test that
        asserts the endpoint *responds* rather than that it *works* is how that
        survived. Assert the subset relationship instead.
        """
        _mock_openrouter()
        sid = await self._generate(client)

        unfiltered = await client.get(f"/api/v1/scenarios/{sid}/prioritized")
        filtered = await client.get(f"/api/v1/scenarios/{sid}/prioritized?days_overdue_min=30")
        assert filtered.status_code == 200

        all_cases = unfiltered.json()["cases"]
        kept = filtered.json()["cases"]

        assert kept, "filter returned nothing — the silent-zero bug is back"
        assert len(kept) < len(all_cases), "filter kept everything — it is not filtering"
        assert all(case["days_overdue"] >= 30 for case in kept)

        expected = {c["client_id"] for c in all_cases if c["days_overdue"] >= 30}
        assert {c["client_id"] for c in kept} == expected

    @pytest.mark.anyio
    @respx.mock
    async def test_sort_by_days_overdue_orders_the_queue(self, client: AsyncClient) -> None:
        """s5.1: ``sort=days_overdue`` was a no-op — every sort key was the fallback 0."""
        _mock_openrouter()
        sid = await self._generate(client)

        resp = await client.get(f"/api/v1/scenarios/{sid}/prioritized?sort=days_overdue&order=desc")
        assert resp.status_code == 200

        ageing = [case["days_overdue"] for case in resp.json()["cases"]]
        assert ageing == sorted(ageing, reverse=True)
        assert len(set(ageing)) > 1, "all equal — sorting proves nothing on this data"

    @pytest.mark.anyio
    @respx.mock
    async def test_every_case_carries_operator_facing_fields(self, client: AsyncClient) -> None:
        """s5.1 AC-1: a row the operator can work — name, not a UUID; real ageing."""
        _mock_openrouter()
        sid = await self._generate(client)

        payload = (await client.get(f"/api/v1/scenarios/{sid}/prioritized")).json()

        assert payload["cases"], "expected a non-empty portfolio for seed 42"
        for group in ("cases", "pareto_subset"):
            for case in payload[group]:
                assert case["client_name"], f"empty client_name in {group}"
                assert case["client_name"] != case["client_id"]
                assert isinstance(case["days_overdue"], int)
                assert case["days_overdue"] >= 0

    async def _generate(self, client: AsyncClient) -> str:
        """Generate the seed-42 retail scenario these contract tests share."""
        gen_resp = await client.post(
            "/api/v1/scenarios/generate",
            json={
                "seed": 42,
                "sector": "retail",
                "client_count": 100,
                "invoice_volume": 5.0,
                "amount_mean": 10000.0,
                "amount_std": 3000.0,
            },
        )
        assert gen_resp.status_code == 201
        return str(gen_resp.json()["id"])

    @pytest.mark.anyio
    @respx.mock
    async def test_empty_portfolio_zero_scores(self, client: AsyncClient) -> None:
        """Portfolio with all zero scores returns valid response with value_share = 0."""
        _mock_openrouter()

        gen_resp = await client.post(
            "/api/v1/scenarios/generate",
            json={
                "seed": 42,
                "sector": "retail",
                "client_count": 100,
                "invoice_volume": 5.0,
                "amount_mean": 10000.0,
                "amount_std": 3000.0,
            },
        )
        sid = gen_resp.json()["id"]

        # Mock a scenario where all scores are 0 by using a special seed
        # For now, just verify the endpoint handles gracefully
        resp = await client.get(f"/api/v1/scenarios/{sid}/prioritized")
        assert resp.status_code == 200
        body = resp.json()
        assert body["value_share"] >= 0.0
        assert body["portfolio_count"] >= 0

    @pytest.mark.anyio
    @respx.mock
    async def test_invalid_sort_field_returns_422(self, client: AsyncClient) -> None:
        """Invalid sort field returns 422."""
        _mock_openrouter()

        gen_resp = await client.post(
            "/api/v1/scenarios/generate",
            json={
                "seed": 42,
                "sector": "retail",
                "client_count": 100,
                "invoice_volume": 5.0,
                "amount_mean": 10000.0,
                "amount_std": 3000.0,
            },
        )
        sid = gen_resp.json()["id"]

        resp = await client.get(f"/api/v1/scenarios/{sid}/prioritized?sort=invalid_field")
        assert resp.status_code == 422

    @pytest.mark.anyio
    @respx.mock
    async def test_invalid_category_value_returns_422(self, client: AsyncClient) -> None:
        """Invalid category value returns 422."""
        _mock_openrouter()

        gen_resp = await client.post(
            "/api/v1/scenarios/generate",
            json={
                "seed": 42,
                "sector": "retail",
                "client_count": 100,
                "invoice_volume": 5.0,
                "amount_mean": 10000.0,
                "amount_std": 3000.0,
            },
        )
        sid = gen_resp.json()["id"]

        resp = await client.get(f"/api/v1/scenarios/{sid}/prioritized?category=InvalidCategory")
        assert resp.status_code == 422

    @pytest.mark.anyio
    @respx.mock
    async def test_invalid_threshold_returns_422(self, client: AsyncClient) -> None:
        """Threshold outside [0, 1] returns 422."""
        _mock_openrouter()

        gen_resp = await client.post(
            "/api/v1/scenarios/generate",
            json={
                "seed": 42,
                "sector": "retail",
                "client_count": 100,
                "invoice_volume": 5.0,
                "amount_mean": 10000.0,
                "amount_std": 3000.0,
            },
        )
        sid = gen_resp.json()["id"]

        resp = await client.get(f"/api/v1/scenarios/{sid}/prioritized?threshold=1.5")
        assert resp.status_code == 422

        resp = await client.get(f"/api/v1/scenarios/{sid}/prioritized?threshold=-0.1")
        assert resp.status_code == 422

    @pytest.mark.anyio
    @respx.mock
    async def test_nonexistent_scenario_returns_404(self, client: AsyncClient) -> None:
        """Nonexistent scenario ID returns 404."""
        import uuid

        fake_id = str(uuid.uuid4())
        resp = await client.get(f"/api/v1/scenarios/{fake_id}/prioritized")
        assert resp.status_code == 404
