"""scikit-learn implementation of the collectability scorer (ADR-007).

`StandardScaler` + `LogisticRegression`, trained on demand per scenario with no
persisted artifact.

**The scaler is mandatory, not stylistic.** ``outstanding_amount`` is on the order
of 10⁴ while ``pct_invoices_settled`` is on the order of 10⁰. Prototyping this
design without scaling produced two failures at once: ``lbfgs`` never converged at
``max_iter=1000``, *and* the coefficient on ``pct_invoices_settled`` came out
negative — a model that looks trained while asserting that clients who settle
their invoices are less collectable. Two tests guard this independently.

**No ``class_weight``** (s4.3 D1). The positive class runs at 0.75–0.86, so
balancing would improve balanced accuracy at a 0.5 cutoff — at the cost of
``predict_proba`` no longer estimating anything real. The score is meant to be read
as a probability, so calibration wins and the quality gate uses ROC-AUC, which is
threshold-free.

This module is the only place in the codebase permitted to import ``sklearn``.
"""

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline, make_pipeline
from sklearn.preprocessing import StandardScaler

from app.domain.value_objects.training_set import TrainingSet
from app.ports.scoring_port import IScoringPort

#: lbfgs converges well within this once features are scaled.
MAX_ITER = 1000


class SklearnScorer(IScoringPort):
    """Logistic-regression collectability scorer over scaled features."""

    def __init__(self) -> None:
        self._pipeline: Pipeline | None = None
        self._feature_names: list[str] = []

    @property
    def pipeline(self) -> Pipeline:
        """The fitted pipeline. Raises if `fit` has not been called."""
        if self._pipeline is None:
            raise RuntimeError("scorer is not fitted — call fit() first")
        return self._pipeline

    def fit(self, training_set: TrainingSet) -> None:
        self._feature_names = list(training_set.X_train.columns)
        pipeline = make_pipeline(
            StandardScaler(),
            LogisticRegression(max_iter=MAX_ITER),
        )
        pipeline.fit(training_set.X_train, training_set.y_train)
        self._pipeline = pipeline

    def predict_scores(self, features: pd.DataFrame) -> pd.Series:
        probabilities = self.pipeline.predict_proba(features[self._feature_names])[:, 1]
        return pd.Series(probabilities * 100.0, index=features.index, name="score")

    def feature_contributions(self, features: pd.DataFrame) -> list[dict[str, float]]:
        """Signed contribution of each feature, in scaled space.

        For a linear model the log-odds decompose exactly:
        ``contribution_i = coef_i * (x_i - mean_i) / scale_i``. Because it is exact
        rather than approximate, s4.4 can explain a score without a second library.
        """
        scaler: StandardScaler = self.pipeline.named_steps["standardscaler"]
        model: LogisticRegression = self.pipeline.named_steps["logisticregression"]

        ordered = features[self._feature_names]
        scaled = scaler.transform(ordered)
        contributions = scaled * model.coef_[0]

        return [
            {name: float(value) for name, value in zip(self._feature_names, row, strict=True)}
            for row in contributions
        ]

    def coefficients(self) -> dict[str, float]:
        """Fitted coefficients by feature name — inspectable for sanity checks.

        ``days_overdue_max`` must be negative and ``pct_invoices_settled`` positive.
        A positive ``days_overdue_max`` means the bug is upstream in the labeller,
        not in the model.
        """
        model: LogisticRegression = self.pipeline.named_steps["logisticregression"]
        return {
            name: float(coefficient)
            for name, coefficient in zip(self._feature_names, model.coef_[0], strict=True)
        }

    def score_distribution(self, features: pd.DataFrame) -> dict[str, float]:
        """Percentiles of the score distribution, for threshold justification."""
        scores = self.predict_scores(features)
        return {f"p{q}": float(np.percentile(scores, q)) for q in (0, 25, 50, 75, 100)}
