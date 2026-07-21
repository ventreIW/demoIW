"""Assemble a labelled, leakage-free training set from a scenario (ADR-006).

Wires the three pieces together: extract observable features, simulate the forward
outcome, and split by client. The split is by *client* rather than by row because a
client on both sides would let the model memorise individuals and report a score
that collapses on unseen data.
"""

import numpy as np
import pandas as pd

from app.application.services.feature_extractor import FeatureExtractor
from app.application.services.outcome_labeller import (
    DEFAULT_HORIZON_DAYS,
    LABEL_COLUMN,
    InsufficientOutstandingError,
    OutcomeLabeller,
)
from app.domain.exceptions import InsufficientTrainingDataError
from app.domain.value_objects.client_features import (
    CATEGORICAL_COLUMNS,
    FEATURE_COLUMNS,
    ID_COLUMN,
)
from app.domain.value_objects.raw_dataset import RawDataset
from app.domain.value_objects.training_set import TrainingSet

#: Below this, a stratified split cannot put both classes on both sides.
MIN_CLIENTS = 20


class BuildTrainingSet:
    """Produces a :class:`TrainingSet` from a generated scenario."""

    def __init__(
        self,
        feature_extractor: FeatureExtractor | None = None,
    ) -> None:
        self._features = feature_extractor or FeatureExtractor()

    def execute(
        self,
        dataset: RawDataset,
        seed: int,
        horizon_days: int = DEFAULT_HORIZON_DAYS,
        test_fraction: float = 0.3,
    ) -> TrainingSet:
        try:
            labels = OutcomeLabeller(seed=seed).label(dataset, horizon_days=horizon_days)
        except InsufficientOutstandingError as exc:
            raise InsufficientTrainingDataError(str(exc)) from exc

        features = self._features.extract(dataset)
        total_clients = len(features)

        joined = features.merge(labels, left_on=ID_COLUMN, right_on="client_id", how="inner")
        joined = joined.sort_values(ID_COLUMN).reset_index(drop=True)

        excluded = total_clients - len(joined)
        self._guard(joined, excluded)

        client_ids = joined[ID_COLUMN].tolist()
        y = joined[LABEL_COLUMN].astype(int).reset_index(drop=True)
        X = self._design_matrix(joined)

        train_index, test_index = self._split_by_client(y, seed, test_fraction)

        return TrainingSet(
            X=X,
            y=y,
            client_ids=client_ids,
            train_index=train_index,
            test_index=test_index,
            excluded_client_count=excluded,
        )

    # -- shaping ----------------------------------------------------------

    def _design_matrix(self, joined: pd.DataFrame) -> pd.DataFrame:
        """Numeric matrix the model consumes. No ids, no forbidden columns.

        ``CATEGORICAL_COLUMNS`` is empty by design (s4.3 D5): ``sector`` is a
        per-scenario parameter written to every client, so encoding it would add a
        zero-variance column that carries no signal. Encoding is kept here, driven
        by the constant, so cross-scenario training can re-enable it by populating
        the list rather than by editing this method.
        """
        numeric = joined[FEATURE_COLUMNS].copy()
        numeric["has_partial_payments"] = numeric["has_partial_payments"].astype(int)
        if not CATEGORICAL_COLUMNS:
            return numeric.reset_index(drop=True)
        encoded = pd.get_dummies(joined[CATEGORICAL_COLUMNS], prefix=CATEGORICAL_COLUMNS)
        return pd.concat([numeric, encoded], axis=1).reset_index(drop=True)

    def _split_by_client(
        self, y: pd.Series, seed: int, test_fraction: float
    ) -> tuple[list[int], list[int]]:
        """Stratified split over client rows, so both classes land on both sides."""
        rng = np.random.default_rng(seed)
        train_index: list[int] = []
        test_index: list[int] = []

        for label_value in sorted(y.unique()):
            positions = np.flatnonzero(y.to_numpy() == label_value)
            shuffled = rng.permutation(positions)
            n_test = max(1, int(round(len(shuffled) * test_fraction)))
            n_test = min(n_test, len(shuffled) - 1)  # never starve the train side
            test_index.extend(int(i) for i in shuffled[:n_test])
            train_index.extend(int(i) for i in shuffled[n_test:])

        return sorted(train_index), sorted(test_index)

    # -- guards -----------------------------------------------------------

    def _guard(self, joined: pd.DataFrame, excluded: int) -> None:
        if len(joined) < MIN_CLIENTS:
            raise InsufficientTrainingDataError(
                f"need at least {MIN_CLIENTS} clients with an outstanding balance to "
                f"build a training set; got {len(joined)} "
                f"({excluded} excluded for having nothing outstanding)"
            )

        classes = set(joined[LABEL_COLUMN].unique())
        if len(classes) < 2:
            only = classes.pop() if classes else "none"
            raise InsufficientTrainingDataError(
                f"training set has a single label class ({LABEL_COLUMN}={only}); "
                f"both classes are needed to train. {len(joined)} clients, "
                f"{excluded} excluded for having nothing outstanding"
            )
