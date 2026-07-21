"""Client-level feature schema for the collectability model (ADR-006).

``FEATURE_COLUMNS`` is the single source of truth for what the model sees.
s4.3 (training) and s4.4 (explanation) index by it, so a literal column name
written anywhere else is a drift bug waiting to happen.

What is deliberately *absent* matters as much as what is present:
``payment_history_pattern`` causally generates every invoice and payment in the
dataset and is stored on the client record. It must never appear here — a model
given it would score near-perfectly by reading the variable that produced its own
labels. See ADR-006.
"""

from typing import Final

#: Numeric and boolean features fed to the model, in a stable order.
FEATURE_COLUMNS: Final[list[str]] = [
    "days_overdue_max",
    "days_overdue_mean",
    "outstanding_amount",
    "invoice_count",
    "avg_invoice_amount",
    "pct_invoices_settled",
    "avg_days_late_historical",
    "has_partial_payments",
]

#: Categorical features requiring encoding before training (one-hot in s4.2 T4).
CATEGORICAL_COLUMNS: Final[list[str]] = ["sector"]

#: Identity column — carried through extraction so the split can be done by
#: client, but never fed to the model.
ID_COLUMN: Final[str] = "client_id"

#: Columns that must never reach the model, whatever else changes.
FORBIDDEN_COLUMNS: Final[frozenset[str]] = frozenset({"payment_history_pattern", "name"})
