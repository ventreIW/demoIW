"""Decide which factors explain a collectability score, and in what order (s4.4).

Turns the model's per-feature contributions into a short, ranked list of business
drivers. Phrasing is a separate concern.

Three rules, each measured rather than assumed (see `s4.4-design.md`):

1. **Group before ranking.** Features mapping to the same business factor are
   summed *first*. Ranking grouped features would let ageing lose a slot it had
   won, because its weight is split across two measurements — the presentational
   twin of the collinearity that destabilised s4.3's coefficients.
2. **Materiality is relative.** A factor is worth naming if it reaches 30% of
   that client's largest contribution. Measured decay by rank was 1.00 / 0.72 /
   0.48 / 0.36, so this typically yields two or three factors — and exactly one
   when a single driver dominates, which is what "no padding" has to mean.
3. **Direction follows the score.** A low score is explained by what pulled it
   down. Naming a positive driver on a low-scored account reads as a
   contradiction to the officer holding it.
"""

from typing import Final

from app.domain.value_objects.explanation_factor import (
    FEATURE_TO_FACTOR,
    ExplanationFactor,
    FactorKey,
)

#: Minimum share of the client's largest contribution for a factor to be named.
#: Measured decay by rank: 1.00, 0.72, 0.48, 0.36, 0.26.
MATERIALITY_THRESHOLD: Final[float] = 0.30

#: Cap on named factors, so the sentence stays readable.
MAX_FACTORS: Final[int] = 3

#: Score below which an account is explained by its negative drivers, and above
#: which by its positive ones. Matches the Low/Medium boundary used for banding.
LOW_BAND: Final[float] = 40.0

#: Score above which an account is explained by its positive drivers.
HIGH_BAND: Final[float] = 70.0


def rank_factors(contributions: dict[str, float], score: float) -> list[ExplanationFactor]:
    """Return the material factors behind a score, strongest first.

    Empty is never returned: if nothing clears the threshold in the score's own
    direction, the single largest contributor is named, because ``Score``
    requires a non-empty explanation.
    """
    grouped = _group(contributions)
    directional = _filter_by_direction(grouped, score)
    material = _filter_material(directional)

    if not material:
        # Every contribution is tiny or points against the score. Name the
        # largest anyway rather than return nothing.
        fallback = max(grouped, key=lambda f: abs(f.contribution), default=None)
        return [fallback] if fallback else []

    return material[:MAX_FACTORS]


def _group(contributions: dict[str, float]) -> list[ExplanationFactor]:
    """Sum contributions per business factor. **Runs before any ranking.**"""
    totals: dict[FactorKey, float] = {}
    for feature, value in contributions.items():
        key = FEATURE_TO_FACTOR.get(feature)
        if key is None:  # unknown feature — ignore rather than guess a label
            continue
        totals[key] = totals.get(key, 0.0) + value

    # Sort by magnitude, then by key name so ties never depend on dict order.
    return sorted(
        (ExplanationFactor(key=key, contribution=total) for key, total in totals.items()),
        key=lambda factor: (-abs(factor.contribution), factor.key.value),
    )


def _filter_by_direction(factors: list[ExplanationFactor], score: float) -> list[ExplanationFactor]:
    """Keep only factors that explain the score in its own direction.

    Mid-band accounts are genuinely mixed, so both directions are kept there —
    forcing a single sign would misrepresent an account that is neither clearly
    good nor clearly bad.
    """
    if score < LOW_BAND:
        return [f for f in factors if f.contribution < 0]
    if score > HIGH_BAND:
        return [f for f in factors if f.contribution > 0]
    return factors


def _filter_material(factors: list[ExplanationFactor]) -> list[ExplanationFactor]:
    """Drop factors below the relative threshold. Input is magnitude-sorted."""
    if not factors:
        return []
    largest = abs(factors[0].contribution)
    if largest == 0.0:
        return []
    return [f for f in factors if abs(f.contribution) / largest >= MATERIALITY_THRESHOLD]
