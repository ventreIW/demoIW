"""Portfolio KPI arithmetic and segmentation (s6.1 T1).

Every figure here is checked against a number computed by hand in
``s6.1-story.md`` §Examples, not against the implementation's own output.

The load-bearing test is :func:`test_bucket_counts_sum_to_client_count`. Three
defects in this codebase were filters that returned nothing while their tests
passed, because each asserted inside a loop over an empty list (s5.1's
``days_overdue`` filter, and ``?category=High``, still live). A sum assertion
cannot pass vacuously.
"""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.domain.enums import ScoreCategory, Sector
from app.domain.value_objects.portfolio_kpis import (
    AMOUNT_RANGE,
    DAYS_OVERDUE_BUCKET,
    SCORE_CATEGORY,
    ClientKpiRow,
    build_portfolio_kpis,
)
from app.domain.value_objects.prioritized_case import (
    PrioritizedCase,
    expected_recoverable,
)

# The worked example from s6.1-story.md:
#   A — 10,000 open with 4,000 paid -> 6,000 outstanding, score 80, 95 days overdue
#   B — 20,000 open, nothing paid                        , score 40, 20 days overdue
#   C — 5,000 settled -> 0 outstanding                   , score 90,  0 days overdue
_A = ClientKpiRow(
    client_id="a", outstanding=6_000.0, score=80.0, category=ScoreCategory.HIGH, days_overdue=95
)
_B = ClientKpiRow(
    client_id="b", outstanding=20_000.0, score=40.0, category=ScoreCategory.LOW, days_overdue=20
)
_C = ClientKpiRow(
    client_id="c", outstanding=0.0, score=90.0, category=ScoreCategory.HIGH, days_overdue=0
)


def _kpis(
    rows: list[ClientKpiRow],
    *,
    collected_to_date: float = 5_000.0,
    unscored_client_count: int = 0,
):
    return build_portfolio_kpis(
        scenario_id=uuid4(),
        scenario_name="Retail Q3",
        sector=Sector.RETAIL,
        scored_at=datetime(2026, 8, 4, 18, 22, 41, tzinfo=UTC),
        rows=rows,
        collected_to_date=collected_to_date,
        unscored_client_count=unscored_client_count,
    )


# -- the shared formula (design D2) ------------------------------------------


def test_expected_recoverable_is_a_reusable_function() -> None:
    """The queue and the dashboard must not hold two expressions for money."""
    assert expected_recoverable(6_000.0, 80.0) == pytest.approx(4_800.0)
    assert expected_recoverable(20_000.0, 40.0) == pytest.approx(8_000.0)
    assert expected_recoverable(50_000.0, 0.0) == 0.0


def test_prioritized_case_delegates_to_the_shared_function() -> None:
    """The extraction is asserted, not assumed — one call site, swept."""
    case = PrioritizedCase(
        client_id="a",
        client_name="Acme",
        score=80.0,
        outstanding=6_000.0,
        days_overdue=95,
        rank=1,
        category=ScoreCategory.HIGH,
    )
    assert case.expected_recoverable == expected_recoverable(6_000.0, 80.0)


# -- headline figures --------------------------------------------------------


def test_worked_example_totals() -> None:
    kpis = _kpis([_A, _B, _C])

    assert kpis.client_count == 3
    assert kpis.total_outstanding == pytest.approx(26_000.0)
    assert kpis.total_expected_recoverable == pytest.approx(12_800.0)
    assert kpis.collected_to_date == pytest.approx(5_000.0)


def test_worked_example_recovery_rates() -> None:
    kpis = _kpis([_A, _B, _C])

    # settled share of the whole book: 5,000 / (5,000 + 26,000)
    assert kpis.recovery_rate_actual == pytest.approx(0.16129, rel=1e-4)
    # what the model expects from the unsettled remainder: 12,800 / 26,000
    assert kpis.recovery_rate_expected == pytest.approx(0.49231, rel=1e-4)


def test_partial_payment_is_neither_outstanding_nor_collected() -> None:
    """A's 4,000 sits against an invoice that is still open.

    Counting it as collected inflates the recovery rate; ignoring the partial
    payment overstates exposure by 4,000.
    """
    kpis = _kpis([_A])

    assert kpis.total_outstanding == pytest.approx(6_000.0)
    assert kpis.total_expected_recoverable == pytest.approx(4_800.0)


def test_unscored_clients_are_counted_not_hidden() -> None:
    """Coverage must be visible — see design D3."""
    kpis = _kpis([_A, _B, _C], unscored_client_count=118)

    assert kpis.client_count == 3
    assert kpis.unscored_client_count == 118


# -- categories --------------------------------------------------------------


def test_cases_by_category_carries_every_member_including_zero() -> None:
    kpis = _kpis([_A, _B, _C])

    assert kpis.cases_by_category == {
        ScoreCategory.HIGH: 2,
        ScoreCategory.MEDIUM: 0,
        ScoreCategory.LOW: 1,
    }


def test_category_counts_are_keyed_by_enum_members() -> None:
    """Not by capitalised literals — that is the live ?category=High defect."""
    kpis = _kpis([_A, _B, _C])

    assert set(kpis.cases_by_category) == set(ScoreCategory)
    assert sum(kpis.cases_by_category.values()) == kpis.client_count


# -- segmentation ------------------------------------------------------------


@pytest.mark.parametrize("dimension", [DAYS_OVERDUE_BUCKET, AMOUNT_RANGE, SCORE_CATEGORY])
def test_bucket_counts_sum_to_client_count(dimension: str) -> None:
    """Every scored client lands in exactly one bucket of every dimension.

    This is the assertion that cannot pass vacuously.
    """
    rows = [_A, _B, _C]
    kpis = _kpis(rows)

    buckets = kpis.segmentation[dimension]
    assert sum(b.client_count for b in buckets) == kpis.client_count == len(rows)


@pytest.mark.parametrize("dimension", [DAYS_OVERDUE_BUCKET, AMOUNT_RANGE, SCORE_CATEGORY])
def test_bucket_money_sums_to_portfolio_money(dimension: str) -> None:
    kpis = _kpis([_A, _B, _C])

    buckets = kpis.segmentation[dimension]
    assert sum(b.outstanding for b in buckets) == pytest.approx(kpis.total_outstanding)
    assert sum(b.expected_recoverable for b in buckets) == pytest.approx(
        kpis.total_expected_recoverable
    )


def test_all_three_dimensions_are_present() -> None:
    kpis = _kpis([_A, _B, _C])

    assert set(kpis.segmentation) == {DAYS_OVERDUE_BUCKET, AMOUNT_RANGE, SCORE_CATEGORY}


def test_client_with_nothing_overdue_lands_in_the_lowest_bucket() -> None:
    """C has no open invoice, so its max days overdue is 0.

    The lowest bucket starts at 0 precisely so C is not dropped — a 1-30 floor
    would silently lose it from the breakdown.
    """
    kpis = _kpis([_C])

    buckets = {b.label: b.client_count for b in kpis.segmentation[DAYS_OVERDUE_BUCKET]}
    assert buckets["0-30"] == 1
    assert sum(buckets.values()) == 1


def test_days_overdue_buckets_split_at_their_boundaries() -> None:
    rows = [
        ClientKpiRow("w", 100.0, 50.0, ScoreCategory.MEDIUM, days_overdue=30),
        ClientKpiRow("x", 100.0, 50.0, ScoreCategory.MEDIUM, days_overdue=31),
        ClientKpiRow("y", 100.0, 50.0, ScoreCategory.MEDIUM, days_overdue=90),
        ClientKpiRow("z", 100.0, 50.0, ScoreCategory.MEDIUM, days_overdue=91),
    ]
    kpis = _kpis(rows)

    counts = {b.label: b.client_count for b in kpis.segmentation[DAYS_OVERDUE_BUCKET]}
    assert counts == {"0-30": 1, "31-60": 1, "61-90": 1, "90+": 1}


def test_score_category_buckets_use_enum_values_as_labels() -> None:
    kpis = _kpis([_A, _B, _C])

    labels = {b.label for b in kpis.segmentation[SCORE_CATEGORY]}
    assert labels == {"high", "medium", "low"}


# -- degenerate portfolios ---------------------------------------------------


def test_all_equal_balances_do_not_lose_clients() -> None:
    """Collapsed quartile edges are why this uses percentile comparison, not qcut."""
    rows = [
        ClientKpiRow(str(i), 5_000.0, 60.0, ScoreCategory.MEDIUM, days_overdue=10) for i in range(8)
    ]
    kpis = _kpis(rows)

    for dimension in (DAYS_OVERDUE_BUCKET, AMOUNT_RANGE, SCORE_CATEGORY):
        buckets = kpis.segmentation[dimension]
        assert sum(b.client_count for b in buckets) == 8


def test_zero_outstanding_portfolio_returns_zero_rates_not_a_division_error() -> None:
    rows = [ClientKpiRow("c", 0.0, 90.0, ScoreCategory.HIGH, days_overdue=0)]
    kpis = _kpis(rows, collected_to_date=0.0)

    assert kpis.total_outstanding == 0.0
    assert kpis.recovery_rate_actual == 0.0
    assert kpis.recovery_rate_expected == 0.0


def test_single_client_portfolio() -> None:
    kpis = _kpis([_B])

    assert kpis.client_count == 1
    for dimension in (DAYS_OVERDUE_BUCKET, AMOUNT_RANGE, SCORE_CATEGORY):
        assert sum(b.client_count for b in kpis.segmentation[dimension]) == 1


def test_empty_portfolio_is_not_constructible_as_a_silent_zero() -> None:
    """An unscored book and a settled book must not look alike (ADR-009)."""
    with pytest.raises(ValueError, match="no scored clients"):
        _kpis([])
