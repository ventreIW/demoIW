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


@pytest.mark.anyio
async def test_activate_scenario_happy_path(client: AsyncClient) -> None:
    """PATCH /{id}/activate sets scenario to active and deactivates others."""
    # Create two scenarios
    r1 = await client.post("/api/v1/scenarios", json={"name": "First", "sector": "retail"})
    r2 = await client.post("/api/v1/scenarios", json={"name": "Second", "sector": "manufacturing"})
    id1 = r1.json()["id"]
    id2 = r2.json()["id"]

    # Activate first
    resp = await client.patch(f"/api/v1/scenarios/{id1}/activate")
    assert resp.status_code == 200
    assert resp.json()["status"] == "active"

    # Activate second — deactivates first
    resp = await client.patch(f"/api/v1/scenarios/{id2}/activate")
    assert resp.status_code == 200
    assert resp.json()["status"] == "active"

    # Verify first is now inactive
    check = await client.get(f"/api/v1/scenarios/{id1}")
    assert check.json()["status"] == "inactive"


@pytest.mark.anyio
async def test_activate_scenario_idempotent(client: AsyncClient) -> None:
    """Activating an already-active scenario is idempotent (200)."""
    create_resp = await client.post(
        "/api/v1/scenarios", json={"name": "Only", "sector": "professional_services"}
    )
    sid = create_resp.json()["id"]

    # Activate once
    r1 = await client.patch(f"/api/v1/scenarios/{sid}/activate")
    assert r1.status_code == 200
    assert r1.json()["status"] == "active"

    # Activate again — idempotent
    r2 = await client.patch(f"/api/v1/scenarios/{sid}/activate")
    assert r2.status_code == 200
    assert r2.json()["status"] == "active"


@pytest.mark.anyio
async def test_activate_scenario_not_found(client: AsyncClient) -> None:
    """PATCH /{id}/activate returns 404 for unknown ID."""
    fake_id = str(uuid.uuid4())
    resp = await client.patch(f"/api/v1/scenarios/{fake_id}/activate")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_get_active_returns_200(client: AsyncClient) -> None:
    """GET /api/v1/scenarios/active returns the active scenario."""
    # Create and activate a scenario
    create_resp = await client.post(
        "/api/v1/scenarios", json={"name": "Active One", "sector": "retail"}
    )
    sid = create_resp.json()["id"]
    await client.patch(f"/api/v1/scenarios/{sid}/activate")

    response = await client.get("/api/v1/scenarios/active")
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == sid
    assert body["status"] == "active"
    assert body["name"] == "Active One"


@pytest.mark.anyio
async def test_get_active_returns_404(client: AsyncClient) -> None:
    """GET /api/v1/scenarios/active returns 404 when no scenario is active."""
    response = await client.get("/api/v1/scenarios/active")
    assert response.status_code == 404


@pytest.mark.anyio
@pytest.mark.parametrize("enriched", [True, False])
async def test_generate_scenario_surfaces_enriched_flag(
    client: AsyncClient, enriched: bool
) -> None:
    """POST /generate returns the ground-truth `enriched` flag; 201 either way.

    A degraded run (enriched=False) must be distinguishable from a live one at
    the API — the whole point of s4.8. The use case and repo are overridden so
    this test isolates the router's serialization from the generator/LLM path
    (the real end-to-end run is verified against the model in T5).
    """
    from datetime import UTC, datetime

    from app.container import get_generate_dataset_use_case, get_scenario_repo
    from app.domain.entities.scenario import Scenario
    from app.domain.enums import ScenarioStatus, Sector
    from app.main import app

    scenario = Scenario(
        id=uuid.uuid4(),
        name="Scenario-MANUFACTURING",
        sector=Sector.MANUFACTURING,
        seed=42,
        parameters={},
        source="procedural+enrichment" if enriched else "procedural",
        status=ScenarioStatus.ACTIVE,
        created_at=datetime.now(UTC),
    )

    class _FakeUseCase:
        async def execute(self, body: object, model: str) -> bool:
            return enriched

    class _FakeRepo:
        async def get_active(self) -> Scenario:
            return scenario

        async def get_client_count(self, scenario_id: object) -> int:
            return 5

    app.dependency_overrides[get_generate_dataset_use_case] = lambda: _FakeUseCase()
    app.dependency_overrides[get_scenario_repo] = lambda: _FakeRepo()
    try:
        payload = {
            "seed": 42,
            "sector": "manufacturing",
            "client_count": 5,
            "invoice_volume": 1.0,
            "amount_mean": 10000.0,
            "amount_std": 3000.0,
            "reference_date": None,
        }
        response = await client.post("/api/v1/scenarios/generate", json=payload)
    finally:
        app.dependency_overrides.pop(get_generate_dataset_use_case, None)
        app.dependency_overrides.pop(get_scenario_repo, None)

    assert response.status_code == 201
    assert response.json()["enriched"] is enriched
