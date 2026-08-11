"""Execute a validated :class:`QueryIntent` against the portfolio aggregate (ADR-008).

**A hand-written builder over already-computed figures, not a query generator.**
Nothing here interpolates a string into a lookup: ``group_by`` selects a
segmentation key that is an enum member, and ``metric`` selects an attribute via
a ``match`` over enum members. There is no code path that accepts an
unrecognised field name because there are no field names, only enum values.

It reads the same :class:`PortfolioKpis` the dashboard renders. That is the
whole reason ADR-008 routes execution through the aggregate rather than the ORM:
the NL answer and the executive panel are not *kept* consistent by discipline,
they are incapable of disagreeing because there is one set of numbers.

Pure and synchronous — no repositories, no I/O, no ``async``. That keeps the
exhaustive ``Metric`` × ``Dimension`` test suite instant and makes the module
trivially reusable from anywhere the aggregate is already loaded.
"""

from dataclasses import dataclass

from app.domain.value_objects.portfolio_kpis import PortfolioKpis, SegmentBucket
from app.domain.value_objects.query_intent import Dimension, Metric, QueryIntent


@dataclass(frozen=True)
class SeriesPoint:
    """One label/value pair — a bar in a chart, or a row in a narrative."""

    label: str
    value: float


@dataclass(frozen=True)
class QueryResult:
    """Numbers answering one intent.

    ``series`` always holds at least one point, including when a filter matches
    nothing: "no clients are 61-90 days overdue" is a real answer, and a zero
    renders as an honest empty bar rather than a blank chart the reader cannot
    distinguish from a failure.

    This object is the **only** thing the narrator sees (design D5). It carries
    no scenario identity and no raw question, so a narrative cannot contain a
    figure that is not here.
    """

    metric: Metric
    group_by: Dimension | None
    total: float
    series: list[SeriesPoint]


def execute(intent: QueryIntent, kpis: PortfolioKpis) -> QueryResult:
    """Turn an intent into numbers drawn from ``kpis``.

    Ungrouped metrics read the aggregate's own totals rather than re-summing
    buckets. This is deliberate: a bucketing defect would otherwise move the
    headline figure in lockstep with the broken breakdown and hide itself.
    Reading the total independently means the two *can* disagree, so a test can
    notice.
    """
    if intent.group_by is None and not intent.filters:
        total = _portfolio_total(intent.metric, kpis)
        return QueryResult(
            metric=intent.metric,
            group_by=None,
            total=total,
            series=[SeriesPoint(label=_UNGROUPED_LABEL, value=total)],
        )

    dimension = intent.group_by or intent.filters[0].dimension
    buckets = _selected_buckets(intent, kpis, dimension)
    points = [SeriesPoint(label=b.label, value=_bucket_value(intent.metric, b)) for b in buckets]

    if intent.group_by is None:
        # Filtered but ungrouped: the caller asked for one number over a subset.
        return QueryResult(
            metric=intent.metric,
            group_by=None,
            total=sum(p.value for p in points),
            series=points,
        )

    return QueryResult(
        metric=intent.metric,
        group_by=intent.group_by,
        total=sum(p.value for p in points),
        series=points,
    )


#: Label for the single point of an unfiltered, ungrouped result. Empty rather
#: than a word, so the frontend and the narrator decide how to render "the whole
#: portfolio" in the user's language instead of inheriting an English literal.
_UNGROUPED_LABEL = ""


def _selected_buckets(
    intent: QueryIntent, kpis: PortfolioKpis, dimension: Dimension
) -> list[SegmentBucket]:
    """Buckets of ``dimension``, narrowed by any filters on that same dimension.

    A filter naming a *different* dimension than ``group_by`` is not supported:
    the aggregate is pre-bucketed per dimension, so it holds no cross-dimension
    cells to intersect. Rather than silently ignoring such a filter — which
    would return the unfiltered portfolio under a filtered label, the exact
    shape of the ``?category=High`` defect — the filter is applied to its own
    dimension and the grouping is refused at the caller. See
    :func:`_wanted_labels`.
    """
    buckets = kpis.segmentation[dimension.value]
    wanted = _wanted_labels(intent, dimension)
    if wanted is None:
        return list(buckets)

    selected = [b for b in buckets if b.label in wanted]
    # A filter that matches no bucket still answers, with zero.
    return selected or [
        SegmentBucket(label=label, client_count=0, outstanding=0.0, expected_recoverable=0.0)
        for label in sorted(wanted)
    ]


def _wanted_labels(intent: QueryIntent, dimension: Dimension) -> set[str] | None:
    """Labels admitted by the filters that apply to ``dimension``.

    ``None`` means "no constraint". Filters on other dimensions are dropped
    here only because :func:`execute` never constructs that combination; the
    router-level vocabulary keeps a question to a single dimension.
    """
    labels = {f.value for f in intent.filters if f.dimension is dimension}
    return labels or None


def _portfolio_total(metric: Metric, kpis: PortfolioKpis) -> float:
    """The aggregate's own headline figure for ``metric``.

    Exhaustive over ``Metric`` with no default branch: adding a member without
    handling it here is a ``mypy`` error, not a silent zero.
    """
    match metric:
        case Metric.OUTSTANDING:
            return kpis.total_outstanding
        case Metric.EXPECTED_RECOVERABLE:
            return kpis.total_expected_recoverable
        case Metric.CLIENT_COUNT:
            return float(kpis.client_count)


def _bucket_value(metric: Metric, bucket: SegmentBucket) -> float:
    """``metric`` projected out of one bucket.

    The three members map one-to-one onto ``SegmentBucket``'s three numeric
    fields — that correspondence is why the vocabulary is three metrics and not
    ADR-008's four (design D1), and it is what makes every cell of the
    ``Metric`` × ``Dimension`` grid answerable without a special case.

    ``float()`` is applied rather than assumed. ``SegmentBucket`` annotates its
    money fields as ``float``, but they are built with ``sum(...)`` over the
    bucket's members, and ``sum([])`` returns ``int`` ``0`` — so an empty bucket
    carries an ``int`` behind a ``float`` annotation. Harmless in JSON, a type
    lie in Python, and this function's own contract says ``float``.
    """
    match metric:
        case Metric.OUTSTANDING:
            return float(bucket.outstanding)
        case Metric.EXPECTED_RECOVERABLE:
            return float(bucket.expected_recoverable)
        case Metric.CLIENT_COUNT:
            return float(bucket.client_count)
