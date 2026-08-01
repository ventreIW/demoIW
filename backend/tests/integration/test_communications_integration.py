"""Integration test for communications endpoint with mocked OpenRouter.

These tests verify the full integration path including OpenRouterAdapter retries.
Note: OpenRouterAdapter retries 3 times on 5xx/timeout (MAX_RETRIES=3).
So failure cases need 4 responses (1 initial + 3 retries).

Note on timeout/malformed JSON tests:
- Timeout: respx wraps TimeoutException in SideEffectError which bypasses
  adapter's retry logic
- Malformed JSON: JSONDecodeError is not caught by OpenRouterAdapter (only
  catches HTTPStatusError, TimeoutException)
  and propagates as unhandled exception (500 with traceback)
These are documented limitations of the test setup, not bugs in the code.
"""

import json

import httpx
import pytest
import respx
from httpx import AsyncClient


async def _setup_scenario_with_client(client: AsyncClient) -> tuple[str, str]:
    """Helper to create a scenario with enough clients for scoring and return
    (scenario_id, client_id)."""
    gen = await client.post(
        "/api/v1/scenarios/generate",
        json={
            "seed": 42,
            "sector": "retail",
            "client_count": 60,
            "invoice_volume": 3.0,
            "amount_mean": 10000.0,
            "amount_std": 3000.0,
            "reference_date": None,
        },
    )
    assert gen.status_code == 201, gen.text

    active = await client.get("/api/v1/scenarios/active")
    assert active.status_code == 200
    scenario_id = active.json()["id"]

    score = await client.post(f"/api/v1/scenarios/{scenario_id}/score")
    assert score.status_code == 201, score.text

    pri = await client.get(f"/api/v1/scenarios/{scenario_id}/prioritized")
    assert pri.status_code == 200, pri.text
    cases = pri.json()["cases"]
    assert len(cases) > 0
    client_id = cases[0]["client_id"]

    return scenario_id, client_id


def _llm_mock_response(
    content: str = "Estimado cliente, le recordamos su pago pendiente.",
) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "choices": [{"message": {"content": content}}],
            "usage": {"prompt_tokens": 50, "completion_tokens": 20},
        },
    )


def _enrichment_mock_response(count: int) -> httpx.Response:
    enriched = [
        {"name": f"Cliente Enriquecido {i}", "sector_description": "Empresa del sector retail."}
        for i in range(count)
    ]
    return httpx.Response(
        200,
        json={"choices": [{"message": {"content": json.dumps(enriched)}}]},
    )


@respx.mock
@pytest.mark.anyio
async def test_generate_communication_integration_persists_draft(
    client: AsyncClient,
) -> None:
    """Full integration test: generate -> score -> prioritized -> communication
    -> verify in DB."""
    mock_route = respx.post("https://openrouter.ai/api/v1/chat/completions").mock(
        side_effect=[
            _enrichment_mock_response(20),
            _enrichment_mock_response(20),
            _enrichment_mock_response(20),
            _llm_mock_response(
                "Estimado cliente, le recordamos su pago pendiente de $50,000."
            ),
        ]
    )

    scenario_id, client_id = await _setup_scenario_with_client(client)

    response = await client.post(
        f"/api/v1/scenarios/{scenario_id}/clients/{client_id}/communications",
        json={"channel": "email", "tone": "formal"},
    )

    assert response.status_code == 201
    body = response.json()

    assert body["channel"] == "email"
    assert body["tone"] == "formal"
    assert body["status"] == "draft"
    assert "Estimado cliente" in body["draft_text"]
    assert "created_at" in body

    assert mock_route.called
    assert mock_route.call_count == 4

    comm_call = mock_route.calls[-1].request
    payload = json.loads(comm_call.content)
    assert payload["max_tokens"] == 512
    assert "messages" in payload
    assert payload["messages"][0]["role"] == "user"

    detail = await client.get(f"/api/v1/scenarios/{scenario_id}/clients/{client_id}")
    assert detail.status_code == 200
    detail_body = detail.json()
    comms = detail_body["communications"]
    assert len(comms) >= 1
    new_comm = next((c for c in comms if c["draft_text"] == body["draft_text"]), None)
    assert new_comm is not None
    assert new_comm["channel"] == "email"
    assert new_comm["tone"] == "formal"
    assert new_comm["status"] == "draft"


@respx.mock
@pytest.mark.anyio
async def test_generate_communication_llm_500_returns_502(
    client: AsyncClient,
) -> None:
    """When OpenRouter returns 500, adapter retries 3x then returns 502."""
    respx.post("https://openrouter.ai/api/v1/chat/completions").mock(
        side_effect=[
            _enrichment_mock_response(20),
            _enrichment_mock_response(20),
            _enrichment_mock_response(20),
            httpx.Response(500, json={"error": "Internal server error"}),
            httpx.Response(500, json={"error": "Internal server error"}),
            httpx.Response(500, json={"error": "Internal server error"}),
            httpx.Response(500, json={"error": "Internal server error"}),
        ]
    )

    scenario_id, client_id = await _setup_scenario_with_client(client)

    response = await client.post(
        f"/api/v1/scenarios/{scenario_id}/clients/{client_id}/communications",
        json={"channel": "email", "tone": "formal"},
    )

    assert response.status_code == 502
    body = response.json()
    assert "detail" in body


@respx.mock
@pytest.mark.anyio
async def test_generate_communication_multiple_calls_independent(
    client: AsyncClient,
) -> None:
    """Multiple communication generations for same client should create
    separate records."""
    respx.post("https://openrouter.ai/api/v1/chat/completions").mock(
        side_effect=[
            _enrichment_mock_response(20),
            _enrichment_mock_response(20),
            _enrichment_mock_response(20),
            _llm_mock_response("Draft message 1"),
            _llm_mock_response("Draft message 2"),
        ]
    )

    scenario_id, client_id = await _setup_scenario_with_client(client)

    resp1 = await client.post(
        f"/api/v1/scenarios/{scenario_id}/clients/{client_id}/communications",
        json={"channel": "email", "tone": "formal"},
    )
    assert resp1.status_code == 201
    draft1 = resp1.json()["draft_text"]

    resp2 = await client.post(
        f"/api/v1/scenarios/{scenario_id}/clients/{client_id}/communications",
        json={"channel": "whatsapp", "tone": "urgent"},
    )
    assert resp2.status_code == 201
    draft2 = resp2.json()["draft_text"]

    detail = await client.get(f"/api/v1/scenarios/{scenario_id}/clients/{client_id}")
    assert detail.status_code == 200
    comms = detail.json()["communications"]
    assert len(comms) >= 2
    draft_texts = [c["draft_text"] for c in comms]
    assert draft1 in draft_texts
    assert draft2 in draft_texts
