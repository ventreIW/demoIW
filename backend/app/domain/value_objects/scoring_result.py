"""Evaluation result for the collectability model (s4.3 D3).

Pure domain value object — **no modelling library imports here.** The computation
that produces it lives in :mod:`app.adapters.scoring.evaluator`, because metric
implementations come from scikit-learn and the domain must not depend on it.

The type exists to make one thing impossible: publishing a number that means
nothing. The design prototype measured ROC-AUC across five seeds, three sectors
and four scenario sizes. At n=100 it ranged **0.286 to 1.000** — worse than chance
to perfect — because ~100 clients yields roughly 60 scoreable and an ~18-row test
set. Below :data:`MIN_TEST_SET_FOR_EVALUATION` the metrics are withheld and the
status says why.
"""

from dataclasses import dataclass
from enum import StrEnum
from typing import Final

#: Below this many held-out clients, evaluation is withheld rather than reported.
MIN_TEST_SET_FOR_EVALUATION: Final[int] = 30

#: Score cutoff at which balanced accuracy is measured — the Low/Medium boundary.
#:
#: Not 0.5. With a positive class of 0.75–0.86, a 0.5 probability cutoff makes the
#: model call almost everyone collectable, collapsing balanced accuracy to ~0.5 —
#: a property of the threshold, not of the model.
DECISION_THRESHOLD: Final[float] = 40.0


class EvaluationStatus(StrEnum):
    EVALUATED = "evaluated"
    INSUFFICIENT_DATA = "insufficient_data"


@dataclass(frozen=True)
class EvaluationMetrics:
    """Held-out performance, or an explicit statement that it is unknowable.

    ``roc_auc`` and ``balanced_accuracy`` are ``None`` exactly when ``status`` is
    ``INSUFFICIENT_DATA``. ``majority_baseline`` is always populated — it is the
    context that stops a raw accuracy of 0.80 from reading as a result.
    """

    status: EvaluationStatus
    test_size: int
    majority_baseline: float
    roc_auc: float | None = None
    balanced_accuracy: float | None = None
    decision_threshold: float = DECISION_THRESHOLD
