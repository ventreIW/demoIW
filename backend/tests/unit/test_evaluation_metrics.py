"""Tests for model evaluation (s4.3 T3, design D3).

The point of this module is refusing to report a number that means nothing. At
n=100 the design prototype measured ROC-AUC anywhere between 0.286 and 1.000
across seeds, because ~100 clients yields an ~18-row test set. Publishing either
figure as a quality signal would be worse than publishing none.
"""

import numpy as np
import pandas as pd
import pytest

from app.adapters.scoring.evaluator import evaluate
from app.domain.value_objects.scoring_result import (
    MIN_TEST_SET_FOR_EVALUATION,
    EvaluationStatus,
)


def _labels_and_scores(n: int, positive_rate: float = 0.8, seed: int = 42):
    rng = np.random.default_rng(seed)
    y = pd.Series((rng.uniform(size=n) < positive_rate).astype(int))
    # Scores correlated with the label, so AUC is meaningfully above chance.
    scores = pd.Series(np.where(y == 1, rng.uniform(45, 95, n), rng.uniform(5, 55, n)))
    return y, scores


def test_evaluation_reports_roc_auc_and_balanced_accuracy() -> None:
    y, scores = _labels_and_scores(200)

    metrics = evaluate(y, scores)

    assert metrics.status is EvaluationStatus.EVALUATED
    assert metrics.roc_auc is not None
    assert metrics.balanced_accuracy is not None
    assert 0.0 <= metrics.roc_auc <= 1.0


def test_small_test_set_reports_insufficient_data() -> None:
    """Below the floor, report nothing rather than noise."""
    y, scores = _labels_and_scores(18)

    metrics = evaluate(y, scores)

    assert metrics.status is EvaluationStatus.INSUFFICIENT_DATA
    assert metrics.roc_auc is None
    assert metrics.balanced_accuracy is None
    assert metrics.test_size == 18


def test_threshold_for_insufficient_data_is_documented() -> None:
    assert MIN_TEST_SET_FOR_EVALUATION == 30


def test_exactly_at_the_floor_is_evaluated() -> None:
    y, scores = _labels_and_scores(MIN_TEST_SET_FOR_EVALUATION)

    assert evaluate(y, scores).status is EvaluationStatus.EVALUATED


def test_majority_baseline_is_reported() -> None:
    """Context for the AUC — without it, 0.75 accuracy looks like a result."""
    y, scores = _labels_and_scores(200, positive_rate=0.8)

    metrics = evaluate(y, scores)

    assert metrics.majority_baseline == pytest.approx(max(y.mean(), 1 - y.mean()))


def test_balanced_accuracy_measured_at_category_cutoff_not_half() -> None:
    """D1's consequence: at a 0.5 cutoff on an 80/20 split the model calls
    everything positive, so balanced accuracy collapses to ~0.5. Measuring at the
    Low/Medium boundary reports something that reflects the model instead."""
    y, scores = _labels_and_scores(300)

    metrics = evaluate(y, scores)

    assert metrics.decision_threshold == 40.0


def test_single_class_test_set_cannot_be_scored() -> None:
    """ROC-AUC is undefined with one class present — say so, do not crash."""
    y = pd.Series([1] * 50)
    scores = pd.Series(np.linspace(10, 90, 50))

    metrics = evaluate(y, scores)

    assert metrics.status is EvaluationStatus.INSUFFICIENT_DATA
    assert metrics.roc_auc is None


def test_metrics_are_frozen() -> None:
    y, scores = _labels_and_scores(100)
    metrics = evaluate(y, scores)

    with pytest.raises(Exception):
        metrics.roc_auc = 0.99  # type: ignore[misc]


def test_perfect_separation_gives_auc_one() -> None:
    y = pd.Series([0] * 50 + [1] * 50)
    scores = pd.Series(list(np.linspace(5, 35, 50)) + list(np.linspace(65, 95, 50)))

    metrics = evaluate(y, scores)

    assert metrics.roc_auc == pytest.approx(1.0)


def test_random_scores_give_auc_near_half() -> None:
    rng = np.random.default_rng(7)
    y = pd.Series(rng.integers(0, 2, 500))
    scores = pd.Series(rng.uniform(0, 100, 500))

    metrics = evaluate(y, scores)

    assert metrics.roc_auc is not None
    assert 0.4 < metrics.roc_auc < 0.6
