import inspect

import pandas as pd
import pytest
from pydantic import ValidationError

from app.application.use_cases.generate_dataset import GenerationParams
from app.domain.enums import Sector
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
