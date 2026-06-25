from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.domain.enums import ScoreCategory


class Score(BaseModel):
    id: UUID
    client_id: UUID
    scenario_id: UUID
    score_value: float
    category: ScoreCategory
    explanation: str
    scored_at: datetime

    model_config = {"frozen": True}
