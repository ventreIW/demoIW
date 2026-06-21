import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_health_ok(client: AsyncClient) -> None:
    """GET /health returns 200 with connected status."""
    response = await client.get("/health")
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["status"] == "ok"
    assert json_data["db"] == "connected"


@pytest.mark.anyio
async def test_health_db_unavailable(client_unavailable: AsyncClient) -> None:
    """GET /health returns 503 when DB is unreachable."""
    response = await client_unavailable.get("/health")
    assert response.status_code == 503
    json_data = response.json()
    assert json_data["status"] == "degraded"
    assert json_data["db"] == "unavailable"
