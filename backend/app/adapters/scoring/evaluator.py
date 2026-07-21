"""Held-out evaluation of collectability scores (s4.3 D3).

Lives in the scoring adapter rather than the domain because the metric
implementations come from scikit-learn, and only this package may import it.
The result it returns — :class:`EvaluationMetrics` — is a pure domain value object,
so the dependency stops here.
"""

import pandas as pd
from sklearn.metrics import balanced_accuracy_score, roc_auc_score

from app.domain.value_objects.scoring_result import (
    DECISION_THRESHOLD,
    MIN_TEST_SET_FOR_EVALUATION,
    EvaluationMetrics,
    EvaluationStatus,
)


def evaluate(y_true: pd.Series, scores: pd.Series) -> EvaluationMetrics:
    """Evaluate held-out predictions, withholding metrics when they would be noise.

    Two conditions withhold: a test set below the floor, and a test set with a
    single label class (ROC-AUC is undefined there). Both report
    ``INSUFFICIENT_DATA`` with the size, rather than raising or returning a
    misleading figure.
    """
    test_size = len(y_true)
    positive_rate = float(y_true.mean()) if test_size else 0.0
    majority_baseline = max(positive_rate, 1.0 - positive_rate)

    too_small = test_size < MIN_TEST_SET_FOR_EVALUATION
    single_class = y_true.nunique() < 2

    if too_small or single_class:
        return EvaluationMetrics(
            status=EvaluationStatus.INSUFFICIENT_DATA,
            test_size=test_size,
            majority_baseline=majority_baseline,
        )

    predictions = (scores >= DECISION_THRESHOLD).astype(int)
    return EvaluationMetrics(
        status=EvaluationStatus.EVALUATED,
        test_size=test_size,
        majority_baseline=majority_baseline,
        roc_auc=float(roc_auc_score(y_true, scores)),
        balanced_accuracy=float(balanced_accuracy_score(y_true, predictions)),
    )
