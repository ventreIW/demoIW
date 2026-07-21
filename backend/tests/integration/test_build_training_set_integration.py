"""End-to-end training-set construction on real generated data (s4.2 T5).

The unit tests build DataFrames by hand, which means they exercise the shapes the
author imagined. This one runs the real ``ProceduralGenerator`` so the pipeline
meets actual dtypes, real empty-payment cases, and the true sector pattern mix.

It also pins the class balance, because s4.3's baseline and metric choice depend
on it (ADR-006 D3).
"""

import pandas as pd
import pytest

from app.adapters.dataset.procedural_generator import ProceduralGenerator
from app.application.use_cases.build_training_set import BuildTrainingSet
from app.domain.enums import Sector
from app.domain.value_objects.generation_params import GenerationParams

_REFERENCE_DATE = pd.Timestamp("2026-07-01").date()


def _scenario(client_count: int = 200, sector: Sector = Sector.RETAIL, seed: int = 42):
    params = GenerationParams(
        seed=seed,
        sector=sector,
        client_count=client_count,
        invoice_volume=4.0,
        amount_mean=10_000.0,
        amount_std=3_000.0,
        reference_date=_REFERENCE_DATE,
    )
    return ProceduralGenerator(params).generate()


def test_training_set_builds_from_a_real_generated_scenario() -> None:
    training_set = BuildTrainingSet().execute(_scenario(), seed=42)

    assert len(training_set.client_ids) > 0
    assert len(training_set.X) == len(training_set.y)
    assert len(training_set.X) == len(training_set.client_ids)


def test_no_leakage_on_real_data() -> None:
    """ADR-006 at the only boundary that ultimately matters."""
    training_set = BuildTrainingSet().execute(_scenario(), seed=42)

    for column in training_set.X.columns:
        assert "pattern" not in column
        assert column not in {"client_id", "name", "id"}


def test_split_is_disjoint_on_real_data() -> None:
    training_set = BuildTrainingSet().execute(_scenario(), seed=42)

    train = set(training_set.train_client_ids)
    test = set(training_set.test_client_ids)

    assert train & test == set()
    assert len(train) + len(test) == len(training_set.client_ids)


def test_both_classes_present_on_real_data() -> None:
    training_set = BuildTrainingSet().execute(_scenario(), seed=42)

    assert set(training_set.y_train.unique()) == {0, 1}
    assert set(training_set.y_test.unique()) == {0, 1}


def test_positive_rate_is_in_the_band_the_design_predicts() -> None:
    """ADR-006 D3 predicts roughly 0.80 positive for the retail mix.

    Asserted as a band, not a point: the exact figure depends on the sector
    weights and the seed. If this ever drifts far outside, s4.3's baseline and
    metric choice must be revisited before training anything.
    """
    training_set = BuildTrainingSet().execute(_scenario(400), seed=42)

    assert 0.65 <= training_set.positive_rate <= 0.92, (
        f"positive rate {training_set.positive_rate:.3f} is outside the band "
        "ADR-006 D3 predicts — revisit the baseline before s4.3"
    )


def test_construction_is_reproducible_for_a_fixed_seed() -> None:
    first = BuildTrainingSet().execute(_scenario(), seed=42)
    second = BuildTrainingSet().execute(_scenario(), seed=42)

    pd.testing.assert_frame_equal(first.X, second.X)
    pd.testing.assert_series_equal(first.y, second.y)
    assert first.client_ids == second.client_ids
    assert first.train_client_ids == second.train_client_ids


def test_different_scenario_seed_produces_a_different_training_set() -> None:
    """Guards the reproducibility test from passing on a constant."""
    first = BuildTrainingSet().execute(_scenario(seed=42), seed=42)
    second = BuildTrainingSet().execute(_scenario(seed=1337), seed=42)

    assert not first.X.equals(second.X)


def test_features_carry_no_nan_on_real_data() -> None:
    training_set = BuildTrainingSet().execute(_scenario(), seed=42)

    assert not training_set.X.isna().to_numpy().any()


@pytest.mark.parametrize(
    "sector",
    [Sector.RETAIL, Sector.MANUFACTURING, Sector.PROFESSIONAL_SERVICES],
)
def test_every_sector_produces_a_usable_training_set(sector: Sector) -> None:
    """Professional services skews healthy — it must still yield both classes."""
    training_set = BuildTrainingSet().execute(_scenario(300, sector=sector), seed=42)

    assert set(training_set.y.unique()) == {0, 1}
    assert 0.0 < training_set.positive_rate < 1.0


def test_partial_payers_have_outstanding_below_their_invoiced_total() -> None:
    """The gemba finding, verified against generator output rather than a fixture."""
    dataset = _scenario(300)
    partial_ids = set(
        dataset.clients.loc[dataset.clients["payment_history_pattern"] == "partial", "id"]
    )
    assert partial_ids, "generator produced no partial payers to check"

    open_invoices = dataset.invoices[dataset.invoices["status"] == "overdue"]
    paid = dataset.payments.groupby("invoice_id")["amount"].sum()
    with_partial = open_invoices[open_invoices["id"].isin(paid.index)]

    assert not with_partial.empty, "no open invoice carries a partial payment"
    for _, invoice in with_partial.iterrows():
        assert paid[invoice["id"]] < invoice["amount"]
