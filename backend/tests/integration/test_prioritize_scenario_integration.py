"""Prioritization on real scored portfolios (s4.5-formula T3).

The unit tests prove the arithmetic. This checks the queue that arithmetic
produces on generated data, across all three sectors — and pins the concentration
against what the design measured, so a change in the generator or the model
surfaces here rather than in a demo.
"""

from uuid import uuid4

import pandas as pd
import pytest

from app.adapters.dataset.procedural_generator import ProceduralGenerator
from app.application.use_cases.prioritize_scenario import PrioritizeScenario
from app.application.use_cases.score_scenario import ScoreScenario
from app.domain.enums import Sector
from app.domain.value_objects.generation_params import GenerationParams

_REFERENCE_DATE = pd.Timestamp("2026-07-01").date()


def _scoring_run(sector: Sector = Sector.RETAIL, n: int = 400, seed: int = 42):
    params = GenerationParams(
        seed=seed,
        sector=sector,
        client_count=n,
        invoice_volume=4.0,
        amount_mean=10_000.0,
        amount_std=3_000.0,
        reference_date=_REFERENCE_DATE,
    )
    dataset = ProceduralGenerator(params).generate()
    return ScoreScenario().execute(dataset, scenario_id=uuid4(), seed=seed)


# --- The queue holds together on real data --------------------------------


@pytest.mark.parametrize(
    "sector", [Sector.RETAIL, Sector.MANUFACTURING, Sector.PROFESSIONAL_SERVICES]
)
def test_every_scored_client_appears_exactly_once(sector: Sector) -> None:
    run = _scoring_run(sector=sector)

    portfolio = PrioritizeScenario().execute(run)

    ids = [case.client_id for case in portfolio.cases]
    assert len(ids) == len(set(ids)) == len(run.scores)


@pytest.mark.parametrize(
    "sector", [Sector.RETAIL, Sector.MANUFACTURING, Sector.PROFESSIONAL_SERVICES]
)
def test_ordering_is_monotonically_decreasing(sector: Sector) -> None:
    portfolio = PrioritizeScenario().execute(_scoring_run(sector=sector))

    values = [case.expected_recoverable for case in portfolio.cases]
    assert values == sorted(values, reverse=True)


def test_clients_without_outstanding_are_absent_not_ranked_last() -> None:
    """ADR-006 D4: they were never assessed, so they are not in the queue."""
    run = _scoring_run(n=400)

    portfolio = PrioritizeScenario().execute(run)

    assert portfolio.portfolio_count == len(run.scores)
    assert run.unscored_client_count > 0
    assert portfolio.portfolio_count + run.unscored_client_count == 400


# --- Concentration matches what the design measured -----------------------


@pytest.mark.parametrize(
    "sector", [Sector.RETAIL, Sector.MANUFACTURING, Sector.PROFESSIONAL_SERVICES]
)
def test_concentration_matches_measured_curve(sector: Sector) -> None:
    """The design measured ~58% of clients for 80% of value, all three sectors.

    Asserted as a band. If this drifts far, either the generator's amount
    distribution or the model has changed — and the demo's Pareto claim changes
    with it, so it should fail here rather than surprise someone live.
    """
    portfolio = PrioritizeScenario().execute(_scoring_run(sector=sector), threshold=0.80)

    subset_share = portfolio.subset_count / portfolio.portfolio_count

    assert portfolio.value_share >= 0.80
    assert 0.45 <= subset_share <= 0.70, (
        f"{sector.value}: {portfolio.subset_count} of {portfolio.portfolio_count} clients "
        f"({subset_share:.1%}) hold 80% of value — design measured ~58%"
    )


def test_top_twenty_percent_holds_far_less_than_eighty_percent() -> None:
    """Guards against anyone reintroducing a 20/80 claim this data does not support."""
    portfolio = PrioritizeScenario().execute(_scoring_run())

    top_fifth = portfolio.cases[: int(portfolio.portfolio_count * 0.2)]
    share = sum(c.expected_recoverable for c in top_fifth) / portfolio.total_expected_recoverable

    assert share < 0.55, f"top 20% hold {share:.1%} — a 20/80 claim would be closer to true"


def test_stricter_threshold_widens_the_subset() -> None:
    run = _scoring_run()

    loose = PrioritizeScenario().execute(run, threshold=0.50)
    strict = PrioritizeScenario().execute(run, threshold=0.95)

    assert strict.subset_count > loose.subset_count


# --- Reproducibility ------------------------------------------------------


def test_priority_reproducible_for_seed() -> None:
    first = PrioritizeScenario().execute(_scoring_run(seed=42))
    second = PrioritizeScenario().execute(_scoring_run(seed=42))

    assert [c.client_id for c in first.cases] == [c.client_id for c in second.cases]
    assert [c.expected_recoverable for c in first.cases] == [
        c.expected_recoverable for c in second.cases
    ]


def test_different_seed_produces_a_different_queue() -> None:
    """Guards the reproducibility test from passing on a constant."""
    first = PrioritizeScenario().execute(_scoring_run(seed=42))
    second = PrioritizeScenario().execute(_scoring_run(seed=1337))

    assert [c.client_id for c in first.cases] != [c.client_id for c in second.cases]


# --- Output shape ---------------------------------------------------------


def test_summary_reports_real_figures() -> None:
    portfolio = PrioritizeScenario().execute(_scoring_run())

    summary = portfolio.summary()

    assert str(portfolio.subset_count) in summary
    assert str(portfolio.portfolio_count) in summary
    assert "valor recuperable esperado" in summary


def test_expected_recoverable_never_exceeds_outstanding() -> None:
    """A probability cannot recover more than is owed."""
    portfolio = PrioritizeScenario().execute(_scoring_run())

    for case in portfolio.cases:
        assert case.expected_recoverable <= case.outstanding
