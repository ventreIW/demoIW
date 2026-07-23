"""Rank a scored portfolio and identify where its value concentrates (RF-03.1–03.2).

Two operations, both deliberately simple:

**Ranking** orders accounts by expected recoverable value — ``outstanding × score/100``
— so a 30-score account owing $100,000 outranks a 90-score account owing $30,000.
Ordering by score alone would send collectors after cheap certainties; ordering by
amount alone would send them after large uncollectables. The product is the point.

**The Pareto subset** is the *smallest* prefix of that ordering whose cumulative
expected value reaches the threshold. Minimality is the requirement: the whole
portfolio also holds ≥80% of its own value, so a filter that returned everything
would be technically correct and operationally useless.

A caution the numbers do not carry on their own: on this generator the curve has
no knee. The top 20% of clients hold ~40% of expected value and reaching 80% takes
~58% of the portfolio, because invoice amounts come from a tight normal
distribution rather than the heavy tail a real receivables book has. The threshold
is therefore a business choice, and the reported concentration is measured rather
than assumed. See `dev/parking-lot.md`.
"""

from app.domain.enums import ScoreCategory
from app.domain.value_objects.prioritized_case import (
    DEFAULT_PARETO_THRESHOLD,
    PrioritizedCase,
    PrioritizedPortfolio,
    categorize,
)


def prioritize(
    scores: dict[str, float],
    outstanding_by_client: dict[str, float],
    categories: dict[str, ScoreCategory] | None = None,
    threshold: float = DEFAULT_PARETO_THRESHOLD,
) -> PrioritizedPortfolio:
    """Rank scored clients and return the value-concentrating subset.

    Raises ``KeyError`` when a scored client has no recorded exposure. That is a
    bug upstream in scoring, not a condition to absorb — defaulting to zero would
    silently rank a real account last instead of failing where the fault is.
    """
    cases = _rank(scores, outstanding_by_client, categories)
    subset = _pareto_prefix(cases, threshold)
    return PrioritizedPortfolio(cases=cases, pareto_subset=subset, threshold=threshold)


def _rank(
    scores: dict[str, float],
    outstanding_by_client: dict[str, float],
    categories: dict[str, ScoreCategory] | None = None,
) -> list[PrioritizedCase]:
    """Order by expected recoverable value, descending."""
    missing = sorted(set(scores) - set(outstanding_by_client))
    if missing:
        raise KeyError(
            f"scored clients have no outstanding balance recorded: {missing}. "
            "Every scored client must carry exposure — see ScoringRun.outstanding_by_client."
        )

    unranked = [
        PrioritizedCase(
            client_id=client_id,
            score=scores[client_id],
            outstanding=outstanding_by_client[client_id],
            rank=0,
            category=categories.get(client_id, categorize(scores[client_id]))
            if categories
            else categorize(scores[client_id]),
        )
        for client_id in scores
    ]

    # Tie-break on client id so equal expected values never depend on dict order.
    ordered = sorted(unranked, key=lambda case: (-case.expected_recoverable, case.client_id))

    return [
        PrioritizedCase(
            client_id=case.client_id,
            score=case.score,
            outstanding=case.outstanding,
            rank=position,
            category=case.category,
        )
        for position, case in enumerate(ordered, start=1)
    ]


def _pareto_prefix(cases: list[PrioritizedCase], threshold: float) -> list[PrioritizedCase]:
    """Smallest prefix whose cumulative expected value reaches ``threshold``.

    Returns empty when there is nothing recoverable — a portfolio of zero expected
    value has no subset worth working, and reporting one would be a lie.
    """
    total = sum(case.expected_recoverable for case in cases)
    if total == 0.0:
        return []

    cumulative = 0.0
    for index, case in enumerate(cases, start=1):
        cumulative += case.expected_recoverable
        if cumulative / total >= threshold:
            return cases[:index]

    return list(cases)