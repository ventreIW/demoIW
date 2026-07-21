"""Tests for the prioritization contract (s4.5-formula T1).

These types are the handoff to **s4.5-API (Nano)**. Their shape and units are the
contract, so the tests double as the specification he builds against.
"""

import pytest

from app.domain.value_objects.prioritized_case import (
    DEFAULT_PARETO_THRESHOLD,
    PrioritizedCase,
    PrioritizedPortfolio,
)


def _case(score: float, outstanding: float, rank: int = 1) -> PrioritizedCase:
    return PrioritizedCase(
        client_id=f"client-{rank}",
        score=score,
        outstanding=outstanding,
        rank=rank,
    )


# --- The formula ----------------------------------------------------------


def test_expected_recoverable_is_outstanding_times_probability() -> None:
    """D1: score/100 is a genuine probability, so the product is pesos."""
    assert _case(score=30.0, outstanding=100_000.0).expected_recoverable == pytest.approx(30_000.0)
    assert _case(score=90.0, outstanding=30_000.0).expected_recoverable == pytest.approx(27_000.0)


def test_trivial_balance_yields_trivial_expected_value() -> None:
    """A 95-score account owing $200 is worth $190 of attention, not a queue slot."""
    assert _case(score=95.0, outstanding=200.0).expected_recoverable == pytest.approx(190.0)


def test_expected_recoverable_is_derived_not_stored() -> None:
    """Computed from its inputs, so it cannot drift from them."""
    case = _case(score=50.0, outstanding=1_000.0)

    assert case.expected_recoverable == pytest.approx(500.0)
    with pytest.raises(Exception):
        case.expected_recoverable = 999.0  # type: ignore[misc]


def test_zero_score_yields_zero_expected_value() -> None:
    assert _case(score=0.0, outstanding=50_000.0).expected_recoverable == 0.0


def test_case_is_frozen() -> None:
    case = _case(score=50.0, outstanding=1_000.0)

    with pytest.raises(Exception):
        case.score = 99.0  # type: ignore[misc]


# --- The portfolio --------------------------------------------------------


def _portfolio() -> PrioritizedPortfolio:
    cases = [
        _case(score=30.0, outstanding=100_000.0, rank=1),  # 30,000
        _case(score=90.0, outstanding=30_000.0, rank=2),  # 27,000
        _case(score=60.0, outstanding=20_000.0, rank=3),  # 12,000
        _case(score=95.0, outstanding=200.0, rank=4),  # 190
    ]
    return PrioritizedPortfolio(cases=cases, pareto_subset=cases[:2], threshold=0.80)


def test_total_expected_recoverable() -> None:
    assert _portfolio().total_expected_recoverable == pytest.approx(69_190.0)


def test_portfolio_count() -> None:
    assert _portfolio().portfolio_count == 4


def test_subset_count() -> None:
    assert _portfolio().subset_count == 2


def test_value_share_is_the_subset_over_the_whole() -> None:
    """D3: the real figure, not an inherited 20/80 claim."""
    assert _portfolio().value_share == pytest.approx(57_000.0 / 69_190.0)


def test_summary_states_real_concentration_in_spanish() -> None:
    summary = _portfolio().summary()

    assert "2 de 4" in summary
    assert "82" in summary  # 82.4%
    assert summary.endswith(".")


def test_empty_portfolio_has_zero_share_not_a_crash() -> None:
    empty = PrioritizedPortfolio(cases=[], pareto_subset=[], threshold=0.80)

    assert empty.total_expected_recoverable == 0.0
    assert empty.value_share == 0.0
    assert empty.portfolio_count == 0


def test_default_threshold_is_documented() -> None:
    """80% is a business choice — the measured curve has no knee."""
    assert DEFAULT_PARETO_THRESHOLD == 0.80


def test_portfolio_is_frozen() -> None:
    portfolio = _portfolio()

    with pytest.raises(Exception):
        portfolio.threshold = 0.5  # type: ignore[misc]
