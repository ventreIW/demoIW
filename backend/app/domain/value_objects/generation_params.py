from datetime import date

from pydantic import BaseModel, Field

from app.domain.enums import Sector


class GenerationParams(BaseModel):
    """Seed parameters controlling procedural dataset generation.

    Fully determines the output: the same params (including seed and reference_date)
    always produce an identical RawDataset.

    Overdue behaviour is NOT a global knob — it emerges from each client's
    ``payment_history_pattern`` (sector-weighted). A portfolio's overall overdue
    rate is therefore a consequence of its sector's behavioural mix, which is what makes the data learnable by the collectability engine (E4).
    """

    seed: int
    sector: Sector
    client_count: int = Field(gt=0)
    invoice_volume: float = Field(gt=0, description="Poisson mean invoices per client")
    amount_mean: float = Field(gt=0)
    amount_std: float = Field(ge=0)
    reference_date: date | None = Field(
        default=None,
        description="'Today' anchor for ageing invoices. None resolves to date.today() "
        "at generation; pin it for cross-day reproducibility.",
    )

    model_config = {"frozen": True}