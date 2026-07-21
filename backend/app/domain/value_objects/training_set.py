"""Labelled training set for the collectability model (ADR-006).

Carries the feature matrix, the labels, and — critically — the client ids behind
each split, so downstream code can prove no client appears on both sides.

Built on demand per ADR-007; nothing here is persisted.
"""

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class TrainingSet:
    """Features, labels, and the split that separates them by client.

    ``X`` excludes the client id and every forbidden column: it is exactly what
    the model sees. ``client_ids`` is kept alongside, positionally aligned, so the
    split can be audited without the identifier ever becoming a feature.
    """

    X: pd.DataFrame
    y: pd.Series
    client_ids: list[str]
    train_index: list[int]
    test_index: list[int]
    excluded_client_count: int

    @property
    def X_train(self) -> pd.DataFrame:
        return self.X.iloc[self.train_index].reset_index(drop=True)

    @property
    def X_test(self) -> pd.DataFrame:
        return self.X.iloc[self.test_index].reset_index(drop=True)

    @property
    def y_train(self) -> pd.Series:
        return self.y.iloc[self.train_index].reset_index(drop=True)

    @property
    def y_test(self) -> pd.Series:
        return self.y.iloc[self.test_index].reset_index(drop=True)

    @property
    def train_client_ids(self) -> list[str]:
        return [self.client_ids[i] for i in self.train_index]

    @property
    def test_client_ids(self) -> list[str]:
        return [self.client_ids[i] for i in self.test_index]

    @property
    def positive_rate(self) -> float:
        """Share of the positive class — s4.3's majority-class baseline (ADR-006 D3).

        Expected around 0.80, which is why raw accuracy is the wrong metric there:
        a model predicting "always collected" would score ~80% while being useless.
        """
        return float(self.y.mean())
