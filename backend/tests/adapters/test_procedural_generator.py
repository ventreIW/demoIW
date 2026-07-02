import inspect

import pandas as pd
import pytest
from pydantic import ValidationError

from app.adapters.dataset.procedural_generator import ProceduralGenerator
from app.application.use_cases.generate_dataset import GenerationParams
from app.domain.enums import PaymentPattern, Sector
from app.domain.value_objects.raw_dataset import RawDataset
from app.ports.dataset_port import IDatasetPort


def _params(**overrides: object) -> GenerationParams:
    base: dict[str, object] = {
        "seed": 42,
        "sector": Sector.MANUFACTURING,
        "client_count": 50,
        "invoice_volume": 4.0,
        "amount_mean": 10_000.0,
        "amount_std": 3_000.0,
        "days_overdue_lambda": 30.0,
        "overdue_rate": 0.30,
    }
    base.update(overrides)
    return GenerationParams(**base)  # type: ignore[arg-type]


# --- T1: contract tests --------------------------------------------------


def test_generation_params_rejects_nonpositive_client_count() -> None:
    with pytest.raises(ValidationError):
        _params(client_count=0)


def test_generation_params_rejects_overdue_rate_out_of_range() -> None:
    with pytest.raises(ValidationError):
        _params(overdue_rate=1.5)


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


# --- T2: statistical / behavioural tests ---------------------------------


def test_determinism() -> None:
    a = ProceduralGenerator(_params()).generate()
    b = ProceduralGenerator(_params()).generate()
    pd.testing.assert_frame_equal(a.clients, b.clients)
    pd.testing.assert_frame_equal(a.invoices, b.invoices)
    pd.testing.assert_frame_equal(a.payments, b.payments)


def test_client_count_matches_params() -> None:
    ds = ProceduralGenerator(_params(client_count=37)).generate()
    assert ds.clients.shape[0] == 37


def test_amounts_positive() -> None:
    ds = ProceduralGenerator(_params(client_count=200)).generate()
    assert (ds.invoices["amount"] > 0).all()


def test_amount_mean_within_tolerance() -> None:
    ds = ProceduralGenerator(
        _params(client_count=400, invoice_volume=6.0, amount_mean=10_000.0, amount_std=3_000.0)
    ).generate()
    sample_mean = float(ds.invoices["amount"].mean())
    assert 0.85 * 10_000.0 <= sample_mean <= 1.15 * 10_000.0


def test_overdue_rate_within_tolerance() -> None:
    ds = ProceduralGenerator(
        _params(client_count=500, invoice_volume=6.0, overdue_rate=0.30)
    ).generate()
    overdue_fraction = float((ds.invoices["status"] == "overdue").mean())
    assert abs(overdue_fraction - 0.30) <= 0.05


def test_payment_row_per_settled_invoice() -> None:
    ds = ProceduralGenerator(_params(client_count=300)).generate()
    settled_ids = set(ds.invoices.loc[ds.invoices["status"] == "paid", "id"])
    payment_invoice_ids = set(ds.payments["invoice_id"])
    assert settled_ids <= payment_invoice_ids


def test_sector_weighting_manufacturing_slower_than_retail() -> None:
    manu = ProceduralGenerator(_params(sector=Sector.MANUFACTURING, client_count=1000)).generate()
    retail = ProceduralGenerator(_params(sector=Sector.RETAIL, client_count=1000)).generate()
    manu_slow = float((manu.clients["payment_history_pattern"] == PaymentPattern.DELAYED_30).mean())
    retail_slow = float(
        (retail.clients["payment_history_pattern"] == PaymentPattern.DELAYED_30).mean()
    )
    assert manu_slow > retail_slow
