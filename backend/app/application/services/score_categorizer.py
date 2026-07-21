"""Map a 0–100 collectability score to a High / Medium / Low band (s4.3 D2).

Thresholds are **fixed absolutes**, not per-scenario quantiles. A tercile split
would guarantee evenly filled buckets, but the same client would land in a
different band depending on which portfolio it sits in, and s4.6's rescore after
contact would shift everyone's bands whenever one client changed.

The values were chosen against a measured distribution rather than by feel. On a
1000-client retail scenario the scores ran p25=40.3, p50=53.4, p75=67.5, so 40 and
70 sit close to natural quartiles and yield roughly 25% Low / 50% Medium / 25% High.
"""

from typing import Final

import pandas as pd

from app.domain.enums import ScoreCategory

#: Below this the account is Low — roughly the observed 25th percentile.
LOW_THRESHOLD: Final[float] = 40.0

#: Above this the account is High — roughly the observed 75th percentile.
HIGH_THRESHOLD: Final[float] = 70.0


def categorize(score: float) -> ScoreCategory:
    """Band a single score.

    Boundaries: ``score < 40`` is Low, ``40 <= score <= 70`` is Medium, and
    ``score > 70`` is High.
    """
    if not 0.0 <= score <= 100.0:
        raise ValueError(f"score {score} is outside the valid range 0-100")
    if score < LOW_THRESHOLD:
        return ScoreCategory.LOW
    if score > HIGH_THRESHOLD:
        return ScoreCategory.HIGH
    return ScoreCategory.MEDIUM


def categorize_series(scores: pd.Series) -> pd.Series:
    """Band a series of scores, preserving the index."""
    return scores.map(categorize)
