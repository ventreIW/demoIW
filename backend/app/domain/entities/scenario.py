from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.domain.enums import ScenarioStatus, Sector


class Scenario(BaseModel):
    id: UUID
    name: str
    sector: Sector
    seed: int | None
    parameters: dict[str, object]
    source: str
    status: ScenarioStatus
    created_at: datetime

    model_config = {"frozen": True}
