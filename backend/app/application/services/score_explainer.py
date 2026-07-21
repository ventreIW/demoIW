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


# --- Phrasing -------------------------------------------------------------
#
# Each factor owns a template rendering the *underlying business fact*, never the
# feature name or its coefficient. An officer can verify "78 días de atraso"
# against the ledger; "days_overdue_max=-0.31" tells them nothing they can act on.

#: Opening clause, chosen from the score band.
_HEADLINES: Final[dict[str, str]] = {
    "low": "Riesgo alto",
    "medium": "Perfil mixto",
    "high": "Buen perfil de pago",
}


def _headline(score: float) -> str:
    if score < LOW_BAND:
        return _HEADLINES["low"]
    if score > HIGH_BAND:
        return _HEADLINES["high"]
    return _HEADLINES["medium"]


def _money(amount: float) -> str:
    return f"${amount:,.0f}"


def _phrase(factor: ExplanationFactor, facts: dict[str, float | bool]) -> str | None:
    """Render one factor as a Spanish clause, or ``None`` if its fact is missing.

    **Framing follows the contribution's sign, not the raw value.** A positive
    ageing contribution means this client is *less* overdue than the portfolio
    average, so "40 días" is favourable here and unfavourable elsewhere. Rendering
    the bare fact produced sentences like "Buen perfil de pago: facturas con hasta
    40 días de atraso", which reads as a contradiction to an officer.

    Returning ``None`` rather than raising means a gap in the feature frame
    degrades the sentence instead of failing the whole scoring run.
    """
    favourable = factor.contribution > 0

    if factor.key is FactorKey.AGEING:
        days = facts.get("days_overdue_max")
        if days is None:
            return None
        value = float(days)
        if value <= 0:
            return "sin facturas vencidas"
        if favourable:
            return f"atraso contenido, de hasta {value:.0f} días"
        return f"facturas con hasta {value:.0f} días de atraso"

    if factor.key is FactorKey.SETTLEMENT:
        pct, count = facts.get("pct_invoices_settled"), facts.get("invoice_count")
        if pct is None or count is None:
            return None
        total = int(float(count))
        settled = round(float(pct) * total)
        if favourable:
            return f"{settled} de {total} facturas liquidadas"
        return f"sólo {settled} de {total} facturas liquidadas"

    if factor.key is FactorKey.OUTSTANDING:
        amount = facts.get("outstanding_amount")
        if amount is None:
            return None
        if favourable:
            return f"saldo bajo, de {_money(float(amount))}"
        return f"{_money(float(amount))} pendientes de cobro"

    if factor.key is FactorKey.PAYMENT_LATENESS:
        days = facts.get("avg_days_late_historical")
        if days is None:
            return None
        value = float(days)
        if value <= 1:
            return "historial de pagos puntuales"
        if favourable:
            return f"historial de pago razonable, {value:.0f} días de retraso promedio"
        return f"pagos históricos con {value:.0f} días de retraso promedio"

    if factor.key is FactorKey.PARTIAL_PAYMENTS:
        has_partial = facts.get("has_partial_payments")
        if has_partial is None:
            return None
        if not has_partial:
            return "sin pagos parciales"
        # A partial payer is mid-gradient: worse than a punctual client, better
        # than one who has paid nothing. Frame by which comparison applies here.
        return "pagos parciales recibidos" if favourable else "pagos parciales pendientes"

    if factor.key is FactorKey.INVOICE_COUNT:
        count = facts.get("invoice_count")
        if count is None:
            return None
        return f"{int(float(count))} facturas en el periodo"

    if factor.key is FactorKey.INVOICE_SIZE:
        amount = facts.get("avg_invoice_amount")
        if amount is None:
            return None
        return f"facturas de {_money(float(amount))} en promedio"

    return None


def _join(clauses: list[str]) -> str:
    """Spanish list joining: 'a', 'a y b', 'a, b y c'."""
    if len(clauses) == 1:
        return clauses[0]
    return f"{', '.join(clauses[:-1])} y {clauses[-1]}"


def explain(score: float, contributions: dict[str, float], facts: dict[str, float | bool]) -> str:
    """One Spanish sentence naming what drove this score.

    Deterministic by construction — template text over ranked numeric
    contributions, with no model call. This is required rather than preferred:
    ``OPENROUTER_API_KEY`` is unavailable, and an LLM would give the same client
    different reasoning on two runs of the same seeded scenario.
    """
    factors = rank_factors(contributions, score)
    clauses = [clause for factor in factors if (clause := _phrase(factor, facts)) is not None]

    headline = _headline(score)
    if not clauses:
        return f"{headline}: probabilidad estimada de cobro en 90 días de {score:.0f}%."

    return f"{headline}: {_join(clauses)}."
