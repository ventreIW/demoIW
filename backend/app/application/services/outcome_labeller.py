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
from app.domain.enums import InvoiceStatus, PaymentPattern
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
            # Report the statuses actually present. The previous message asserted
            # "Every invoice in this scenario is settled", which is only one of the
            # ways outstanding can be zero — and it was the wrong one for BUG-03,
            # where every invoice carried an unrecognised status and so matched
            # neither the open nor the settled branch. A status this code does not
            # know about must name itself rather than be misattributed.
            observed = dataset.invoices["status"].value_counts().to_dict()
            known = {member.value for member in InvoiceStatus}
            unknown = {value: n for value, n in observed.items() if value not in known}
            detail = (
                f" Unrecognised invoice status values present: {unknown} — these match "
                f"neither the open nor the settled branch, so their balances are invisible."
                if unknown
                else " Every invoice in this scenario is settled."
            )
            raise InsufficientOutstandingError(
                "no clients with an outstanding balance — nothing to label. "
                f"Invoice statuses observed: {observed}.{detail}"
            )

        clients = dataset.clients[dataset.clients["id"].isin(with_balance.index)]
        # Order by the generation sequence, NOT by `id`. `rng` below is seeded, so it emits
        # the same draws every run — but those draws are applied along this axis. `id` is a
        # random surrogate key assigned at persist time, so ordering by it applied a seeded
        # sequence to a randomly permuted client list: same seed, different labels, different
        # model, different scores (BUG-05, ADR-011). A seeded draw along an unseeded axis is
        # not seeded.
        order_column = "generation_index" if "generation_index" in clients.columns else "id"
        clients = clients.sort_values(order_column).reset_index(drop=True)

        rng = np.random.default_rng(self._seed)
        scales = clients["payment_history_pattern"].map(
            lambda value: PATTERN_PROFILES[PaymentPattern(value)].late_days_mean
        )
        days_to_collect = rng.exponential(scale=scales.to_numpy())

        labelled = pd.DataFrame(
            {
                "client_id": clients["id"],
                LABEL_COLUMN: (days_to_collect <= horizon_days).astype(int),
            }
        )
        # Carry the ordering key downstream. BuildTrainingSet sorts the joined frame before
        # taking a positional train/test split, and sorting *there* by the random `id` would
        # reintroduce exactly the defect fixed here, one stage later (BUG-05, ADR-011).
        if order_column in clients.columns:
            labelled[order_column] = clients[order_column]
        return labelled
