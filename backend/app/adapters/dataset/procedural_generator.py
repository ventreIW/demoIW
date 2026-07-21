import uuid
from dataclasses import dataclass
from datetime import date, timedelta

import numpy as np
import pandas as pd
from faker import Faker

from app.domain.enums import PaymentPattern, Sector
from app.domain.value_objects.generation_params import GenerationParams
from app.domain.value_objects.raw_dataset import RawDataset
from app.ports.dataset_port import IDatasetPort


@dataclass(frozen=True)
class _PatternProfile:
    """Behavioural profile a payment pattern imposes on a client's invoices.

    ``overdue_prob``  P(an invoice is currently past-due and unsettled).
    ``late_days_mean`` Exponential scale (days) for both how overdue an open invoice
                       is and how late a settled invoice was paid.
    ``partial_payer``  When overdue, this client makes a partial payment (balance
                       still outstanding) rather than none.
    """

    overdue_prob: float
    late_days_mean: float
    partial_payer: bool


# Pattern → behaviour. Ordered from healthiest to worst so overdue propensity is
# monotonic — this is the signal the collectability engine (E4) is meant to learn.
_PATTERN_PROFILES: dict[PaymentPattern, _PatternProfile] = {
    PaymentPattern.ON_TIME: _PatternProfile(
        overdue_prob=0.05, late_days_mean=3.0, partial_payer=False
    ),
    PaymentPattern.DELAYED_30: _PatternProfile(
        overdue_prob=0.25, late_days_mean=30.0, partial_payer=False
    ),
    PaymentPattern.DELAYED_60: _PatternProfile(
        overdue_prob=0.45, late_days_mean=60.0, partial_payer=False
    ),
    PaymentPattern.DELAYED_90_PLUS: _PatternProfile(
        overdue_prob=0.65, late_days_mean=100.0, partial_payer=False
    ),
    PaymentPattern.PARTIAL: _PatternProfile(
        overdue_prob=0.60, late_days_mean=50.0, partial_payer=True
    ),
    PaymentPattern.DEFAULT: _PatternProfile(
        overdue_prob=0.90, late_days_mean=160.0, partial_payer=False
    ),
}

# Probabilities over PaymentPattern (enum order), per sector. Each row sums to 1.0.
_SECTOR_PATTERN_WEIGHTS: dict[Sector, list[float]] = {
    #                 ON_TIME DELAYED_30 DELAYED_60 DELAYED_90_PLUS PARTIAL DEFAULT
    Sector.MANUFACTURING: [0.30, 0.30, 0.15, 0.08, 0.10, 0.07],
    Sector.RETAIL: [0.25, 0.20, 0.15, 0.10, 0.20, 0.10],
    Sector.PROFESSIONAL_SERVICES: [0.45, 0.20, 0.10, 0.05, 0.15, 0.05],
}

_MIN_AMOUNT = 100.0
_PAYMENT_TERM_DAYS = 30  # issue_date = due_date - net-30 terms
_PARTIAL_MIN, _PARTIAL_MAX = 0.20, 0.60  # fraction of amount a partial payer covers


class ProceduralGenerator(IDatasetPort):
    """Seed-based procedural generator for synthetic AR portfolios.

    Determinism comes from two anchors seeded identically: ``np.random.default_rng``
    for numeric sampling and ``Faker.seed`` for company names. UUIDs are drawn from
    the numpy RNG (not ``uuid.uuid4``) so identity is reproducible too. Each client's
    payment pattern causally drives its invoices' overdue status, ageing, and payments.
    """

    def __init__(self, params: GenerationParams) -> None:
        self._params = params
        self._rng: np.random.Generator = np.random.default_rng(params.seed)
        self._faker = Faker("es_MX")
        Faker.seed(params.seed)
        self._today = params.reference_date or date.today()
        self._folio_seq = 0

    def generate(self) -> RawDataset:
        clients = self._generate_clients()
        invoices, payments = self._generate_invoices_and_payments(clients)
        return RawDataset(clients=clients, invoices=invoices, payments=payments)

    def _uuid(self) -> str:
        """Deterministic UUID drawn from the seeded RNG."""
        return str(uuid.UUID(bytes=self._rng.bytes(16), version=4))

    def _next_folio(self) -> str:
        self._folio_seq += 1
        return f"INV-{self._folio_seq:05d}"

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

    def _generate_invoices_and_payments(
        self, clients: pd.DataFrame
    ) -> tuple[pd.DataFrame, pd.DataFrame]:
        params = self._params
        invoice_rows: list[dict[str, object]] = []
        payment_rows: list[dict[str, object]] = []

        for client_id, pattern_value in zip(
            clients["id"], clients["payment_history_pattern"], strict=True
        ):
            profile = _PATTERN_PROFILES[PaymentPattern(pattern_value)]
            n_invoices = max(1, int(self._rng.poisson(params.invoice_volume)))
            for _ in range(n_invoices):
                amount = round(
                    max(
                        _MIN_AMOUNT, float(self._rng.normal(params.amount_mean, params.amount_std))
                    ),
                    2,
                )
                invoice_id = self._uuid()
                is_overdue = bool(self._rng.random() < profile.overdue_prob)
                if is_overdue:
                    row, payment = self._build_overdue(invoice_id, client_id, amount, profile)
                else:
                    row, payment = self._build_settled(invoice_id, client_id, amount, profile)
                invoice_rows.append(row)
                if payment is not None:
                    payment_rows.append(payment)

        invoices = pd.DataFrame(invoice_rows)
        payment_cols = ["id", "invoice_id", "amount", "paid_date"]
        payments = (
            pd.DataFrame(payment_rows) if payment_rows else pd.DataFrame(columns=payment_cols)
        )
        return invoices, payments

    def _build_overdue(
        self, invoice_id: str, client_id: object, amount: float, profile: _PatternProfile
    ) -> tuple[dict[str, object], dict[str, object] | None]:
        days_overdue = int(self._rng.exponential(profile.late_days_mean)) + 1
        due_date = self._today - timedelta(days=days_overdue)
        row: dict[str, object] = {
            "id": invoice_id,
            "client_id": client_id,
            "folio": self._next_folio(),
            "amount": amount,
            "issue_date": due_date - timedelta(days=_PAYMENT_TERM_DAYS),
            "due_date": due_date,
            "days_overdue": days_overdue,
            "status": "overdue",
        }
        payment: dict[str, object] | None = None
        if profile.partial_payer:
            fraction = float(self._rng.uniform(_PARTIAL_MIN, _PARTIAL_MAX))
            paid_offset = int(self._rng.integers(0, days_overdue)) if days_overdue > 1 else 0
            payment = {
                "id": self._uuid(),
                "invoice_id": invoice_id,
                "amount": round(amount * fraction, 2),
                "paid_date": due_date + timedelta(days=paid_offset),
            }
        return row, payment

    def _build_settled(
        self, invoice_id: str, client_id: object, amount: float, profile: _PatternProfile
    ) -> tuple[dict[str, object], dict[str, object]]:
        days_late = int(self._rng.exponential(profile.late_days_mean))
        settled_days_ago = int(self._rng.integers(1, 60))
        paid_date = self._today - timedelta(days=settled_days_ago)
        due_date = paid_date - timedelta(days=days_late)
        row: dict[str, object] = {
            "id": invoice_id,
            "client_id": client_id,
            "folio": self._next_folio(),
            "amount": amount,
            "issue_date": due_date - timedelta(days=_PAYMENT_TERM_DAYS),
            "due_date": due_date,
            "days_overdue": 0,
            "status": "paid",
        }
        payment: dict[str, object] = {
            "id": self._uuid(),
            "invoice_id": invoice_id,
            "amount": amount,
            "paid_date": paid_date,
        }
        return row, payment
