"""Abstract port for collectability scoring.

Keeps the application layer independent of the modelling library, the same way
``ILLMPort`` keeps it independent of any single AI provider. Nothing outside
``app.adapters.scoring`` may import ``sklearn``.

The contract deliberately speaks in pandas and plain floats rather than estimator
types, so a different implementation — a rules engine, a gradient-boosted model,
a remote service — could satisfy it without leaking its internals upward.
"""

from abc import ABC, abstractmethod

import pandas as pd

from app.domain.value_objects.training_set import TrainingSet


class IScoringPort(ABC):
    """Abstract port for fitting and applying a collectability model."""

    @abstractmethod
    def fit(self, training_set: TrainingSet) -> None:
        """Fit the model on a labelled training set."""
        ...

    @abstractmethod
    def predict_scores(self, features: pd.DataFrame) -> pd.Series:
        """Return a 0–100 collectability score per row.

        The score is ``P(collected within the horizon) * 100`` — a probability,
        not a relative index (ADR-007, s4.3 D1).
        """
        ...

    @abstractmethod
    def feature_contributions(self, features: pd.DataFrame) -> list[dict[str, float]]:
        """Per-row, per-feature contribution to the score.

        Signed: positive raises collectability, negative lowers it. s4.4 ranks
        these to produce the plain-language explanation RF-02.3 requires.
        """
        ...
