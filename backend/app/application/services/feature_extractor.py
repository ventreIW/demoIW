"""Derive client-level model features from a generated scenario (ADR-006).

Consumes a :class:`RawDataset` snapshot and produces exactly one row per client.
Every feature is an aggregate over *observable* invoices and payments — nothing
here reads the client's ``payment_history_pattern``, which is the hidden cause
that generated the data (see ``client_features.FORBIDDEN_COLUMNS``).

Two subtleties, both found by reading the generator rather than the schema:

* **Partial payers** emit a payment smaller than the invoice on an invoice still
  marked ``overdue``. Outstanding must net those off, or exposure is overstated
  for the very cohort a collections model exists to rank.
* **Historical lateness is not stored.** ``days_overdue`` is 0 on settled
  invoices, so lateness must be derived from ``paid_date - due_date`` joined
  through ``invoice_id``.
"""

import pandas as pd

from app.domain.value_objects.client_features import (
    CATEGORICAL_COLUMNS,
    FEATURE_COLUMNS,
    FORBIDDEN_COLUMNS,
    ID_COLUMN,
)
from app.domain.value_objects.raw_dataset import RawDataset

_OPEN_STATUS = "overdue"
_SETTLED_STATUS = "paid"

#: Column holding the client identifier in ``RawDataset.clients``.
ID_COLUMN_SOURCE = "id"


def outstanding_by_client(invoices: pd.DataFrame, payments: pd.DataFrame) -> pd.Series:
    """Unsettled balance per client, net of partial payments.

    Shared with :mod:`app.application.services.outcome_labeller`, which needs the
    same notion of "has something to collect" to decide who can be labelled at all
    (ADR-006 D4). Two implementations would drift apart silently.
    """
    open_invoices = invoices[invoices["status"] == _OPEN_STATUS]
    if open_invoices.empty:
        return pd.Series(dtype=float)

    paid = _paid_amount_per_invoice(open_invoices, payments)
    balance = (open_invoices["amount"] - paid).clip(lower=0.0)
    return balance.groupby(open_invoices["client_id"]).sum()


def _paid_amount_per_invoice(invoices: pd.DataFrame, payments: pd.DataFrame) -> pd.Series:
    """Total paid against each invoice, aligned to ``invoices``' index."""
    if payments.empty:
        return pd.Series(0.0, index=invoices.index)
    totals = payments.groupby("invoice_id")["amount"].sum()
    return invoices["id"].map(totals).fillna(0.0)


class FeatureExtractor:
    """Turns a ``RawDataset`` snapshot into a client-level feature frame."""

    def extract(self, dataset: RawDataset) -> pd.DataFrame:
        clients = dataset.clients
        invoices = dataset.invoices
        payments = dataset.payments

        base = clients[[ID_COLUMN_SOURCE, *CATEGORICAL_COLUMNS]].rename(
            columns={ID_COLUMN_SOURCE: ID_COLUMN}
        )

        if invoices.empty:
            features = base.copy()
            for column in FEATURE_COLUMNS:
                features[column] = 0.0
            features["has_partial_payments"] = False
            features["invoice_count"] = 0
            return self._finalize(features)

        paid_per_invoice = self._paid_per_invoice(invoices, payments)
        enriched = invoices.merge(paid_per_invoice, on="id", how="left")
        enriched["paid_amount"] = enriched["paid_amount"].fillna(0.0)

        per_client = base.merge(
            self._aggregate(enriched, payments),
            left_on=ID_COLUMN,
            right_on="client_id_agg",
            how="left",
        ).drop(columns=["client_id_agg"], errors="ignore")

        return self._finalize(per_client)

    # -- aggregation ------------------------------------------------------

    def _paid_per_invoice(self, invoices: pd.DataFrame, payments: pd.DataFrame) -> pd.DataFrame:
        """Total paid against each invoice. Empty payments still yields the column."""
        if payments.empty:
            return pd.DataFrame({"id": invoices["id"], "paid_amount": 0.0})
        totals = payments.groupby("invoice_id", as_index=False)["amount"].sum()
        return totals.rename(columns={"invoice_id": "id", "amount": "paid_amount"})

    def _aggregate(self, invoices: pd.DataFrame, payments: pd.DataFrame) -> pd.DataFrame:
        open_invoices = invoices[invoices["status"] == _OPEN_STATUS]
        settled = invoices[invoices["status"] == _SETTLED_STATUS]

        grouped = invoices.groupby("client_id")
        result = pd.DataFrame(
            {
                "client_id_agg": grouped.size().index,
                "invoice_count": grouped.size().to_numpy(),
                "avg_invoice_amount": grouped["amount"].mean().to_numpy(),
            }
        )

        result = result.merge(self._open_aggregates(open_invoices), on="client_id_agg", how="left")
        result = result.merge(
            self._settled_aggregates(settled, invoices), on="client_id_agg", how="left"
        )
        result = result.merge(
            self._partial_payment_flag(open_invoices), on="client_id_agg", how="left"
        )
        result = result.merge(
            self._historical_lateness(settled, payments), on="client_id_agg", how="left"
        )
        return result

    def _open_aggregates(self, open_invoices: pd.DataFrame) -> pd.DataFrame:
        if open_invoices.empty:
            return pd.DataFrame(
                columns=[
                    "client_id_agg",
                    "days_overdue_max",
                    "days_overdue_mean",
                    "outstanding_amount",
                ]
            )
        grouped = open_invoices.groupby("client_id")
        balance = (open_invoices["amount"] - open_invoices["paid_amount"]).clip(lower=0.0)
        outstanding = balance.groupby(open_invoices["client_id"]).sum()
        return pd.DataFrame(
            {
                "client_id_agg": grouped.size().index,
                "days_overdue_max": grouped["days_overdue"].max().to_numpy(),
                "days_overdue_mean": grouped["days_overdue"].mean().to_numpy(),
                "outstanding_amount": outstanding.to_numpy(),
            }
        )

    def _settled_aggregates(self, settled: pd.DataFrame, invoices: pd.DataFrame) -> pd.DataFrame:
        totals = invoices.groupby("client_id").size()
        settled_counts = settled.groupby("client_id").size() if not settled.empty else None
        pct = (
            (settled_counts / totals).fillna(0.0)
            if settled_counts is not None
            else pd.Series(0.0, index=totals.index)
        )
        pct = pct.reindex(totals.index).fillna(0.0)
        return pd.DataFrame({"client_id_agg": pct.index, "pct_invoices_settled": pct.to_numpy()})

    def _partial_payment_flag(self, open_invoices: pd.DataFrame) -> pd.DataFrame:
        """A partial payer has money against an invoice that is still open."""
        if open_invoices.empty:
            return pd.DataFrame(columns=["client_id_agg", "has_partial_payments"])
        has_partial = open_invoices["paid_amount"] > 0.0
        flag = has_partial.groupby(open_invoices["client_id"]).any()
        return pd.DataFrame({"client_id_agg": flag.index, "has_partial_payments": flag.to_numpy()})

    def _historical_lateness(self, settled: pd.DataFrame, payments: pd.DataFrame) -> pd.DataFrame:
        """Mean ``paid_date - due_date`` over settled invoices, in days."""
        empty = pd.DataFrame(columns=["client_id_agg", "avg_days_late_historical"])
        if settled.empty or payments.empty:
            return empty

        joined = settled.merge(
            payments[["invoice_id", "paid_date"]], left_on="id", right_on="invoice_id", how="inner"
        )
        if joined.empty:
            return empty

        days_late = (
            pd.to_datetime(joined["paid_date"]) - pd.to_datetime(joined["due_date"])
        ).dt.days.clip(lower=0)
        mean_late = days_late.groupby(joined["client_id"]).mean()
        return pd.DataFrame(
            {"client_id_agg": mean_late.index, "avg_days_late_historical": mean_late.to_numpy()}
        )

    # -- shaping ----------------------------------------------------------

    def _finalize(self, features: pd.DataFrame) -> pd.DataFrame:
        """Fill gaps with zeros, enforce dtypes, and assert the leakage guard."""
        for column in FEATURE_COLUMNS:
            if column not in features.columns:
                features[column] = 0.0

        # Cast before filling: fillna on an object-dtype column silently downcasts,
        # which pandas deprecates and will change behaviour on.
        features["has_partial_payments"] = (
            features["has_partial_payments"]
            .map(lambda value: bool(value) if pd.notna(value) else False)
            .astype(bool)
        )
        numeric = [c for c in FEATURE_COLUMNS if c != "has_partial_payments"]
        features[numeric] = features[numeric].astype(float).fillna(0.0)
        features["invoice_count"] = features["invoice_count"].astype(int)

        ordered = features[[ID_COLUMN, *CATEGORICAL_COLUMNS, *FEATURE_COLUMNS]].reset_index(
            drop=True
        )

        leaked = FORBIDDEN_COLUMNS & set(ordered.columns)
        if leaked:  # pragma: no cover — structural guard, not a runtime path
            raise AssertionError(f"leakage: {sorted(leaked)} must never reach the model (ADR-006)")
        return ordered
