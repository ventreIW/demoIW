import uuid

import pytest
from httpx import AsyncClient


@pytest.mark.anyio
@pytest.mark.parametrize("already", [False, True])
async def test_score_endpoint_returns_summary(client: AsyncClient, already: bool) -> None:
    from app.application.use_cases.score_and_persist_scenario import ScorePersistResult
    from app.container import get_score_and_persist_use_case
    from app.main import app

    sid = uuid.uuid4()

    class _Stub:
        async def execute(self, scenario_id: uuid.UUID) -> ScorePersistResult:
            return ScorePersistResult(scored_count=60, unscored_count=12, already_persisted=already)

    app.dependency_overrides[get_score_and_persist_use_case] = lambda: _Stub()
    try:
        response = await client.post(f"/api/v1/scenarios/{sid}/score")
    finally:
        app.dependency_overrides.pop(get_score_and_persist_use_case, None)

    assert response.status_code == 201
    body = response.json()
    assert body["scenario_id"] == str(sid)
    assert body["scored_count"] == 60
    assert body["unscored_count"] == 12
    assert body["already_persisted"] is already


@pytest.mark.anyio
async def test_score_endpoint_404_when_not_found(client: AsyncClient) -> None:
    from app.container import get_score_and_persist_use_case
    from app.domain.exceptions import EntityNotFoundError
    from app.main import app

    sid = uuid.uuid4()

    class _Stub:
        async def execute(self, scenario_id: uuid.UUID) -> None:
            raise EntityNotFoundError("Scenario", str(scenario_id))

    app.dependency_overrides[get_score_and_persist_use_case] = lambda: _Stub()
    try:
        response = await client.post(f"/api/v1/scenarios/{sid}/score")
    finally:
        app.dependency_overrides.pop(get_score_and_persist_use_case, None)

    assert response.status_code == 404
