"""Forward-outcome labelling for the collectability model (ADR-006 D2/D4).

The generator produces a *snapshot*, not a resolved history, so there is no
"did this client eventually pay" column to learn from. This service simulates one:
for each client with an outstanding balance, it draws a time-to-collection from
that client's own behavioural profile and asks whether it lands inside the horizon.

Why this and not the obvious alternative: mapping ``payment_history_pattern``
straight to a collectability class would train the model to invert the generator —
high accuracy, no meaning. Here the label is a *future* event and the features are
the *present* snapshot, so the two are separated by a time boundary.

Note the deliberate asymmetry with :class:`FeatureExtractor`: this service **does**
read ``payment_history_pattern``, because it is the hidden truth being simulated
from. The features must never see it.
"""

import numpy as np
import pandas as pd

from app.application.services.feature_extractor import outstanding_by_client
from app.domain.enums import PaymentPattern
from app.domain.value_objects.payment_behaviour import PATTERN_PROFILES
from app.domain.value_objects.raw_dataset import RawDataset

#: Name of the produced label column.
LABEL_COLUMN = "collected_within_90d"

#: Default collection horizon in days, aligned with the ``delayed_90_plus``
#: boundary in :class:`~app.domain.enums.PaymentPattern`.
DEFAULT_HORIZON_DAYS = 90


class InsufficientOutstandingError(Exception):
    """Raised when no client has anything left to collect, so nothing is labellable."""


class OutcomeLabeller:
    """Simulates whether each client's outstanding balance is collected in time."""

    def __init__(self, seed: int) -> None:
        self._seed = seed

    def label(self, dataset: RawDataset, horizon_days: int = DEFAULT_HORIZON_DAYS) -> pd.DataFrame:
        """Return ``client_id`` and a binary label for every labellable client.

        Clients whose invoices are all settled are excluded rather than labelled:
        "will it be collected" is undefined when there is nothing to collect
        (ADR-006 D4). The caller reports the exclusion count.
        """
        outstanding = outstanding_by_client(dataset.invoices, dataset.payments)
        with_balance = outstanding[outstanding > 0.0]

        if with_balance.empty:
            raise InsufficientOutstandingError(
                "no clients with an outstanding balance — nothing to label. "
                "Every invoice in this scenario is settled."
            )

        clients = dataset.clients[dataset.clients["id"].isin(with_balance.index)]
        clients = clients.sort_values("id").reset_index(drop=True)

        rng = np.random.default_rng(self._seed)
        scales = clients["payment_history_pattern"].map(
            lambda value: PATTERN_PROFILES[PaymentPattern(value)].late_days_mean
        )
        days_to_collect = rng.exponential(scale=scales.to_numpy())

        return pd.DataFrame(
            {
                "client_id": clients["id"],
                LABEL_COLUMN: (days_to_collect <= horizon_days).astype(int),
            }
        )
