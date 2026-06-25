from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.domain.enums import ContactResultType


class ContactResult(BaseModel):
    id: UUID
    client_id: UUID
    communication_id: UUID
    result_type: ContactResultType
    notes: str | None
    recorded_at: datetime

    model_config = {"frozen": True}
