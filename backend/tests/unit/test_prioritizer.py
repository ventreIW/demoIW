"""Tests for ranking and Pareto filtering (s4.5-formula T2).

The story's point in one sentence: a low-scoring account with a large balance is
worth more attention than a high-scoring account with a trivial one, and the
queue must say so.

The subtle requirement is **minimality**. "The subset holds ≥80% of value" is
satisfied by the entire portfolio, so asserting the share alone proves nothing.
`test_pareto_returns_smallest_qualifying_prefix` removes the prefix's last member
and checks the share falls below the threshold.
"""

import pytest

from app.application.services.prioritizer import prioritize
from app.domain.value_objects.prioritized_case import DEFAULT_PARETO_THRESHOLD


def _scored(**client_to_score_outstanding: tuple[float, float]):
    """Build (scores, outstanding) inputs from ``id=(score, outstanding)``."""
    scores = {cid: value[0] for cid, value in client_to_score_outstanding.items()}
    outstanding = {cid: value[1] for cid, value in client_to_score_outstanding.items()}
    return scores, outstanding


# --- Ranking --------------------------------------------------------------


def test_low_score_high_amount_outranks_high_score_low_amount() -> None:
    """The reason this story exists."""
    scores, outstanding = _scored(big_risky=(30.0, 100_000.0), small_safe=(90.0, 30_000.0))

    portfolio = prioritize(scores, outstanding)

    assert portfolio.cases[0].client_id == "big_risky"  # 30,000
    assert portfolio.cases[1].client_id == "small_safe"  # 27,000


def test_trivial_balance_does_not_lead_the_queue() -> None:
    scores, outstanding = _scored(
        trivial=(95.0, 200.0), modest=(60.0, 20_000.0), large=(30.0, 100_000.0)
    )

    portfolio = prioritize(scores, outstanding)

    assert portfolio.cases[-1].client_id == "trivial"


def test_ranks_are_sequential_from_one() -> None:
    scores, outstanding = _scored(a=(50.0, 1_000.0), b=(50.0, 2_000.0), c=(50.0, 3_000.0))

    portfolio = prioritize(scores, outstanding)

    assert [case.rank for case in portfolio.cases] == [1, 2, 3]


def test_ordering_is_by_expected_value_not_score_or_amount() -> None:
    scores, outstanding = _scored(
        top_score=(99.0, 1_000.0),  # 990
        top_amount=(10.0, 50_000.0),  # 5,000
        balanced=(70.0, 20_000.0),  # 14,000
    )

    portfolio = prioritize(scores, outstanding)

    assert [case.client_id for case in portfolio.cases] == ["balanced", "top_amount", "top_score"]


# --- Pareto: minimality is the requirement --------------------------------


def test_pareto_returns_smallest_qualifying_prefix() -> None:
    """The off-by-one guard.

    Asserting only "share >= threshold" would pass for the whole portfolio.
    Minimality is proven by removal: drop the last member and the share must fall
    below the threshold.
    """
    scores, outstanding = _scored(
        a=(100.0, 40_000.0),  # 40,000
        b=(100.0, 30_000.0),  # 30,000
        c=(100.0, 20_000.0),  # 20,000
        d=(100.0, 10_000.0),  # 10,000
    )  # total 100,000; 80% needs a+b+c = 90,000

    portfolio = prioritize(scores, outstanding, threshold=0.80)

    assert portfolio.subset_count == 3
    assert portfolio.value_share >= 0.80

    without_last = sum(c.expected_recoverable for c in portfolio.pareto_subset[:-1])
    assert without_last / portfolio.total_expected_recoverable < 0.80


def test_subset_share_meets_threshold() -> None:
    scores, outstanding = _scored(**{f"c{i}": (50.0 + i, 1_000.0 * (20 - i)) for i in range(20)})

    portfolio = prioritize(scores, outstanding, threshold=0.80)

    assert portfolio.value_share >= 0.80


def test_threshold_is_configurable() -> None:
    scores, outstanding = _scored(
        a=(100.0, 40_000.0), b=(100.0, 30_000.0), c=(100.0, 20_000.0), d=(100.0, 10_000.0)
    )

    strict = prioritize(scores, outstanding, threshold=0.95)
    loose = prioritize(scores, outstanding, threshold=0.40)

    assert strict.subset_count > loose.subset_count
    assert loose.subset_count == 1  # 40,000 / 100,000 = 40%


def test_default_threshold_applied_when_omitted() -> None:
    scores, outstanding = _scored(a=(100.0, 100.0))

    assert prioritize(scores, outstanding).threshold == DEFAULT_PARETO_THRESHOLD


# --- Degenerate portfolios ------------------------------------------------


def test_single_dominant_client_returns_alone() -> None:
    scores, outstanding = _scored(
        whale=(80.0, 1_000_000.0), minnow_a=(80.0, 1_000.0), minnow_b=(80.0, 1_000.0)
    )

    portfolio = prioritize(scores, outstanding, threshold=0.80)

    assert portfolio.subset_count == 1
    assert portfolio.pareto_subset[0].client_id == "whale"


def test_all_equal_values_does_not_return_empty() -> None:
    scores, outstanding = _scored(**{f"c{i}": (50.0, 1_000.0) for i in range(10)})

    portfolio = prioritize(scores, outstanding, threshold=0.80)

    assert portfolio.subset_count == 8  # 8/10 reaches exactly 80%
    assert portfolio.value_share >= 0.80


def test_single_client_portfolio() -> None:
    scores, outstanding = _scored(only=(50.0, 1_000.0))

    portfolio = prioritize(scores, outstanding)

    assert portfolio.subset_count == 1
    assert portfolio.value_share == pytest.approx(1.0)


def test_empty_portfolio_is_empty_not_an_error() -> None:
    portfolio = prioritize({}, {})

    assert portfolio.cases == []
    assert portfolio.pareto_subset == []
    assert portfolio.value_share == 0.0


def test_all_zero_expected_value_returns_empty_subset() -> None:
    """Nothing to prioritise when nothing is recoverable — say so, do not divide by zero."""
    scores, outstanding = _scored(a=(0.0, 10_000.0), b=(0.0, 20_000.0))

    portfolio = prioritize(scores, outstanding)

    assert portfolio.total_expected_recoverable == 0.0
    assert portfolio.value_share == 0.0


# --- Contract guards ------------------------------------------------------


def test_missing_outstanding_raises() -> None:
    """AC #8: a scored client with no exposure is a bug upstream, not a zero.

    Defaulting would silently rank a real account last.
    """
    scores = {"a": 50.0, "b": 60.0}
    outstanding = {"a": 1_000.0}

    with pytest.raises(KeyError, match="b"):
        prioritize(scores, outstanding)


def test_ties_break_deterministically() -> None:
    """Equal expected value must not depend on dict iteration order."""
    scores, outstanding = _scored(zeta=(50.0, 2_000.0), alpha=(50.0, 2_000.0), mid=(50.0, 2_000.0))

    runs = [prioritize(dict(scores), dict(outstanding)) for _ in range(5)]
    orders = [[case.client_id for case in run.cases] for run in runs]

    assert all(order == orders[0] for order in orders)


def test_every_client_appears_exactly_once() -> None:
    scores, outstanding = _scored(**{f"c{i}": (50.0, 1_000.0 * i + 1) for i in range(25)})

    portfolio = prioritize(scores, outstanding)

    ids = [case.client_id for case in portfolio.cases]
    assert len(ids) == len(set(ids)) == 25


def test_pareto_subset_is_a_prefix_of_the_ordering() -> None:
    scores, outstanding = _scored(**{f"c{i}": (50.0 + i, 1_000.0 * (30 - i)) for i in range(30)})

    portfolio = prioritize(scores, outstanding)

    assert portfolio.pareto_subset == portfolio.cases[: portfolio.subset_count]
