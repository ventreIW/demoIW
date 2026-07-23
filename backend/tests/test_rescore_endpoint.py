"""Tests for POST /api/v1/scenarios/{scenario_id}/clients/{client_id}/rescore endpoint (s4.6)."""

import httpx
import pytest
import respx


class TestRescoreEndpoint:
    """Tests for the rescore endpoint."""

    @pytest.mark.anyio
    @respx.mock
    async def test_invalid_contact_result(self, client) -> None:
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
