"""
Integration tests for the case detail aggregate endpoint.

Tests for 404 handling (unknown scenario, unknown client). The full
data-composition path is verified by the unit tests on the individual
repos and the manual E2E test in Task 5.
"""

import uuid

import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_case_detail_404_unknown_scenario(client: AsyncClient) -> None:
    """GET with unknown scenario_id returns 404."""
    fake_sid = str(uuid.uuid4())
    fake_cid = str(uuid.uuid4())
    response = await client.get(f"/api/v1/scenarios/{fake_sid}/clients/{fake_cid}")
    assert response.status_code == 404


@pytest.mark.anyio
async def test_case_detail_404_unknown_client(client: AsyncClient) -> None:
    """GET with unknown client_id returns 404 for a valid scenario."""
    create_resp = await client.post(
        "/api/v1/scenarios", json={"name": "Detail 404", "sector": "retail"}
    )
    assert create_resp.status_code == 201
    scenario_id = create_resp.json()["id"]

    fake_cid = str(uuid.uuid4())
    response = await client.get(f"/api/v1/scenarios/{scenario_id}/clients/{fake_cid}")
    assert response.status_code == 404
