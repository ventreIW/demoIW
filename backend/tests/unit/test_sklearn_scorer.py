"""Tests for the scikit-learn collectability scorer (s4.3 T2, ADR-007).

Two of these tests exist because of a failure found while prototyping the design:
an **unscaled** pipeline does not merely converge poorly — it inverts
``pct_invoices_settled``, producing a model that looks trained while having the
domain backwards (clients who settle their invoices scored as *less* collectable).

`test_pipeline_includes_a_scaler` and `test_coefficient_directions` guard that
independently. Either alone could be satisfied by a broken pipeline.
"""

import numpy as np
import pandas as pd
import pytest

from app.adapters.scoring.sklearn_scorer import SklearnScorer
from app.domain.value_objects.client_features import FEATURE_COLUMNS
from app.domain.value_objects.training_set import TrainingSet
from app.ports.scoring_port import IScoringPort


def _training_set(n: int = 300, seed: int = 42) -> TrainingSet:
    """Synthetic features with a deliberate, known signal.

    Collectability rises with ``pct_invoices_settled`` and falls with
    ``days_overdue_max`` — the directions the real data exhibits, so coefficient
    assertions here mean the same thing they mean in production.
    """
    rng = np.random.default_rng(seed)
    settled = rng.uniform(0.0, 1.0, n)
    overdue = rng.uniform(0.0, 180.0, n)

    logit = 3.0 * settled - 0.02 * overdue - 0.5
    prob = 1.0 / (1.0 + np.exp(-logit))
    y = pd.Series((rng.uniform(size=n) < prob).astype(int))

    X = pd.DataFrame(
        {
            "days_overdue_max": overdue,
            "days_overdue_mean": overdue * 0.6,
            "outstanding_amount": rng.uniform(1_000, 50_000, n),
            "invoice_count": rng.integers(1, 10, n).astype(float),
            "avg_invoice_amount": rng.uniform(5_000, 15_000, n),
            "pct_invoices_settled": settled,
            "avg_days_late_historical": rng.uniform(0, 60, n),
            "has_partial_payments": rng.integers(0, 2, n).astype(float),
        }
    )
    index = list(range(n))
    split = int(n * 0.7)
    return TrainingSet(
        X=X,
        y=y,
        client_ids=[f"c{i:04d}" for i in index],
        train_index=index[:split],
        test_index=index[split:],
        excluded_client_count=0,
    )


# --- Contract -------------------------------------------------------------


def test_scorer_implements_the_port() -> None:
    assert isinstance(SklearnScorer(), IScoringPort)


def test_port_methods_are_abstract() -> None:
    assert IScoringPort.fit.__isabstractmethod__ is True
    assert IScoringPort.predict_scores.__isabstractmethod__ is True
    assert IScoringPort.feature_contributions.__isabstractmethod__ is True


# --- The two guards against the prototype's failure -----------------------


def test_pipeline_includes_a_scaler() -> None:
    """Unscaled is a defect, not a style choice.

    outstanding_amount is ~1e4 while pct_invoices_settled is ~1e0; without
    scaling, lbfgs fails to converge at max_iter=1000 and the coefficients come
    out with the wrong signs.
    """
    from sklearn.preprocessing import StandardScaler

    scorer = SklearnScorer()
    scorer.fit(_training_set())

    steps = [type(step) for _, step in scorer.pipeline.steps]
    assert StandardScaler in steps


def test_coefficient_directions() -> None:
    """The pipeline canary from the epic design.

    A positive coefficient on days_overdue_max means the bug is upstream in the
    labeller, not in the model.
    """
    scorer = SklearnScorer()
    scorer.fit(_training_set())

    coefficients = scorer.coefficients()

    assert coefficients["pct_invoices_settled"] > 0, "settling invoices must raise collectability"
    assert coefficients["days_overdue_max"] < 0, "being further overdue must lower it"


def test_model_converges() -> None:
    """No ConvergenceWarning — the prototype's original failure."""
    import warnings

    from sklearn.exceptions import ConvergenceWarning

    with warnings.catch_warnings():
        warnings.simplefilter("error", ConvergenceWarning)
        SklearnScorer().fit(_training_set())


# --- Score semantics ------------------------------------------------------


def test_scores_are_between_0_and_100() -> None:
    ts = _training_set()
    scorer = SklearnScorer()
    scorer.fit(ts)

    scores = scorer.predict_scores(ts.X)

    assert scores.min() >= 0.0
    assert scores.max() <= 100.0
    assert len(scores) == len(ts.X)


def test_no_class_weight_is_applied() -> None:
    """D1: class_weight='balanced' would break the score's meaning.

    Without it, predict_proba remains a calibrated estimate, so a score of 34
    means 'roughly 34% likely to be collected within 90 days'. With it, the score
    becomes a relative index and the executive panel loses its interpretation.
    """
    scorer = SklearnScorer()
    scorer.fit(_training_set())

    assert scorer.pipeline.named_steps["logisticregression"].class_weight is None


def test_scores_track_probability() -> None:
    """A client with strong signals must outscore one with weak signals."""
    ts = _training_set()
    scorer = SklearnScorer()
    scorer.fit(ts)

    strong = pd.DataFrame(
        [
            {
                "days_overdue_max": 5.0,
                "days_overdue_mean": 3.0,
                "outstanding_amount": 5_000.0,
                "invoice_count": 6.0,
                "avg_invoice_amount": 10_000.0,
                "pct_invoices_settled": 0.95,
                "avg_days_late_historical": 2.0,
                "has_partial_payments": 0.0,
            }
        ]
    )
    weak = strong.copy()
    weak.loc[0, "days_overdue_max"] = 170.0
    weak.loc[0, "pct_invoices_settled"] = 0.05

    assert scorer.predict_scores(strong)[0] > scorer.predict_scores(weak)[0]


def test_scores_are_deterministic() -> None:
    ts = _training_set()

    first = SklearnScorer()
    first.fit(ts)
    second = SklearnScorer()
    second.fit(ts)

    np.testing.assert_allclose(first.predict_scores(ts.X), second.predict_scores(ts.X))


# --- Contributions (input for s4.4) ---------------------------------------


def test_feature_contributions_shape() -> None:
    ts = _training_set()
    scorer = SklearnScorer()
    scorer.fit(ts)

    contributions = scorer.feature_contributions(ts.X.head(3))

    assert len(contributions) == 3
    for row in contributions:
        assert set(row) == set(FEATURE_COLUMNS)


def test_contribution_sign_follows_coefficient_and_deviation() -> None:
    """A high-overdue client must get a negative contribution from that feature."""
    ts = _training_set()
    scorer = SklearnScorer()
    scorer.fit(ts)

    extreme = ts.X.copy()
    extreme.loc[extreme.index[0], "days_overdue_max"] = 1_000.0

    contribution = scorer.feature_contributions(extreme.head(1))[0]["days_overdue_max"]

    assert contribution < 0


# --- Guards ---------------------------------------------------------------


def test_predict_before_fit_raises() -> None:
    with pytest.raises(RuntimeError, match="not fitted"):
        SklearnScorer().predict_scores(_training_set().X)
