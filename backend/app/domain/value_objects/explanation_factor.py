"""A single named driver behind a collectability score (s4.4).

Sits between the model's per-feature contributions and the Spanish sentence an
officer reads. Model features map onto *business* factors, which is not
one-to-one: ``days_overdue_max`` and ``days_overdue_mean`` are two measurements
of the same thing — how old the debt is — and are represented by one
:attr:`FactorKey.AGEING` factor.
"""

from dataclasses import dataclass
from enum import StrEnum
from typing import Final


class FactorKey(StrEnum):
    """Business drivers an officer would recognise, not model feature names."""

    AGEING = "ageing"
    SETTLEMENT = "settlement"
    OUTSTANDING = "outstanding"
    PAYMENT_LATENESS = "payment_lateness"
    INVOICE_COUNT = "invoice_count"
    PARTIAL_PAYMENTS = "partial_payments"
    INVOICE_SIZE = "invoice_size"


#: Model feature → business factor.
#:
#: ``days_overdue_max`` and ``days_overdue_mean`` both map to ``AGEING``. Their
#: contributions correlate at 0.885 and 26.2% of clients have both in their top
#: tier, so naming them separately would state the same fact twice.
#:
#: The mapping is many-to-one by design; grouping is a property of this table,
#: not of the ranking algorithm, so adding a future pair means editing here only.
FEATURE_TO_FACTOR: Final[dict[str, FactorKey]] = {
    "days_overdue_max": FactorKey.AGEING,
    "days_overdue_mean": FactorKey.AGEING,
    "pct_invoices_settled": FactorKey.SETTLEMENT,
    "outstanding_amount": FactorKey.OUTSTANDING,
    "avg_days_late_historical": FactorKey.PAYMENT_LATENESS,
    "invoice_count": FactorKey.INVOICE_COUNT,
    "has_partial_payments": FactorKey.PARTIAL_PAYMENTS,
    "avg_invoice_amount": FactorKey.INVOICE_SIZE,
}


@dataclass(frozen=True)
class ExplanationFactor:
    """One driver, with its signed contribution to the score.

    ``contribution`` is the sum over every feature mapping to ``key``. Positive
    raises collectability, negative lowers it.
    """

    key: FactorKey
    contribution: float
