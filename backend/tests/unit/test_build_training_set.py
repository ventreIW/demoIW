"""Tests for training-set assembly (s4.2 T4, ADR-006).

Joins features to labels, encodes the categorical, and splits **by client**. The
split discipline matters: a client appearing on both sides would let the model
memorise individuals and report an optimistic score that collapses on real data.
"""

from datetime import datetime

import pandas as pd
import pytest

from app.application.use_cases.build_training_set import BuildTrainingSet
from app.domain.exceptions import InsufficientTrainingDataError
from app.domain.value_objects.client_features import FEATURE_COLUMNS
from app.domain.value_objects.raw_dataset import RawDataset


def _client(client_id: str, pattern: str, sector: str = "retail") -> dict:
    return {
        "id": client_id,
        "name": f"Empresa {client_id}",
        "sector": sector,
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


def _settled_invoice(invoice_id: str, client_id: str) -> dict:
    due = datetime.fromisoformat("2026-03-01")
    return {
        "id": invoice_id,
        "client_id": client_id,
        "folio": f"INV-{invoice_id}",
        "amount": 1000.0,
        "issue_date": due,
        "due_date": due,
        "days_overdue": 0,
        "status": "paid",
    }


def _payment(payment_id: str, invoice_id: str, amount: float = 1000.0) -> dict:
    return {
        "id": payment_id,
        "invoice_id": invoice_id,
        "amount": amount,
        "paid_date": datetime.fromisoformat("2026-03-05"),
    }


def _mixed_dataset(size: int = 120) -> RawDataset:
    """A realistic spread of patterns so both label classes appear."""
    patterns = ["on_time", "delayed_30", "delayed_60", "delayed_90_plus", "partial", "default"]
    clients, invoices = [], []
    for i in range(size):
        pattern = patterns[i % len(patterns)]
        clients.append(_client(f"c{i:03d}", pattern))
        invoices.append(_open_invoice(f"i{i:03d}", f"c{i:03d}", amount=1000.0 + i))
    return RawDataset(
        clients=pd.DataFrame(clients),
        invoices=pd.DataFrame(invoices),
        payments=pd.DataFrame(columns=["id", "invoice_id", "amount", "paid_date"]),
    )


# --- Split discipline -----------------------------------------------------


def test_split_is_disjoint_by_client() -> None:
    ts = BuildTrainingSet().execute(_mixed_dataset(), seed=42)

    assert set(ts.train_client_ids) & set(ts.test_client_ids) == set()
    assert len(ts.train_client_ids) + len(ts.test_client_ids) == len(ts.client_ids)


def test_both_classes_present_in_each_split() -> None:
    ts = BuildTrainingSet().execute(_mixed_dataset(300), seed=42)

    assert set(ts.y_train.unique()) == {0, 1}
    assert set(ts.y_test.unique()) == {0, 1}


def test_split_respects_test_fraction() -> None:
    ts = BuildTrainingSet().execute(_mixed_dataset(200), seed=42, test_fraction=0.25)

    ratio = len(ts.test_client_ids) / len(ts.client_ids)
    assert 0.2 <= ratio <= 0.3


def test_x_and_y_are_aligned() -> None:
    ts = BuildTrainingSet().execute(_mixed_dataset(), seed=42)

    assert len(ts.X_train) == len(ts.y_train)
    assert len(ts.X_test) == len(ts.y_test)


# --- Leakage --------------------------------------------------------------


def test_no_forbidden_column_reaches_the_matrix() -> None:
    """The guard, restated at the boundary the model actually consumes."""
    ts = BuildTrainingSet().execute(_mixed_dataset(), seed=42)

    assert "payment_history_pattern" not in ts.X_train.columns
    assert "client_id" not in ts.X_train.columns
    assert "name" not in ts.X_train.columns


def test_feature_matrix_contains_expected_features() -> None:
    ts = BuildTrainingSet().execute(_mixed_dataset(), seed=42)

    for column in FEATURE_COLUMNS:
        assert column in ts.X_train.columns


def test_sector_is_absent_from_design_matrix() -> None:
    """s4.3 D5: sector is constant within a scenario, so it carries no signal.

    GenerationParams takes one sector for the whole scenario and the generator
    writes it to every client, so a one-hot column would have zero variance —
    a dead feature a reader of the model would wrongly assume matters.
    """
    dataset = _mixed_dataset(60)

    ts = BuildTrainingSet().execute(dataset, seed=42)

    assert not [c for c in ts.X_train.columns if c.startswith("sector")]
    assert "sector" not in ts.X_train.columns


# --- Determinism ----------------------------------------------------------


def test_training_set_is_deterministic_for_seed() -> None:
    dataset = _mixed_dataset()

    first = BuildTrainingSet().execute(dataset, seed=42)
    second = BuildTrainingSet().execute(dataset, seed=42)

    pd.testing.assert_frame_equal(first.X_train, second.X_train)
    pd.testing.assert_series_equal(first.y_train, second.y_train)
    assert first.train_client_ids == second.train_client_ids


def test_different_seed_changes_the_split() -> None:
    dataset = _mixed_dataset(200)

    first = BuildTrainingSet().execute(dataset, seed=1)
    second = BuildTrainingSet().execute(dataset, seed=2)

    assert first.train_client_ids != second.train_client_ids


# --- Exclusions and error paths -------------------------------------------


def test_excluded_client_count_is_reported() -> None:
    """D4: settled-only clients are dropped, and the caller is told how many."""
    clients = [_client(f"c{i}", "delayed_60") for i in range(60)]
    clients += [_client(f"s{i}", "on_time") for i in range(10)]
    invoices = [_open_invoice(f"i{i}", f"c{i}") for i in range(60)]
    invoices += [_settled_invoice(f"si{i}", f"s{i}") for i in range(10)]
    payments = [_payment(f"p{i}", f"si{i}") for i in range(10)]

    dataset = RawDataset(
        clients=pd.DataFrame(clients),
        invoices=pd.DataFrame(invoices),
        payments=pd.DataFrame(payments),
    )

    ts = BuildTrainingSet().execute(dataset, seed=42)

    assert ts.excluded_client_count == 10
    assert len(ts.client_ids) == 60
    assert not any(cid.startswith("s") for cid in ts.client_ids)


def test_single_label_class_raises_with_a_clear_message() -> None:
    """A uniform cohort cannot train a classifier — say so loudly."""
    clients = [_client(f"c{i}", "on_time") for i in range(40)]
    invoices = [_open_invoice(f"i{i}", f"c{i}") for i in range(40)]
    dataset = RawDataset(
        clients=pd.DataFrame(clients),
        invoices=pd.DataFrame(invoices),
        payments=pd.DataFrame(columns=["id", "invoice_id", "amount", "paid_date"]),
    )

    with pytest.raises(InsufficientTrainingDataError) as excinfo:
        BuildTrainingSet().execute(dataset, seed=42)

    message = str(excinfo.value)
    assert "single label class" in message
    assert "40" in message


def test_too_few_clients_raises() -> None:
    clients = [_client("c1", "on_time"), _client("c2", "default")]
    invoices = [_open_invoice("i1", "c1"), _open_invoice("i2", "c2")]
    dataset = RawDataset(
        clients=pd.DataFrame(clients),
        invoices=pd.DataFrame(invoices),
        payments=pd.DataFrame(columns=["id", "invoice_id", "amount", "paid_date"]),
    )

    with pytest.raises(InsufficientTrainingDataError, match="at least"):
        BuildTrainingSet().execute(dataset, seed=42)


def test_positive_rate_is_exposed_for_baseline_comparison() -> None:
    """s4.3 needs the majority-class rate to state its baseline (ADR-006 D3)."""
    ts = BuildTrainingSet().execute(_mixed_dataset(300), seed=42)

    assert 0.0 < ts.positive_rate < 1.0
    assert ts.positive_rate == pytest.approx(ts.y.mean())
