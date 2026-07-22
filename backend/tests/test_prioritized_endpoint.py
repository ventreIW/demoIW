"""Tests for GET /api/v1/scenarios/{scenario_id}/prioritized endpoint (s4.5-API)."""

import httpx
import pytest
import respx
from app.container import get_prioritize_scenario_use_case


class TestPrioritizedEndpoint:
    """Tests for the prioritized portfolio endpoint."""

    @pytest.mark.anyio
    async def test_404_unscored_scenario(self, client) -> None:
        """Unscored scenario returns 404 with clear message."""
        # Create a scenario without scores
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
    async def test_happy_path(self, client) -> None:
        """Integration test: generate scenario then get prioritized portfolio."""
        # Mock OpenRouter LLM call
        mock_llm_response = [
            {"name": "Enriched Client 1", "sector_description": "A retail company in Mexico."},
            {"name": "Enriched Client 2", "sector_description": "A retail business operating in Mexico."},
            {"name": "Enriched Client 3", "sector_description": "Mexican retail enterprise."},
        ]
        respx.post("https://openrouter.ai/api/v1/chat/completions").mock(
            return_value=httpx.Response(
                200,
                json={
                    "choices": [{"message": {"content": str(mock_llm_response).replace("'", '"')}}],
                    "usage": {"prompt_tokens": 100, "completion_tokens": 50},
                },
            )
        )

        # Generate a scenario with scores
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

        # Get prioritized portfolio
        response = await client.get(f"/api/v1/scenarios/{sid}/prioritized")
        assert response.status_code == 200
        body = response.json()

        # Top-level fields from PrioritizedPortfolio
        assert "cases" in body
        assert "pareto_subset" in body
        assert "threshold" in body
        assert "total_expected_recoverable" in body
        assert "subset_expected_recoverable" in body
        assert "portfolio_count" in body
        assert "subset_count" in body
        assert "value_share" in body
        assert "summary" in body

        # Pareto subset reaches threshold
        assert body["value_share"] >= body["threshold"]

        # Each case has PrioritizedCase fields
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
    async def test_response_shape_matches_contract(self, client) -> None:
        """Response shape matches PrioritizedPortfolio contract exactly."""
        # Mock OpenRouter LLM call
        mock_llm_response = [
            {"name": "Enriched Client 1", "sector_description": "A retail company in Mexico."},
            {"name": "Enriched Client 2", "sector_description": "A retail business operating in Mexico."},
            {"name": "Enriched Client 3", "sector_description": "Mexican retail enterprise."},
        ]
        respx.post("https://openrouter.ai/api/v1/chat/completions").mock(
            return_value=httpx.Response(
                200,
                json={
                    "choices": [{"message": {"content": str(mock_llm_response).replace("'", '"')}}],
                    "usage": {"prompt_tokens": 100, "completion_tokens": 50},
                },
            )
        )

        # Generate a scored scenario
        gen_resp = await client.post(
            "/api/v1/scenarios/generate",
            json={
                "seed": 42,
                "sector": "retail",
                "client_count": 50,
                "invoice_volume": 5.0,
                "amount_mean": 10000.0,
                "amount_std": 3000.0,
            },
        )
        sid = gen_resp.json()["id"]

        response = await client.get(f"/api/v1/scenarios/{sid}/prioritized")
        assert response.status_code == 200
        body = response.json()

        # Top-level fields from PrioritizedPortfolio
        assert "cases" in body
        assert "pareto_subset" in body
        assert "threshold" in body
        assert "total_expected_recoverable" in body
        assert "subset_expected_recoverable" in body
        assert "portfolio_count" in body
        assert "subset_count" in body
        assert "value_share" in body
        assert "summary" in body

        # Each case has PrioritizedCase fields
        if body["cases"]:
            case = body["cases"][0]
            assert "client_id" in case
            assert "score" in case
            assert "outstanding" in case
            assert "rank" in case
            assert "expected_recoverable" in case
            assert "category" in case