"""Tests for score categorization (s4.3 T3, design D2).

Thresholds are fixed absolutes rather than per-scenario terciles so a client's
band does not depend on who else is in the portfolio, and so s4.6's rescore after
contact moves a band only when that client actually changes.
"""

import pytest

from app.application.services.score_categorizer import (
    HIGH_THRESHOLD,
    LOW_THRESHOLD,
    categorize,
)
from app.domain.enums import ScoreCategory


def test_documented_thresholds() -> None:
    """The values the design justified against the observed distribution."""
    assert LOW_THRESHOLD == 40.0
    assert HIGH_THRESHOLD == 70.0


@pytest.mark.parametrize(
    ("score", "expected"),
    [
        (0.0, ScoreCategory.LOW),
        (39.9, ScoreCategory.LOW),
        (40.0, ScoreCategory.MEDIUM),
        (55.0, ScoreCategory.MEDIUM),
        (70.0, ScoreCategory.MEDIUM),
        (70.1, ScoreCategory.HIGH),
        (100.0, ScoreCategory.HIGH),
    ],
)
def test_categories_at_documented_thresholds(score: float, expected: ScoreCategory) -> None:
    """Boundaries included explicitly — 40 and 70 are where off-by-one lives."""
    assert categorize(score) == expected


def test_boundary_is_inclusive_at_the_bottom_of_medium() -> None:
    """A score of exactly 40 is Medium, not Low."""
    assert categorize(40.0) is ScoreCategory.MEDIUM
    assert categorize(39.999) is ScoreCategory.LOW


def test_boundary_is_exclusive_at_the_top_of_medium() -> None:
    """A score of exactly 70 is Medium, not High."""
    assert categorize(70.0) is ScoreCategory.MEDIUM
    assert categorize(70.001) is ScoreCategory.HIGH


def test_out_of_range_scores_rejected() -> None:
    """A score outside 0-100 means the scorer is broken; fail loudly."""
    with pytest.raises(ValueError, match="outside"):
        categorize(-1.0)
    with pytest.raises(ValueError, match="outside"):
        categorize(100.1)
