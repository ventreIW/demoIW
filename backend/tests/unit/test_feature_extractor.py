"""Tests for client-level feature extraction (s4.2 T2, ADR-006).

The leakage guard is the reason this story exists. ``payment_history_pattern``
causally generates every invoice and payment in the dataset and is stored on the
client record; a model given it as a feature scores ~100% by reading the answer
key. The first test below is the constraint that keeps that from happening.
"""

from datetime import datetime

import pandas as pd
import pytest

from app.application.services.feature_extractor import FeatureExtractor
from app.domain.value_objects.client_features import FEATURE_COLUMNS


def _dataset(
    clients: list[dict[str, object]],
    invoices: list[dict[str, object]],
    payments: list[dict[str, object]],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    from app.domain.value_objects.raw_dataset import RawDataset

    payment_cols = ["id", "invoice_id", "amount", "paid_date"]
    ds = RawDataset(
        clients=pd.DataFrame(clients),
        invoices=pd.DataFrame(invoices),
        payments=pd.DataFrame(payments) if payments else pd.DataFrame(columns=payment_cols),
    )
    return ds  # type: ignore[return-value]


def _client(client_id: str, pattern: str = "delayed_30") -> dict[str, object]:
    return {
        "id": client_id,
        "name": f"Empresa {client_id}",
        "sector": "retail",
        "payment_history_pattern": pattern,
    }


def _invoice(
    invoice_id: str,
    client_id: str,
    amount: float,
    status: str,
    due: str,
    days_overdue: int = 0,
) -> dict[str, object]:
    due_date = datetime.fromisoformat(due)
    return {
        "id": invoice_id,
        "client_id": client_id,
        "folio": f"INV-{invoice_id}",
        "amount": amount,
        "issue_date": due_date,
        "due_date": due_date,
        "days_overdue": days_overdue,
        "status": status,
    }


def _payment(payment_id: str, invoice_id: str, amount: float, paid: str) -> dict[str, object]:
    return {
        "id": payment_id,
        "invoice_id": invoice_id,
        "amount": amount,
        "paid_date": datetime.fromisoformat(paid),
    }


# --- The leakage guard ----------------------------------------------------


def test_leakage_guard_pattern_absent_from_features() -> None:
    """ADR-006: payment_history_pattern must never reach the model.

    If this test ever fails, the collectability score becomes meaningless — the
    model would be reading the variable that generated its own labels.
    """
    ds = _dataset(
        [_client("c1", pattern="default"), _client("c2", pattern="on_time")],
        [_invoice("i1", "c1", 1000.0, "overdue", "2026-05-01", 60)],
        [],
    )

    features = FeatureExtractor().extract(ds)

    assert "payment_history_pattern" not in features.columns
    assert not any("pattern" in c for c in features.columns)


def test_feature_columns_constant_matches_output() -> None:
    """s4.3 and s4.4 index by FEATURE_COLUMNS; drift here breaks them silently."""
    ds = _dataset(
        [_client("c1")],
        [_invoice("i1", "c1", 1000.0, "overdue", "2026-05-01", 30)],
        [],
    )

    features = FeatureExtractor().extract(ds)

    assert set(FEATURE_COLUMNS).issubset(set(features.columns))


# --- Aggregation correctness ----------------------------------------------


def test_one_row_per_client() -> None:
    ds = _dataset(
        [_client("c1"), _client("c2"), _client("c3")],
        [
            _invoice("i1", "c1", 100.0, "overdue", "2026-05-01", 30),
            _invoice("i2", "c1", 200.0, "paid", "2026-04-01"),
            _invoice("i3", "c2", 300.0, "paid", "2026-04-01"),
        ],
        [_payment("p1", "i2", 200.0, "2026-04-10"), _payment("p2", "i3", 300.0, "2026-04-05")],
    )

    features = FeatureExtractor().extract(ds)

    assert len(features) == 3
    assert set(features["client_id"]) == {"c1", "c2", "c3"}


def test_outstanding_nets_partial_payments() -> None:
    """A partial payer still owes the balance, not the full invoice.

    Gemba finding: partial payers emit a payment SMALLER than the invoice on an
    invoice still marked overdue. Summing invoice amounts would overstate
    exposure for exactly the cohort a collections model cares about most.
    """
    ds = _dataset(
        [_client("c1", pattern="partial")],
        [_invoice("i1", "c1", 1000.0, "overdue", "2026-05-01", 45)],
        [_payment("p1", "i1", 400.0, "2026-05-10")],
    )

    features = FeatureExtractor().extract(ds)
    row = features.iloc[0]

    assert row["outstanding_amount"] == pytest.approx(600.0)
    assert row["has_partial_payments"]


def test_outstanding_is_full_amount_when_no_payment() -> None:
    ds = _dataset(
        [_client("c1")],
        [_invoice("i1", "c1", 1000.0, "overdue", "2026-05-01", 45)],
        [],
    )

    features = FeatureExtractor().extract(ds)

    assert features.iloc[0]["outstanding_amount"] == pytest.approx(1000.0)
    assert not features.iloc[0]["has_partial_payments"]


def test_days_overdue_max_and_mean() -> None:
    ds = _dataset(
        [_client("c1")],
        [
            _invoice("i1", "c1", 100.0, "overdue", "2026-05-01", 10),
            _invoice("i2", "c1", 100.0, "overdue", "2026-04-01", 50),
            _invoice("i3", "c1", 100.0, "paid", "2026-03-01"),
        ],
        [_payment("p1", "i3", 100.0, "2026-03-05")],
    )

    row = FeatureExtractor().extract(ds).iloc[0]

    assert row["days_overdue_max"] == pytest.approx(50.0)
    assert row["days_overdue_mean"] == pytest.approx(30.0)  # open invoices only


def test_pct_invoices_settled() -> None:
    ds = _dataset(
        [_client("c1")],
        [
            _invoice("i1", "c1", 100.0, "paid", "2026-03-01"),
            _invoice("i2", "c1", 100.0, "paid", "2026-03-01"),
            _invoice("i3", "c1", 100.0, "overdue", "2026-05-01", 20),
            _invoice("i4", "c1", 100.0, "overdue", "2026-05-01", 20),
        ],
        [_payment("p1", "i1", 100.0, "2026-03-05"), _payment("p2", "i2", 100.0, "2026-03-05")],
    )

    row = FeatureExtractor().extract(ds).iloc[0]

    assert row["pct_invoices_settled"] == pytest.approx(0.5)
    assert row["invoice_count"] == 4


def test_avg_days_late_historical_derived_from_paid_minus_due() -> None:
    """Not stored anywhere — must be derived by joining payments to invoices."""
    ds = _dataset(
        [_client("c1")],
        [
            _invoice("i1", "c1", 100.0, "paid", "2026-03-01"),
            _invoice("i2", "c1", 100.0, "paid", "2026-03-01"),
        ],
        [
            _payment("p1", "i1", 100.0, "2026-03-11"),  # 10 days late
            _payment("p2", "i2", 100.0, "2026-03-21"),  # 20 days late
        ],
    )

    row = FeatureExtractor().extract(ds).iloc[0]

    assert row["avg_days_late_historical"] == pytest.approx(15.0)


# --- Missing-data contract ------------------------------------------------


def test_no_settled_invoices_yields_zero_not_nan() -> None:
    ds = _dataset(
        [_client("c1")],
        [_invoice("i1", "c1", 500.0, "overdue", "2026-05-01", 30)],
        [],
    )

    row = FeatureExtractor().extract(ds).iloc[0]

    assert row["pct_invoices_settled"] == pytest.approx(0.0)
    assert row["avg_days_late_historical"] == pytest.approx(0.0)
    assert not pd.isna(row).any()


def test_no_open_invoices_yields_zero_not_nan() -> None:
    ds = _dataset(
        [_client("c1")],
        [_invoice("i1", "c1", 500.0, "paid", "2026-03-01")],
        [_payment("p1", "i1", 500.0, "2026-03-02")],
    )

    row = FeatureExtractor().extract(ds).iloc[0]

    assert row["outstanding_amount"] == pytest.approx(0.0)
    assert row["days_overdue_max"] == pytest.approx(0.0)
    assert not pd.isna(row).any()


def test_client_with_no_invoices_yields_zeros() -> None:
    ds = _dataset(
        [_client("c1"), _client("c2")],
        [_invoice("i1", "c1", 100.0, "overdue", "2026-05-01", 5)],
        [],
    )

    features = FeatureExtractor().extract(ds).set_index("client_id")

    assert features.loc["c2", "invoice_count"] == 0
    assert features.loc["c2", "outstanding_amount"] == pytest.approx(0.0)
    assert not pd.isna(features.loc["c2"]).any()


def test_extraction_is_deterministic() -> None:
    ds = _dataset(
        [_client("c1"), _client("c2")],
        [
            _invoice("i1", "c1", 100.0, "overdue", "2026-05-01", 30),
            _invoice("i2", "c2", 200.0, "paid", "2026-03-01"),
        ],
        [_payment("p1", "i2", 200.0, "2026-03-05")],
    )

    first = FeatureExtractor().extract(ds)
    second = FeatureExtractor().extract(ds)

    pd.testing.assert_frame_equal(first, second)


def test_sector_is_preserved_for_downstream_encoding() -> None:
    ds = _dataset(
        [_client("c1")],
        [_invoice("i1", "c1", 100.0, "overdue", "2026-05-01", 5)],
        [],
    )

    assert FeatureExtractor().extract(ds).iloc[0]["sector"] == "retail"
