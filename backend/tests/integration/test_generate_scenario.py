import httpx
import pytest
import respx
from httpx import AsyncClient


@pytest.mark.anyio
@respx.mock
async def test_generate_scenario_valid_returns_201_and_persists(client: AsyncClient) -> None:
    """POST /api/v1/scenarios/generate returns 201 and persists scenario + 3 clients."""
    # Arrange: Mock LLM response for enrichment
    # Enrichment service expects JSON array with name and sector_description
    mock_llm_response = [
        {"name": "Enriched Client 1", "sector_description": "A retail company in Mexico."},
        {
            "name": "Enriched Client 2",
            "sector_description": "A retail business operating in Mexico.",
        },
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

    # Act
    payload = {
        "seed": 42,
        "sector": "retail",
        "client_count": 3,
        "invoice_volume": 5.0,
        "amount_mean": 1000.0,
        "amount_std": 200.0,
    }
    response = await client.post("/api/v1/scenarios/generate", json=payload)

    # Assert: HTTP 201
    assert response.status_code == 201
    body = response.json()

    # Assert: Response matches ScenarioSummary shape
    assert "id" in body
    assert body["name"] == "Scenario-retail"
    assert body["sector"] == "retail"
    assert body["status"] == "active"  # generate_scenario activates it
    assert body["client_count"] == 3
    assert "created_at" in body

    scenario_id = body["id"]

    # Assert: Scenario is persisted in DB
    # Use the test session from the client fixture's engine
    # We need to get the session from the app's dependency override
    # The client fixture creates its own engine; we can't directly access it
    # Instead, make another API call to verify persistence
    get_response = await client.get(f"/api/v1/scenarios/{scenario_id}")
    assert get_response.status_code == 200
    detail = get_response.json()
    assert detail["id"] == scenario_id
    assert detail["name"] == "Scenario-retail"
    assert detail["client_count"] == 3

    # Also verify active scenario endpoint works
    active_response = await client.get("/api/v1/scenarios/active")
    assert active_response.status_code == 200
    assert active_response.json()["id"] == scenario_id


@pytest.mark.anyio
async def test_generate_scenario_invalid_params_returns_422(client: AsyncClient) -> None:
    """POST /api/v1/scenarios/generate with invalid params returns 422."""
    # Missing required field: seed
    payload = {
        "sector": "retail",
        "client_count": 3,
        "invoice_volume": 5.0,
        "amount_mean": 1000.0,
        "amount_std": 200.0,
    }

    response = await client.post("/api/v1/scenarios/generate", json=payload)

    assert response.status_code == 422


@pytest.mark.anyio
async def test_generate_scenario_invalid_sector_returns_422(client: AsyncClient) -> None:
    """POST /api/v1/scenarios/generate with invalid sector returns 422."""
    payload = {
        "seed": 42,
        "sector": "invalid_sector",
        "client_count": 3,
        "invoice_volume": 5.0,
        "amount_mean": 1000.0,
        "amount_std": 200.0,
    }

    response = await client.post("/api/v1/scenarios/generate", json=payload)

    assert response.status_code == 422


@pytest.mark.anyio
@respx.mock
async def test_generate_scenario_llm_failure_graceful_degradation(client: AsyncClient) -> None:
    """POST /api/v1/scenarios/generate handles LLM failure gracefully."""
    # Arrange: Mock LLM to return 500
    respx.post("https://openrouter.ai/api/v1/chat/completions").mock(
        return_value=httpx.Response(500, json={"error": "Internal server error"})
    )

    payload = {
        "seed": 42,
        "sector": "retail",
        "client_count": 3,
        "invoice_volume": 5.0,
        "amount_mean": 1000.0,
        "amount_std": 200.0,
    }

    response = await client.post("/api/v1/scenarios/generate", json=payload)

    # The enrichment service has graceful degradation - it falls back to original data
    # So the endpoint should still succeed (201) but with non-enriched names
    assert response.status_code == 201
    body = response.json()
    assert body["client_count"] == 3
    # Verify the scenario was created and is active
    assert body["status"] == "active"
