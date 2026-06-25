from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.container import get_scenario_repo
from app.domain.enums import Sector
from app.ports.repositories import IScenarioRepository

router = APIRouter(prefix="/api/v1/scenarios", tags=["scenarios"])


class ScenarioSummary(BaseModel):
    id: UUID
    name: str
    sector: Sector
    status: str
    client_count: int
    created_at: datetime


@router.get("", response_model=list[ScenarioSummary])
async def list_scenarios(
    repo: IScenarioRepository = Depends(get_scenario_repo),
) -> list[ScenarioSummary]:
    scenarios = await repo.list_all()
    result: list[ScenarioSummary] = []
    for s in scenarios:
        count = await repo.get_client_count(s.id)
        result.append(
            ScenarioSummary(
                id=s.id,
                name=s.name,
                sector=s.sector,
                status=s.status.value,
                client_count=count,
                created_at=s.created_at,
            )
        )
    return result
