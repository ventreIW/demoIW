from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.domain.enums import Channel, CommunicationStatus, Tone


class Communication(BaseModel):
    id: UUID
    client_id: UUID
    scenario_id: UUID
    channel: Channel
    tone: Tone
    draft_text: str
    status: CommunicationStatus
    created_at: datetime

    model_config = {"frozen": True}
