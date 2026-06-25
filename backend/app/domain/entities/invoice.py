from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class Invoice(BaseModel):
    id: UUID
    client_id: UUID
    folio: str
    amount: float
    issue_date: datetime
    due_date: datetime
    days_overdue: int
    status: str

    model_config = {"frozen": True}
