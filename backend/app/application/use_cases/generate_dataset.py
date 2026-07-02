from pydantic import BaseModel, Field

from app.domain.enums import Sector


class GenerationParams(BaseModel):
    """Seed parameters controlling procedural dataset generation.

    Fully determines the output: the same params (including seed) always produce
    an identical RawDataset.
    """

    seed: int
    sector: Sector
    client_count: int = Field(gt=0)
    invoice_volume: float = Field(gt=0, description="Poisson mean invoices per client")
    amount_mean: float = Field(gt=0)
    amount_std: float = Field(ge=0)
    days_overdue_lambda: float = Field(gt=0)
    overdue_rate: float = Field(ge=0, le=1)

    model_config = {"frozen": True}
