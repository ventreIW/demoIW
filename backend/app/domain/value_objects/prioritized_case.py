"""Prioritization contract for the operations queue (RF-03.1–03.2).

**This is the handoff to s4.5-API.** The shapes and units here are what the
endpoint serialises; treat changes as contract changes.

Units matter. ``score`` is a 0–100 collectability score which, because s4.3 kept
``predict_proba`` calibrated (no ``class_weight``), is a genuine probability of
collection within 90 days. So ``expected_recoverable`` is **money — pesos** — not
a weighted index. That is what makes the Pareto statement a claim about value
rather than about an arbitrary ranking number.

``outstanding`` already nets partial payments (s4.2), so it is the true balance
rather than the invoiced total.
"""

from dataclasses import dataclass
from typing import Final

from app.domain.enums import ScoreCategory


#: Share of expected recoverable value the Pareto subset must reach.
#:
#: A **business choice, not a property of the data.** The measured concentration
#: curve on this generator has no knee: the top 20% of clients hold ~40% of
#: expected value and reaching 80% takes ~58% of the portfolio, because invoice
#: amounts are drawn from a tight normal distribution rather than the heavy tail
#: a real receivables book has. See `dev/parking-lot.md`.
DEFAULT_PARETO_THRESHOLD: Final[float] = 0.80


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


@dataclass(frozen=True)
class PrioritizedCase:
    """One account in the collections queue.

    ``expected_recoverable`` is derived rather than stored, so it can never drift
    from the score and balance it is computed from.
    """

    client_id: str
    score: float
    outstanding: float
    rank: int
    category: ScoreCategory

    @property
    def expected_recoverable(self) -> float:
        """Outstanding balance weighted by probability of collection, in pesos."""
        return self.outstanding * self.score / 100.0


@dataclass(frozen=True)
class PrioritizedPortfolio:
    """A ranked portfolio and the subset concentrating most of its value.

    ``pareto_subset`` is the **smallest** prefix of ``cases`` whose cumulative
    expected value reaches ``threshold``. Any larger set also exceeds it, which is
    why minimality is the requirement rather than the share alone.
    """

    cases: list[PrioritizedCase]
    pareto_subset: list[PrioritizedCase]
    threshold: float = DEFAULT_PARETO_THRESHOLD

    @property
    def total_expected_recoverable(self) -> float:
        return sum(case.expected_recoverable for case in self.cases)

    @property
    def subset_expected_recoverable(self) -> float:
        return sum(case.expected_recoverable for case in self.pareto_subset)

    @property
    def portfolio_count(self) -> int:
        return len(self.cases)

    @property
    def subset_count(self) -> int:
        return len(self.pareto_subset)

    @property
    def value_share(self) -> float:
        """Share of total expected value held by the subset. 0.0 when empty."""
        total = self.total_expected_recoverable
        if total == 0.0:
            return 0.0
        return self.subset_expected_recoverable / total

    def summary(self) -> str:
        """One Spanish line stating the real concentration.

        Deliberately reports measured figures rather than an inherited "20/80"
        claim, which this portfolio does not support.
        """
        return (
            f"{self.subset_count} de {self.portfolio_count} cuentas concentran "
            f"{self.value_share:.1%} del valor recuperable esperado."
        )