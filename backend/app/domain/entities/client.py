from uuid import UUID

from pydantic import BaseModel

from app.domain.enums import PaymentPattern


class Client(BaseModel):
    id: UUID
    scenario_id: UUID
    name: str
    sector_description: str | None
    payment_history_pattern: PaymentPattern

    model_config = {"frozen": True}
