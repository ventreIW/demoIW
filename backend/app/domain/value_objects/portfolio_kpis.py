"""Portfolio-level KPI contract for the executive panel (RF-06.1–06.2).

**This is the handoff to s6.2 and s6.3.** The dashboard renders this aggregate and
the natural-language query layer executes its intents *against* it (ADR-008), so
the two views cannot report different numbers for the same portfolio.

Everything here is pure arithmetic over :class:`ClientKpiRow` values. No I/O, no
repositories, no model fitting — reading persisted scores is
:mod:`app.application.services.kpi_aggregate_service`'s job (ADR-009). Keeping the
arithmetic separable is what lets it be checked against figures computed by hand.

Two properties the segmentation must hold, and which the tests assert directly:

* **Totality.** Every scored client lands in exactly one bucket of every dimension,
  so per-dimension counts sum to ``client_count``. Three defects in this codebase
  were filters that quietly matched nothing while their tests passed by iterating
  an empty list — a sum assertion cannot fail that way.
* **The lowest ageing bucket starts at 0, not 1.** A scored client with no open
  invoices has a max days overdue of 0; a ``1-30`` floor would drop it from the
  breakdown and the counts would stop summing.

Sector is deliberately absent. It is an attribute of ``Scenario``, not ``Client``,
so it is constant within a scenario and would render as a single bar. See
``work/epics/e6-executive-panel/design.md`` §Gemba G2.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Final
from uuid import UUID

import numpy as np

from app.domain.enums import ScoreCategory, Sector
from app.domain.value_objects.prioritized_case import expected_recoverable

#: Segmentation dimension keys. Named constants because s6.3's ``QueryIntent``
#: vocabulary is built from the same set (ADR-008) and a typo'd string key would
#: silently produce an empty breakdown.
DAYS_OVERDUE_BUCKET: Final[str] = "days_overdue_bucket"
AMOUNT_RANGE: Final[str] = "amount_range"
SCORE_CATEGORY: Final[str] = "score_category"

#: Upper bounds of the ageing buckets, in whole days. The final bucket is open-ended.
_DAYS_OVERDUE_EDGES: Final[tuple[int, ...]] = (30, 60, 90)

#: Ageing bucket labels. Public for the same reason the dimension keys above are:
#: s6.3's ``QueryIntent`` validates ``days_overdue_bucket`` filter values against
#: this exact tuple (ADR-008), and a second copy of these strings would drift into
#: a filter that matches nothing while looking correct.
DAYS_OVERDUE_LABELS: Final[tuple[str, ...]] = ("0-30", "31-60", "61-90", "90+")


@dataclass(frozen=True)
class ClientKpiRow:
    """One scored client, reduced to what the portfolio view needs.

    ``days_overdue`` is the **maximum** across the client's open invoices, matching
    the rule ``PrioritizedCase`` established: a mean flatters a badly aged account
    by averaging it against recent invoices, and a collector triages on the oldest
    thing owed. Two definitions of "how overdue is this client" across the operator
    panel and the executive panel would be a defect the director finds first.
    """

    client_id: str
    outstanding: float
    score: float
    category: ScoreCategory
    days_overdue: int

    @property
    def expected_recoverable(self) -> float:
        return expected_recoverable(self.outstanding, self.score)


@dataclass(frozen=True)
class SegmentBucket:
    """One bar of one segmentation dimension."""

    label: str
    client_count: int
    outstanding: float
    expected_recoverable: float


@dataclass(frozen=True)
class PortfolioKpis:
    """The executive view of one scored scenario.

    ``client_count`` counts **scored** clients only, and every monetary figure is
    over the same set. ``unscored_client_count`` sits beside it rather than being
    folded in: E4 excludes clients with nothing outstanding from scoring, and a
    denominator drawn from a different population than its numerator would make
    ``recovery_rate_expected`` quietly wrong. A director who sees "271 scored, 118
    unscored" can judge coverage; one who sees only "271" cannot.
    """

    scenario_id: UUID
    scenario_name: str
    sector: Sector
    scored_at: datetime
    client_count: int
    unscored_client_count: int
    total_outstanding: float
    total_expected_recoverable: float
    collected_to_date: float
    cases_by_category: dict[ScoreCategory, int]
    segmentation: dict[str, list[SegmentBucket]]

    @property
    def recovery_rate_actual(self) -> float:
        """Share of the whole book already settled.

        Historical: it reflects payments the generator produced, so it does not
        move when a collector records a contact result during the demo. Derived
        rather than stored, so it cannot drift from the figures it comes from.
        """
        book = self.collected_to_date + self.total_outstanding
        if book == 0.0:
            return 0.0
        return self.collected_to_date / book

    @property
    def recovery_rate_expected(self) -> float:
        """Share of the *unsettled remainder* the model expects to recover.

        Not a before/after pair with :attr:`recovery_rate_actual` — the two answer
        different questions over different denominators, which is why both are
        reported and neither is labelled "recovery rate" on its own.
        """
        if self.total_outstanding == 0.0:
            return 0.0
        return self.total_expected_recoverable / self.total_outstanding


def build_portfolio_kpis(
    *,
    scenario_id: UUID,
    scenario_name: str,
    sector: Sector,
    scored_at: datetime,
    rows: list[ClientKpiRow],
    collected_to_date: float,
    unscored_client_count: int,
) -> PortfolioKpis:
    """Aggregate scored clients into the portfolio view.

    Raises ``ValueError`` on an empty portfolio rather than returning zeros. A book
    worth $0 is a legitimate answer for a fully settled scenario and an illegitimate
    one for an unscored scenario; zeros make the two indistinguishable to the reader
    (ADR-009). The caller turns this into a 409.
    """
    if not rows:
        raise ValueError(
            "portfolio has no scored clients — nothing to aggregate. "
            "Score the scenario before requesting its KPIs."
        )

    return PortfolioKpis(
        scenario_id=scenario_id,
        scenario_name=scenario_name,
        sector=sector,
        scored_at=scored_at,
        client_count=len(rows),
        unscored_client_count=unscored_client_count,
        total_outstanding=sum(row.outstanding for row in rows),
        total_expected_recoverable=sum(row.expected_recoverable for row in rows),
        collected_to_date=collected_to_date,
        cases_by_category=_count_by_category(rows),
        segmentation={
            DAYS_OVERDUE_BUCKET: _bucket_by_days_overdue(rows),
            AMOUNT_RANGE: _bucket_by_amount_range(rows),
            SCORE_CATEGORY: _bucket_by_score_category(rows),
        },
    )


def _count_by_category(rows: list[ClientKpiRow]) -> dict[ScoreCategory, int]:
    """Count per band, seeded with every member so zeros are reported.

    Built from ``ScoreCategory`` members, never from capitalised string literals —
    that comparison is the live ``?category=High`` defect on ``/prioritized``,
    where the router validates against ``{"High","Medium","Low"}`` and the enum's
    values are lowercase, so the filter matches nothing for every valid input.
    """
    counts: dict[ScoreCategory, int] = {member: 0 for member in ScoreCategory}
    for row in rows:
        counts[row.category] += 1
    return counts


def _bucket_by_days_overdue(rows: list[ClientKpiRow]) -> list[SegmentBucket]:
    """Fixed ageing bands. Every client falls in exactly one, including 0 days."""
    grouped: dict[str, list[ClientKpiRow]] = {label: [] for label in DAYS_OVERDUE_LABELS}
    for row in rows:
        grouped[_days_overdue_label(row.days_overdue)].append(row)
    return [_summarize(label, members) for label, members in grouped.items()]


def _days_overdue_label(days_overdue: int) -> str:
    for edge, label in zip(_DAYS_OVERDUE_EDGES, DAYS_OVERDUE_LABELS, strict=False):
        if days_overdue <= edge:
            return label
    return DAYS_OVERDUE_LABELS[-1]


def _bucket_by_amount_range(rows: list[ClientKpiRow]) -> list[SegmentBucket]:
    """Per-scenario quartiles of client outstanding balance.

    Fixed peso bands cannot work — invoice amounts are a generation parameter, so
    a band that segments one scenario collapses on another. Quartiles are also
    self-describing to a director ("the top quarter of accounts by balance").

    Assignment is by comparison against ``numpy.percentile`` boundaries rather than
    ``pandas.qcut``: ``qcut`` raises on duplicate bin edges, which any portfolio
    with many equal or zero balances produces. When the boundaries collapse, clients
    pile into fewer buckets and the counts still sum — a degenerate portfolio
    reported honestly rather than an error.
    """
    balances = [row.outstanding for row in rows]
    lower = min(balances)
    edges = [float(np.percentile(balances, q)) for q in (25, 50, 75)]
    labels = _amount_range_labels(lower, edges)

    grouped: dict[str, list[ClientKpiRow]] = {label: [] for label in labels}
    for row in rows:
        grouped[labels[_amount_range_index(row.outstanding, edges)]].append(row)
    return [_summarize(label, members) for label, members in grouped.items()]


def _amount_range_index(outstanding: float, edges: list[float]) -> int:
    for index, edge in enumerate(edges):
        if outstanding <= edge:
            return index
    return len(edges)


def _amount_range_labels(lower: float, edges: list[float]) -> list[str]:
    bounds = [lower, *edges]
    labels = [f"{_pesos(bounds[i])} – {_pesos(edges[i])}" for i in range(len(edges))]
    labels.append(f"> {_pesos(edges[-1])}")
    # Collapsed quartiles can produce identical labels; de-duplicate so the bucket
    # dict cannot silently merge two bands and lose the clients in one of them.
    return _uniquify(labels)


def _uniquify(labels: list[str]) -> list[str]:
    seen: dict[str, int] = {}
    unique: list[str] = []
    for label in labels:
        if label in seen:
            seen[label] += 1
            unique.append(f"{label} ({seen[label]})")
        else:
            seen[label] = 1
            unique.append(label)
    return unique


def _pesos(amount: float) -> str:
    return f"${amount:,.0f}"


def _bucket_by_score_category(rows: list[ClientKpiRow]) -> list[SegmentBucket]:
    """One bucket per ``ScoreCategory`` member, zero-count bands included."""
    grouped: dict[ScoreCategory, list[ClientKpiRow]] = {member: [] for member in ScoreCategory}
    for row in rows:
        grouped[row.category].append(row)
    return [_summarize(member.value, members) for member, members in grouped.items()]


def _summarize(label: str, members: list[ClientKpiRow]) -> SegmentBucket:
    return SegmentBucket(
        label=label,
        client_count=len(members),
        outstanding=sum(row.outstanding for row in members),
        expected_recoverable=sum(row.expected_recoverable for row in members),
    )
