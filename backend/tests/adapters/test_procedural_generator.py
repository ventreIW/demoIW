import inspect
from datetime import date

import pandas as pd
import pytest
from pydantic import ValidationError

from app.adapters.dataset.procedural_generator import ProceduralGenerator
from app.application.use_cases.generate_dataset import GenerationParams
from app.domain.enums import PaymentPattern, Sector
from app.domain.value_objects.raw_dataset import RawDataset
from app.ports.dataset_port import IDatasetPort

_REF = date(2026, 7, 2)


def _params(**overrides: object) -> GenerationParams:
    base: dict[str, object] = {
        "seed": 42,
        "sector": Sector.MANUFACTURING,
        "client_count": 50,
        "invoice_volume": 4.0,
        "amount_mean": 10_000.0,
        "amount_std": 3_000.0,
        "reference_date": _REF,
    }
    base.update(overrides)
    return GenerationParams(**base)  # type: ignore[arg-type]


def _gen(**overrides: object) -> RawDataset:
    return ProceduralGenerator(_params(**overrides)).generate()


def _invoices_with_pattern(ds: RawDataset) -> pd.DataFrame:
    return ds.invoices.merge(
        ds.clients[["id", "payment_history_pattern"]],
        left_on="client_id",
        right_on="id",
        suffixes=("", "_client"),
    )


# --- Contract tests ------------------------------------------------------


def test_generation_params_rejects_nonpositive_client_count() -> None:
    with pytest.raises(ValidationError):
        _params(client_count=0)


def test_generation_params_rejects_nonpositive_invoice_volume() -> None:
    with pytest.raises(ValidationError):
        _params(invoice_volume=0)


def test_raw_dataset_holds_three_frames() -> None:
    empty = pd.DataFrame()
    ds = RawDataset(clients=empty, invoices=empty, payments=empty)
    assert isinstance(ds.clients, pd.DataFrame)
    assert isinstance(ds.invoices, pd.DataFrame)
    assert isinstance(ds.payments, pd.DataFrame)


def test_dataset_port_is_abstract() -> None:
    assert inspect.isabstract(IDatasetPort)
    with pytest.raises(TypeError):
        IDatasetPort()  # type: ignore[abstract]


def test_procedural_generator_implements_port() -> None:
    assert issubclass(ProceduralGenerator, IDatasetPort)


# --- Determinism & structure ---------------------------------------------


def test_determinism() -> None:
    a = _gen()
    b = _gen()
    pd.testing.assert_frame_equal(a.clients, b.clients)
    pd.testing.assert_frame_equal(a.invoices, b.invoices)
    pd.testing.assert_frame_equal(a.payments, b.payments)


def test_client_count_matches_params() -> None:
    ds = _gen(client_count=37)
    assert ds.clients.shape[0] == 37


def test_amounts_positive() -> None:
    ds = _gen(client_count=200)
    assert (ds.invoices["amount"] > 0).all()
    assert ds.invoices["amount"].min() >= 100.0


def test_amount_mean_within_tolerance() -> None:
    ds = _gen(client_count=400, invoice_volume=6.0)
    sample_mean = float(ds.invoices["amount"].mean())
    assert 0.85 * 10_000.0 <= sample_mean <= 1.15 * 10_000.0


# --- Sector weighting ----------------------------------------------------


def test_sector_weighting_manufacturing_slower_than_retail() -> None:
    manu = _gen(sector=Sector.MANUFACTURING, client_count=1000)
    retail = _gen(sector=Sector.RETAIL, client_count=1000)
    manu_slow = float((manu.clients["payment_history_pattern"] == PaymentPattern.DELAYED_30).mean())
    retail_slow = float(
        (retail.clients["payment_history_pattern"] == PaymentPattern.DELAYED_30).mean()
    )
    assert manu_slow > retail_slow


# --- Causal behaviour: pattern drives outcomes ---------------------------


def test_pattern_drives_overdue_propensity() -> None:
    """The core realism guarantee: overdue rate rises monotonically with pattern severity."""
    ds = _gen(sector=Sector.MANUFACTURING, client_count=3000, invoice_volume=5.0)
    inv = _invoices_with_pattern(ds)
    overdue = inv.assign(is_overdue=inv["status"] == "overdue")
    frac = overdue.groupby("payment_history_pattern")["is_overdue"].mean()

    on_time = float(frac[PaymentPattern.ON_TIME.value])
    delayed_60 = float(frac[PaymentPattern.DELAYED_60.value])
    default = float(frac[PaymentPattern.DEFAULT.value])

    assert on_time < 0.15
    assert default > 0.75
    assert on_time < delayed_60 < default


def test_days_overdue_coherent_with_status() -> None:
    ds = _gen(client_count=300)
    overdue = ds.invoices[ds.invoices["status"] == "overdue"]
    paid = ds.invoices[ds.invoices["status"] == "paid"]
    assert (overdue["days_overdue"] >= 1).all()
    assert (paid["days_overdue"] == 0).all()


def test_settled_invoice_has_full_payment() -> None:
    ds = _gen(client_count=300)
    paid = ds.invoices[ds.invoices["status"] == "paid"]
    merged = paid.merge(ds.payments, left_on="id", right_on="invoice_id", suffixes=("_inv", "_pay"))
    # exactly one payment per settled invoice, covering the full amount
    assert len(merged) == len(paid)
    assert (merged["amount_inv"] == merged["amount_pay"]).all()


def test_partial_payers_make_partial_payments_on_overdue() -> None:
    ds = _gen(sector=Sector.RETAIL, client_count=1500)  # RETAIL has the most PARTIAL clients
    inv = _invoices_with_pattern(ds)
    partial_overdue = inv[
        (inv["payment_history_pattern"] == PaymentPattern.PARTIAL.value)
        & (inv["status"] == "overdue")
    ]
    merged = partial_overdue.merge(
        ds.payments, left_on="id", right_on="invoice_id", suffixes=("_inv", "_pay")
    )
    assert len(merged) > 0
    assert (merged["amount_pay"] < merged["amount_inv"]).all()


def test_default_overdue_invoices_have_no_payment() -> None:
    ds = _gen(sector=Sector.MANUFACTURING, client_count=1500)
    inv = _invoices_with_pattern(ds)
    default_overdue = inv[
        (inv["payment_history_pattern"] == PaymentPattern.DEFAULT.value)
        & (inv["status"] == "overdue")
    ]
    assert len(default_overdue) > 0
    paid_ids = set(ds.payments["invoice_id"])
    assert not set(default_overdue["id"]) & paid_ids


def test_dates_are_coherent() -> None:
    ds = _gen(client_count=300)
    # issue_date precedes due_date for every invoice
    assert (ds.invoices["issue_date"] < ds.invoices["due_date"]).all()
    # payments never land in the future
    assert (ds.payments["paid_date"] <= _REF).all()
