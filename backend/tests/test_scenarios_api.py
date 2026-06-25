import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_list_scenarios_empty_returns_200(client: AsyncClient) -> None:
    """GET /api/v1/scenarios on an empty DB returns 200 with empty list."""
    response = await client.get("/api/v1/scenarios")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.anyio
async def test_create_scenario_returns_201(client: AsyncClient) -> None:
    """POST /api/v1/scenarios creates a blank scenario and returns 201."""
    payload = {"name": "Demo Q3", "sector": "retail"}
    response = await client.post("/api/v1/scenarios", json=payload)
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Demo Q3"
    assert body["sector"] == "retail"
    assert body["status"] == "inactive"
    assert body["client_count"] == 0
    assert "id" in body
    assert "created_at" in body
