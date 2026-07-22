"""Tests for GET /api/v1/scenarios/{scenario_id}/prioritized endpoint (s4.5-API)."""

import pytest
from uuid import uuid4
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