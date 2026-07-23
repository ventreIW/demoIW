"""Tests for POST /api/v1/scenarios/{scenario_id}/clients/{client_id}/rescore endpoint (s4.6)."""

import uuid

import httpx
import pytest
import respx
from httpx import AsyncClient


class TestRescoreEndpoint:
    """Tests for the rescore endpoint."""

    @pytest.mark.anyio
    async def test_container_provides_use_case(self) -> None:
        """Container provides RescoreScenario use case."""
        from app.container import get_rescore_scenario_use_case

        use_case = await get_rescore_scenario_use_case()
        assert use_case is not None
        from app.application.use_cases.rescore_scenario import RescoreScenario

        assert isinstance(use_case, RescoreScenario)

    @pytest.mark.anyio
    @respx.mock
    async def test_happy_path(self, client: AsyncClient) -> None:
        """Integration test: generate scenario, rescore client, verify updated score and Pareto."""
        mock_llm_response = [
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

        # Get original prioritized list
        orig_resp = await client.get(f"/api/v1/scenarios/{sid}/prioritized")
        assert orig_resp.status_code == 200
        orig_body = orig_resp.json()
        client_id = orig_body["cases"][0]["client_id"]
        orig_score = orig_body["cases"][0]["score"]

        # Rescore with promise_to_pay (+10)
        rescore_resp = await client.post(
            f"/api/v1/scenarios/{sid}/clients/{client_id}/rescore",
            json={"contact_result": "promise_to_pay"},
        )
        assert rescore_resp.status_code == 200
        rescore_body = rescore_resp.json()

        # Verify updated score
        updated_case = next(c for c in rescore_body["cases"] if c["client_id"] == client_id)
        # Score is orig_score + 10, clamped to 100, with floating point precision
        expected_score = min(100, orig_score + 10)
        assert abs(updated_case["score"] - expected_score) < 0.01

        # Verify Pareto subset is present
        assert "pareto_subset" in rescore_body
        assert len(rescore_body["pareto_subset"]) > 0
        assert rescore_body["value_share"] >= 0.80

    @pytest.mark.anyio
    @respx.mock
    async def test_invalid_contact_result(self, client: AsyncClient) -> None:
        """Invalid contact_result returns 422 with valid options."""
        # Mock OpenRouter LLM call
        mock_llm_response = [
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

        # Get a client ID from the prioritized list
        resp = await client.get(f"/api/v1/scenarios/{sid}/prioritized")
        assert resp.status_code == 200
        body = resp.json()
        client_id = body["cases"][0]["client_id"]

        # Try rescore with invalid contact_result
        response = await client.post(
            f"/api/v1/scenarios/{sid}/clients/{client_id}/rescore",
            json={"contact_result": "invalid_value"},
        )
        assert response.status_code == 422
        detail = response.json()["detail"]
        # Pydantic returns enum validation error as a list of errors
        assert any("invalid_value" in str(err) for err in detail)

    @pytest.mark.anyio
    @respx.mock
    async def test_unknown_scenario(self, client: AsyncClient) -> None:
        """Unknown scenario_id returns 404."""

        fake_id = str(uuid.uuid4())
        response = await client.post(
            f"/api/v1/scenarios/{fake_id}/clients/{uuid.uuid4()}/rescore",
            json={"contact_result": "promise_to_pay"},
        )
        assert response.status_code == 404

    @pytest.mark.anyio
    @respx.mock
    async def test_unknown_client(self, client: AsyncClient) -> None:
        """Unknown client_id returns 404."""

        mock_llm_response = [
            {"name": "Enriched Client 1", "sector_description": "A retail company in Mexico."},
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

        response = await client.post(
            f"/api/v1/scenarios/{sid}/clients/{uuid.uuid4()}/rescore",
            json={"contact_result": "promise_to_pay"},
        )
        assert response.status_code == 404

    @pytest.mark.anyio
    @respx.mock
    async def test_unscored_scenario(self, client: AsyncClient) -> None:
        """Unscored scenario returns 404."""

        # Create a scenario without scores
        create_resp = await client.post(
            "/api/v1/scenarios", json={"name": "Unscored", "sector": "retail"}
        )
        assert create_resp.status_code == 201
        sid = create_resp.json()["id"]

        response = await client.post(
            f"/api/v1/scenarios/{sid}/clients/{uuid.uuid4()}/rescore",
            json={"contact_result": "promise_to_pay"},
        )
        assert response.status_code == 404
