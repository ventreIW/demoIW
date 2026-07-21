"""Tests for forward-outcome labelling (s4.2 T3, ADR-006 D2/D4).

The label is a *simulated future event*: will this client's outstanding balance be
collected within the horizon. Features are the present snapshot, so features and
label are separated by a time boundary — which is what stops the model from
inverting the generator.

Note the asymmetry with the feature extractor: the labeller *does* read
``payment_history_pattern``, because it is the hidden truth being simulated from.
Only the features must never see it.
"""

from datetime import datetime

import pandas as pd
import pytest

from app.application.services.outcome_labeller import (
    LABEL_COLUMN,
    InsufficientOutstandingError,
    OutcomeLabeller,
)
from app.domain.value_objects.raw_dataset import RawDataset


def _dataset(clients: list[dict], invoices: list[dict], payments: list[dict]) -> RawDataset:
    payment_cols = ["id", "invoice_id", "amount", "paid_date"]
    return RawDataset(
        clients=pd.DataFrame(clients),
        invoices=pd.DataFrame(invoices),
        payments=pd.DataFrame(payments) if payments else pd.DataFrame(columns=payment_cols),
    )


def _client(client_id: str, pattern: str) -> dict:
    return {
        "id": client_id,
        "name": f"Empresa {client_id}",
        "sector": "retail",
        "payment_history_pattern": pattern,
    }


def _open_invoice(invoice_id: str, client_id: str, amount: float = 1000.0) -> dict:
    due = datetime.fromisoformat("2026-05-01")
    return {
        "id": invoice_id,
        "client_id": client_id,
        "folio": f"INV-{invoice_id}",
        "amount": amount,
        "issue_date": due,
        "due_date": due,
        "days_overdue": 40,
        "status": "overdue",
    }


def _settled_invoice(invoice_id: str, client_id: str, amount: float = 1000.0) -> dict:
    due = datetime.fromisoformat("2026-03-01")
    return {
        "id": invoice_id,
        "client_id": client_id,
        "folio": f"INV-{invoice_id}",
        "amount": amount,
        "issue_date": due,
        "due_date": due,
        "days_overdue": 0,
        "status": "paid",
    }


def _cohort(pattern: str, size: int) -> RawDataset:
    clients = [_client(f"{pattern}-{i}", pattern) for i in range(size)]
    invoices = [_open_invoice(f"i{pattern}-{i}", f"{pattern}-{i}") for i in range(size)]
    return _dataset(clients, invoices, [])


# --- The signal check: does the label mean anything? ----------------------


def test_on_time_cohort_collects_more_than_default() -> None:
    """The whole story depends on this separation existing.

    If it fails, ADR-006's horizon produces no learnable gradient and s4.3 must
    not proceed — revise the ADR first.
    """
    on_time = OutcomeLabeller(seed=42).label(_cohort("on_time", 500))
    default = OutcomeLabeller(seed=42).label(_cohort("default", 500))

    on_time_rate = on_time[LABEL_COLUMN].mean()
    default_rate = default[LABEL_COLUMN].mean()

    assert on_time_rate > default_rate
    assert on_time_rate - default_rate > 0.3, (
        f"separation too weak to learn: on_time={on_time_rate:.3f} " f"default={default_rate:.3f}"
    )


def test_collection_rate_is_monotonic_across_severity() -> None:
    """Matches the gradient in ADR-006 D2."""
    rates = [
        OutcomeLabeller(seed=7).label(_cohort(pattern, 400))[LABEL_COLUMN].mean()
        for pattern in ("on_time", "delayed_30", "delayed_60", "delayed_90_plus", "default")
    ]
    assert rates == sorted(rates, reverse=True), rates


def test_on_time_almost_always_collects_within_horizon() -> None:
    rate = OutcomeLabeller(seed=1).label(_cohort("on_time", 400))[LABEL_COLUMN].mean()
    assert rate > 0.95


def test_default_frequently_misses_the_horizon() -> None:
    rate = OutcomeLabeller(seed=1).label(_cohort("default", 400))[LABEL_COLUMN].mean()
    assert rate < 0.65


# --- Determinism ----------------------------------------------------------


def test_labels_deterministic_for_seed() -> None:
    dataset = _cohort("delayed_60", 50)

    first = OutcomeLabeller(seed=42).label(dataset)
    second = OutcomeLabeller(seed=42).label(dataset)

    pd.testing.assert_series_equal(first[LABEL_COLUMN], second[LABEL_COLUMN])


def test_different_seed_gives_different_labels() -> None:
    """Guards the determinism test from passing on a constant."""
    dataset = _cohort("delayed_60", 200)

    first = OutcomeLabeller(seed=1).label(dataset)
    second = OutcomeLabeller(seed=2).label(dataset)

    assert not first[LABEL_COLUMN].equals(second[LABEL_COLUMN])


# --- Shape and exclusions -------------------------------------------------


def test_label_is_binary() -> None:
    labels = OutcomeLabeller(seed=42).label(_cohort("delayed_30", 100))
    assert set(labels[LABEL_COLUMN].unique()) <= {0, 1}


def test_clients_with_no_outstanding_are_excluded() -> None:
    """D4: 'will it be collected' is undefined when there is nothing to collect."""
    dataset = _dataset(
        [_client("c1", "delayed_30"), _client("c2", "on_time")],
        [_open_invoice("i1", "c1"), _settled_invoice("i2", "c2")],
        [
            {
                "id": "p1",
                "invoice_id": "i2",
                "amount": 1000.0,
                "paid_date": datetime.fromisoformat("2026-03-05"),
            }
        ],
    )

    labels = OutcomeLabeller(seed=42).label(dataset)

    assert list(labels["client_id"]) == ["c1"]


def test_partial_payer_with_balance_is_included() -> None:
    """Netting to a positive balance still counts as outstanding."""
    dataset = _dataset(
        [_client("c1", "partial")],
        [_open_invoice("i1", "c1", amount=1000.0)],
        [
            {
                "id": "p1",
                "invoice_id": "i1",
                "amount": 400.0,
                "paid_date": datetime.fromisoformat("2026-05-10"),
            }
        ],
    )

    labels = OutcomeLabeller(seed=42).label(dataset)

    assert list(labels["client_id"]) == ["c1"]


def test_all_clients_settled_raises() -> None:
    dataset = _dataset(
        [_client("c1", "on_time")],
        [_settled_invoice("i1", "c1")],
        [
            {
                "id": "p1",
                "invoice_id": "i1",
                "amount": 1000.0,
                "paid_date": datetime.fromisoformat("2026-03-05"),
            }
        ],
    )

    with pytest.raises(InsufficientOutstandingError, match="no clients with an outstanding"):
        OutcomeLabeller(seed=42).label(dataset)


def test_horizon_is_configurable() -> None:
    """A longer horizon can only collect more, never less."""
    dataset = _cohort("delayed_90_plus", 300)

    short = OutcomeLabeller(seed=3).label(dataset, horizon_days=30)[LABEL_COLUMN].mean()
    long = OutcomeLabeller(seed=3).label(dataset, horizon_days=180)[LABEL_COLUMN].mean()

    assert long > short
