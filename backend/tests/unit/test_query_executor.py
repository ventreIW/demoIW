"""Intent execution over the s6.1 aggregate (s6.3 T2, ADR-008).

The executor is a pure function, which is what makes these tests exhaustive
rather than representative: every ``Metric`` × ``group_by`` cell is covered by
:class:`TestTotality`, so a branch that stops returning numbers fails loudly
instead of falling through to a default.

The fixture is built from ``s6.1-payload.json`` — the response captured with
``curl`` against a running app — not from hand-written literals. That is the
s5.1 lesson: a type or fixture derived from what the code *should* return
cannot detect that the code returns something else.

:func:`TestAgreement.test_grouped_outstanding_equals_the_dashboard_buckets` is
the load-bearing test of ADR-008's central claim. The NL answer and the
dashboard read one aggregate, so they cannot disagree — this asserts it rather
than trusting it.
"""

import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import pytest

from app.domain.enums import ScoreCategory, Sector
from app.domain.value_objects.portfolio_kpis import (
    AMOUNT_RANGE,
    DAYS_OVERDUE_BUCKET,
    SCORE_CATEGORY,
    ClientKpiRow,
    PortfolioKpis,
    build_portfolio_kpis,
)
from app.domain.value_objects.query_intent import (
    Dimension,
    Filter,
    Metric,
    QueryIntent,
)
from app.application.services.query_executor import QueryResult, execute

_PAYLOAD = (
    Path(__file__).resolve().parents[2].parent
    / "work/epics/e6-executive-panel/stories/s6.1-payload.json"
)


@pytest.fixture(scope="module")
def captured_payload() -> dict:
    """The real ``GET /{id}/kpis`` response committed by s6.1."""
    return json.loads(_PAYLOAD.read_text(encoding="utf-8"))


@pytest.fixture
def kpis() -> PortfolioKpis:
    """A portfolio with known, hand-checkable figures.

    Deliberately small and computed by hand rather than sampled: the captured
    payload proves the *shape* (see :class:`TestCapturedPayloadShape`), while
    these rows prove the *arithmetic*.

    Four clients, one per ageing band, two categories::

        A  6,000 outstanding, score 80 (high),  95 days -> "90+"
        B 20,000 outstanding, score 40 (low),   20 days -> "0-30"
        C      0 outstanding, score 90 (high),   0 days -> "0-30"
        D 10,000 outstanding, score 50 (medium),45 days -> "31-60"
    """
    rows = [
        ClientKpiRow("a", 6_000.0, 80.0, ScoreCategory.HIGH, 95),
        ClientKpiRow("b", 20_000.0, 40.0, ScoreCategory.LOW, 20),
        ClientKpiRow("c", 0.0, 90.0, ScoreCategory.HIGH, 0),
        ClientKpiRow("d", 10_000.0, 50.0, ScoreCategory.MEDIUM, 45),
    ]
    return build_portfolio_kpis(
        scenario_id=UUID("aaaaaaaa-0000-4000-8000-000000000001"),
        scenario_name="Retail Q3 (manual)",
        sector=Sector.RETAIL,
        scored_at=datetime(2026, 8, 4, 17, 4, 57, tzinfo=UTC),
        rows=rows,
        collected_to_date=4_000.0,
        unscored_client_count=0,
    )


class TestTotality:
    """Every cell of the vocabulary answers. AC3."""

    @pytest.mark.parametrize("metric", list(Metric))
    @pytest.mark.parametrize("group_by", [None, *list(Dimension)])
    def test_every_metric_by_every_dimension_returns_numbers(
        self, kpis: PortfolioKpis, metric: Metric, group_by: Dimension | None
    ) -> None:
        """Twelve cells, none unimplemented.

        The executor must be total over the enum surface — ADR-008 requires
        every combination to be either implemented or rejected at construction,
        and since the vocabulary admits all twelve, all twelve must compute.
        """
        result = execute(QueryIntent(metric=metric, group_by=group_by), kpis)

        assert isinstance(result, QueryResult)
        assert result.metric is metric
        assert result.group_by is group_by
        assert result.series, "a cell returned an empty series"
        assert all(isinstance(point.value, float) for point in result.series)

    def test_no_metric_falls_through_to_zero(self, kpis: PortfolioKpis) -> None:
        """A silent ``else: 0.0`` would satisfy the shape assertions above."""
        for metric in Metric:
            result = execute(QueryIntent(metric=metric), kpis)
            assert result.total > 0.0, f"{metric} produced 0 on a non-empty portfolio"


class TestAgreement:
    """The NL answer and the dashboard read one aggregate. AC2."""

    def test_grouped_outstanding_equals_the_dashboard_buckets(self, kpis: PortfolioKpis) -> None:
        """ADR-008's central claim, asserted rather than assumed.

        If this ever fails, the director is being shown two different numbers
        for the same portfolio — the failure mode ADR-008 was written to make
        impossible.
        """
        result = execute(
            QueryIntent(metric=Metric.OUTSTANDING, group_by=Dimension.SCORE_CATEGORY), kpis
        )

        from_dashboard = {b.label: b.outstanding for b in kpis.segmentation[SCORE_CATEGORY]}
        from_query = {p.label: p.value for p in result.series}
        assert from_query == from_dashboard

    @pytest.mark.parametrize(
        "dimension,key",
        [
            (Dimension.DAYS_OVERDUE_BUCKET, DAYS_OVERDUE_BUCKET),
            (Dimension.AMOUNT_RANGE, AMOUNT_RANGE),
            (Dimension.SCORE_CATEGORY, SCORE_CATEGORY),
        ],
    )
    def test_expected_recoverable_matches_every_dimension(
        self, kpis: PortfolioKpis, dimension: Dimension, key: str
    ) -> None:
        result = execute(QueryIntent(metric=Metric.EXPECTED_RECOVERABLE, group_by=dimension), kpis)
        expected = {b.label: b.expected_recoverable for b in kpis.segmentation[key]}
        assert {p.label: p.value for p in result.series} == expected


class TestUngroupedTotals:
    """Headline figures come from the aggregate's own fields. AC4."""

    def test_outstanding_reads_the_aggregate_total_not_a_bucket_sum(
        self, kpis: PortfolioKpis
    ) -> None:
        """A bucketing bug must not be able to move a headline number.

        Re-summing buckets would make the ungrouped total agree with a broken
        segmentation, hiding the break. Reading ``total_outstanding`` directly
        means the two can disagree — and a test can catch it.
        """
        result = execute(QueryIntent(metric=Metric.OUTSTANDING), kpis)
        assert result.total == kpis.total_outstanding == 36_000.0

    def test_expected_recoverable_reads_the_aggregate_total(self, kpis: PortfolioKpis) -> None:
        result = execute(QueryIntent(metric=Metric.EXPECTED_RECOVERABLE), kpis)
        assert result.total == kpis.total_expected_recoverable

    def test_client_count_reads_the_aggregate_total(self, kpis: PortfolioKpis) -> None:
        result = execute(QueryIntent(metric=Metric.CLIENT_COUNT), kpis)
        assert result.total == float(kpis.client_count) == 4.0

    def test_ungrouped_result_is_a_single_point(self, kpis: PortfolioKpis) -> None:
        result = execute(QueryIntent(metric=Metric.OUTSTANDING), kpis)
        assert len(result.series) == 1


class TestTotalityOfCounts:
    """s6.1's sum property, re-asserted through the query path. AC11."""

    @pytest.mark.parametrize("dimension", list(Dimension))
    def test_client_count_series_sums_to_the_portfolio(
        self, kpis: PortfolioKpis, dimension: Dimension
    ) -> None:
        """A sum assertion cannot pass vacuously.

        Three defects in this codebase were filters that matched nothing while
        their tests passed by iterating an empty list. This is the shape of
        assertion that catches that.
        """
        result = execute(QueryIntent(metric=Metric.CLIENT_COUNT, group_by=dimension), kpis)
        assert sum(p.value for p in result.series) == float(kpis.client_count)


class TestFilters:
    def test_filter_narrows_to_the_matching_bucket(self, kpis: PortfolioKpis) -> None:
        result = execute(
            QueryIntent(
                metric=Metric.OUTSTANDING,
                filters=[Filter(dimension=Dimension.SCORE_CATEGORY, value="high")],
            ),
            kpis,
        )
        high = next(b for b in kpis.segmentation[SCORE_CATEGORY] if b.label == "high")
        assert result.total == high.outstanding == 6_000.0

    def test_filter_and_group_by_compose(self, kpis: PortfolioKpis) -> None:
        result = execute(
            QueryIntent(
                metric=Metric.CLIENT_COUNT,
                group_by=Dimension.SCORE_CATEGORY,
                filters=[Filter(dimension=Dimension.SCORE_CATEGORY, value="high")],
            ),
            kpis,
        )
        assert [(p.label, p.value) for p in result.series] == [("high", 2.0)]

    def test_filter_matching_no_clients_returns_zero_not_an_empty_series(
        self, kpis: PortfolioKpis
    ) -> None:
        """An honest zero beats a vacant answer.

        "No clients are 61-90 days overdue" is a real, useful answer. An empty
        series would render as a blank chart the director cannot distinguish
        from a failure.
        """
        result = execute(
            QueryIntent(
                metric=Metric.CLIENT_COUNT,
                filters=[Filter(dimension=Dimension.DAYS_OVERDUE_BUCKET, value="61-90")],
            ),
            kpis,
        )
        assert result.total == 0.0
        assert result.series == [_zero_point("61-90")]


class TestCapturedPayloadShape:
    """The executor must handle the real aggregate, not just the tidy fixture."""

    def test_dimensions_cover_the_captured_payload(self, captured_payload: dict) -> None:
        """Guards against a dimension being added to s6.1 and missed here."""
        assert set(captured_payload["segmentation"]) == {d.value for d in Dimension}

    def test_captured_score_category_labels_are_lowercase(self, captured_payload: dict) -> None:
        """The real API returns ``"high"``. Filter validation must match that."""
        labels = {b["label"] for b in captured_payload["segmentation"][SCORE_CATEGORY]}
        assert labels == {"high", "medium", "low"}


def _zero_point(label: str):
    from app.application.services.query_executor import SeriesPoint

    return SeriesPoint(label=label, value=0.0)
