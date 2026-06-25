from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class Payment(BaseModel):
    id: UUID
    invoice_id: UUID
    amount: float
    payment_date: datetime
    method: str

    model_config = {"frozen": True}
