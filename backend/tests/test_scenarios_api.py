import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_list_scenarios_empty_returns_200(client: AsyncClient) -> None:
    """GET /api/v1/scenarios on an empty DB returns 200 with empty list."""
    response = await client.get("/api/v1/scenarios")
    assert response.status_code == 200
    assert response.json() == []
