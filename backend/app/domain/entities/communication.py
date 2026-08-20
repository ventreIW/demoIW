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

    #: NFR-06 provenance. All optional: a record written before BUG-08, or one whose
    #: operator is unknown, must be able to say so rather than carry an invented value.
    operator_id: str | None = None
    model_used: str | None = None
    prompt_version: str | None = None
    sent_at: datetime | None = None

    model_config = {"frozen": True}
