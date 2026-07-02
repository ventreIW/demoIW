import uuid
from datetime import date, timedelta

import numpy as np
import pandas as pd
from faker import Faker

from app.application.use_cases.generate_dataset import GenerationParams
from app.domain.enums import PaymentPattern, Sector
from app.domain.value_objects.raw_dataset import RawDataset
from app.ports.dataset_port import IDatasetPort

# Probabilities over PaymentPattern (enum order), per sector. Each row sums to 1.0.
_SECTOR_PATTERN_WEIGHTS: dict[Sector, list[float]] = {
    #                 ON_TIME DELAYED_30 DELAYED_60 DELAYED_90_PLUS PARTIAL DEFAULT
    Sector.MANUFACTURING: [0.30, 0.30, 0.15, 0.08, 0.10, 0.07],
    Sector.RETAIL: [0.25, 0.20, 0.15, 0.10, 0.20, 0.10],
    Sector.PROFESSIONAL_SERVICES: [0.45, 0.20, 0.10, 0.05, 0.15, 0.05],
}

_MIN_AMOUNT = 100.0


class ProceduralGenerator(IDatasetPort):
    """Seed-based procedural generator for synthetic AR portfolios.

    Determinism comes from two anchors seeded identically: ``np.random.default_rng``
    for numeric sampling and ``Faker.seed`` for company names. UUIDs are drawn from
    the numpy RNG (not ``uuid.uuid4``) so identity is reproducible too.
    """

    def __init__(self, params: GenerationParams) -> None:
        self._params = params
        self._rng: np.random.Generator = np.random.default_rng(params.seed)
        self._faker = Faker("es_MX")
        Faker.seed(params.seed)

    def generate(self) -> RawDataset:
        clients = self._generate_clients()
        invoices = self._generate_invoices(clients)
        payments = self._generate_payments(invoices)
        return RawDataset(clients=clients, invoices=invoices, payments=payments)

    def _uuid(self) -> str:
        """Deterministic UUID drawn from the seeded RNG."""
        return str(uuid.UUID(bytes=self._rng.bytes(16), version=4))

    def _generate_clients(self) -> pd.DataFrame:
        n = self._params.client_count
        weights = _SECTOR_PATTERN_WEIGHTS[self._params.sector]
        pattern_values = [p.value for p in PaymentPattern]
        names = [self._faker.company() for _ in range(n)]
        ids = [self._uuid() for _ in range(n)]
        patterns = self._rng.choice(pattern_values, size=n, p=weights).tolist()
        return pd.DataFrame(
            {
                "id": ids,
                "name": names,
                "sector": self._params.sector.value,
                "payment_history_pattern": patterns,
            }
        )

    def _generate_invoices(self, clients: pd.DataFrame) -> pd.DataFrame:
        params = self._params
        today = date.today()
        rows: list[dict[str, object]] = []
        for client_id in clients["id"]:
            n_invoices = max(1, int(self._rng.poisson(params.invoice_volume)))
            for _ in range(n_invoices):
                amount = max(
                    _MIN_AMOUNT, float(self._rng.normal(params.amount_mean, params.amount_std))
                )
                days_overdue = int(self._rng.exponential(params.days_overdue_lambda))
                is_overdue = bool(self._rng.random() < params.overdue_rate)
                rows.append(
                    {
                        "id": self._uuid(),
                        "client_id": client_id,
                        "amount": round(amount, 2),
                        "days_overdue": days_overdue,
                        "due_date": today - timedelta(days=days_overdue),
                        "status": "overdue" if is_overdue else "paid",
                    }
                )
        return pd.DataFrame(rows)

    def _generate_payments(self, invoices: pd.DataFrame) -> pd.DataFrame:
        columns = ["id", "invoice_id", "amount", "paid_date"]
        settled = invoices[invoices["status"] == "paid"]
        rows: list[dict[str, object]] = []
        for _, invoice in settled.iterrows():
            rows.append(
                {
                    "id": self._uuid(),
                    "invoice_id": invoice["id"],
                    "amount": invoice["amount"],
                    "paid_date": invoice["due_date"],
                }
            )
        if not rows:
            return pd.DataFrame(columns=columns)
        return pd.DataFrame(rows)
