from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class RawDataset:
    """Procedurally generated, pre-enrichment dataset.

    Holds three related tables as pandas DataFrames. This is the raw output of
    the procedural generation layer (s3.1); LLM enrichment (s3.3) and persistence
    mapping (s3.4) consume it. Frozen to prevent mutation between generation and
    downstream consumers.
    """

    clients: pd.DataFrame
    invoices: pd.DataFrame
    payments: pd.DataFrame
