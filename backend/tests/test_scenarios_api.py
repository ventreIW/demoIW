import uuid

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


@pytest.mark.anyio
async def test_get_scenario_returns_200(client: AsyncClient) -> None:
    """GET /api/v1/scenarios/{id} returns full scenario detail."""
    # Create a scenario first
    create_resp = await client.post(
        "/api/v1/scenarios", json={"name": "Detail Test", "sector": "manufacturing"}
    )
    scenario_id = create_resp.json()["id"]

    response = await client.get(f"/api/v1/scenarios/{scenario_id}")
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == scenario_id
    assert body["name"] == "Detail Test"
    assert body["sector"] == "manufacturing"
    assert body["seed"] is None
    assert body["parameters"] == {}
    assert body["source"] == "manual"


@pytest.mark.anyio
async def test_get_scenario_returns_404(client: AsyncClient) -> None:
    """GET /api/v1/scenarios/{id} returns 404 for unknown ID."""
    fake_id = str(uuid.uuid4())
    response = await client.get(f"/api/v1/scenarios/{fake_id}")
    assert response.status_code == 404
