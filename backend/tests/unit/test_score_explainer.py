"""Tests for score explanation ranking (s4.4 T1).

Decides which factors are worth naming and in what order. Phrasing is T2.

The measurement behind this: on a 600-client retail scenario the two ageing
contributions correlate at 0.885, and 26.2% of clients have both in their top
tier. Without grouping, more than a quarter of explanations would state overdue
ageing twice — which a collections officer reads as padding.
"""

import pytest

from app.application.services.score_explainer import (
    MATERIALITY_THRESHOLD,
    MAX_FACTORS,
    explain,
    rank_factors,
)
from app.domain.value_objects.explanation_factor import FactorKey

# A realistic contributions dict; individual tests override what they care about.
_BASELINE = {
    "days_overdue_max": -0.05,
    "days_overdue_mean": -0.04,
    "pct_invoices_settled": -0.03,
    "outstanding_amount": -0.02,
    "avg_days_late_historical": -0.01,
    "invoice_count": 0.01,
    "has_partial_payments": -0.01,
    "avg_invoice_amount": 0.005,
}


def _contributions(**overrides: float) -> dict[str, float]:
    return {**_BASELINE, **overrides}


# --- Grouping -------------------------------------------------------------


def test_ageing_reported_once() -> None:
    """The measured 26.2% case: both ageing features strong and similar."""
    factors = rank_factors(
        _contributions(days_overdue_max=-0.40, days_overdue_mean=-0.38), score=30.0
    )

    ageing = [f for f in factors if f.key is FactorKey.AGEING]
    assert len(ageing) == 1


def test_ageing_contribution_is_the_sum_of_both_features() -> None:
    factors = rank_factors(
        _contributions(days_overdue_max=-0.30, days_overdue_mean=-0.20), score=30.0
    )

    ageing = next(f for f in factors if f.key is FactorKey.AGEING)
    assert ageing.contribution == pytest.approx(-0.50)


def test_grouping_happens_before_ranking() -> None:
    """The subtle one, and the reason this task exists.

    Individually `pct_invoices_settled` (0.40) beats either ageing feature
    (0.25, 0.24). Summed, ageing reaches 0.49 and should lead. If grouping were
    applied when rendering rather than before ranking, ageing would lose a slot
    it had actually won — the same split-weight problem that destabilised the
    coefficients in s4.3.
    """
    factors = rank_factors(
        _contributions(
            days_overdue_max=-0.25,
            days_overdue_mean=-0.24,
            pct_invoices_settled=-0.40,
        ),
        score=30.0,
    )

    assert factors[0].key is FactorKey.AGEING
    assert factors[1].key is FactorKey.SETTLEMENT


def test_only_the_measured_pair_is_grouped() -> None:
    """No broader grouping is invented without evidence."""
    factors = rank_factors(
        _contributions(
            pct_invoices_settled=-0.40,
            avg_days_late_historical=-0.35,
            days_overdue_max=-0.01,
            days_overdue_mean=-0.01,
        ),
        score=30.0,
    )

    keys = [f.key for f in factors]
    assert FactorKey.SETTLEMENT in keys
    assert FactorKey.PAYMENT_LATENESS in keys


# --- Materiality ----------------------------------------------------------


def test_documented_threshold_and_cap() -> None:
    assert MATERIALITY_THRESHOLD == 0.30
    assert MAX_FACTORS == 3


def test_factors_below_threshold_omitted() -> None:
    """A factor at 10% of the leader is noise, not a reason."""
    factors = rank_factors(
        _contributions(
            days_overdue_max=-0.50,
            days_overdue_mean=-0.00,
            pct_invoices_settled=-0.45,
            outstanding_amount=-0.05,  # 10% of the leader
        ),
        score=30.0,
    )

    assert FactorKey.OUTSTANDING not in [f.key for f in factors]


def test_factor_exactly_at_threshold_is_kept() -> None:
    factors = rank_factors(
        _contributions(
            days_overdue_max=-1.00,
            days_overdue_mean=0.0,
            pct_invoices_settled=-0.30,  # exactly 30%
            outstanding_amount=-0.01,
        ),
        score=30.0,
    )

    assert FactorKey.SETTLEMENT in [f.key for f in factors]


def test_dominant_factor_yields_single_reason() -> None:
    """No padding: one real driver produces one stated reason."""
    factors = rank_factors(
        _contributions(
            days_overdue_max=-0.90,
            days_overdue_mean=-0.10,
            pct_invoices_settled=-0.02,
            outstanding_amount=-0.01,
            avg_days_late_historical=-0.01,
            invoice_count=0.005,
            has_partial_payments=-0.005,
            avg_invoice_amount=0.001,
        ),
        score=20.0,
    )

    assert len(factors) == 1
    assert factors[0].key is FactorKey.AGEING


def test_at_most_three_factors() -> None:
    """Even when many factors are material, the sentence stays readable."""
    factors = rank_factors(
        _contributions(
            days_overdue_max=-0.50,
            days_overdue_mean=0.0,
            pct_invoices_settled=-0.50,
            outstanding_amount=-0.50,
            avg_days_late_historical=-0.50,
            invoice_count=-0.50,
        ),
        score=30.0,
    )

    assert len(factors) <= MAX_FACTORS


def test_factors_are_ordered_by_magnitude() -> None:
    factors = rank_factors(
        _contributions(
            days_overdue_max=-0.20,
            days_overdue_mean=0.0,
            pct_invoices_settled=-0.60,
            outstanding_amount=-0.40,
        ),
        score=30.0,
    )

    magnitudes = [abs(f.contribution) for f in factors]
    assert magnitudes == sorted(magnitudes, reverse=True)


# --- Direction ------------------------------------------------------------


def test_low_score_names_negative_drivers() -> None:
    """Guards the s4.3-class failure: explanation must not contradict the score."""
    factors = rank_factors(
        _contributions(
            days_overdue_max=-0.50,
            days_overdue_mean=-0.30,
            pct_invoices_settled=-0.45,
            invoice_count=0.40,
        ),
        score=25.0,
    )

    assert all(f.contribution < 0 for f in factors)


def test_high_score_names_positive_drivers() -> None:
    factors = rank_factors(
        _contributions(
            pct_invoices_settled=0.55,
            days_overdue_max=0.30,
            days_overdue_mean=0.25,
            outstanding_amount=-0.40,
        ),
        score=84.0,
    )

    assert all(f.contribution > 0 for f in factors)


def test_medium_score_may_name_either_direction() -> None:
    """Mid-band accounts are genuinely mixed; forcing one sign would misrepresent."""
    factors = rank_factors(
        _contributions(
            pct_invoices_settled=0.50,
            days_overdue_max=-0.45,
            days_overdue_mean=-0.10,
        ),
        score=55.0,
    )

    assert len(factors) >= 2


def test_no_material_factors_in_score_direction_falls_back_to_largest() -> None:
    """Score contract: an explanation is always possible."""
    factors = rank_factors(
        _contributions(
            days_overdue_max=0.02,
            days_overdue_mean=0.01,
            pct_invoices_settled=0.01,
            outstanding_amount=0.01,
            avg_days_late_historical=0.005,
            invoice_count=0.005,
            has_partial_payments=0.001,
            avg_invoice_amount=0.001,
        ),
        score=20.0,
    )

    assert len(factors) >= 1


# --- Determinism ----------------------------------------------------------


def test_ranking_is_deterministic() -> None:
    contributions = _contributions(days_overdue_max=-0.40, pct_invoices_settled=-0.35)

    first = rank_factors(contributions, score=30.0)
    second = rank_factors(contributions, score=30.0)

    assert [(f.key, f.contribution) for f in first] == [(f.key, f.contribution) for f in second]


def test_ties_broken_deterministically() -> None:
    """Equal magnitudes must not depend on dict iteration order."""
    contributions = _contributions(
        days_overdue_max=-0.40, days_overdue_mean=0.0, pct_invoices_settled=-0.40
    )

    runs = [rank_factors(dict(contributions), score=30.0) for _ in range(5)]
    keys = [[f.key for f in run] for run in runs]

    assert all(run == keys[0] for run in keys)


# --- Phrasing (T2) --------------------------------------------------------

_FACTS = {
    "days_overdue_max": 78.0,
    "days_overdue_mean": 41.0,
    "pct_invoices_settled": 0.29,
    "outstanding_amount": 18_500.0,
    "avg_days_late_historical": 12.0,
    "invoice_count": 7.0,
    "has_partial_payments": True,
    "avg_invoice_amount": 9_250.0,
}


def test_explanation_is_never_empty() -> None:
    """Score.explanation must always hold text."""
    assert explain(score=34.0, contributions=_contributions(), facts=_FACTS).strip()


def test_no_feature_names_in_output() -> None:
    """The officer reads business facts, never the model's vocabulary."""
    text = explain(
        score=34.0,
        contributions=_contributions(days_overdue_max=-0.5, pct_invoices_settled=-0.4),
        facts=_FACTS,
    )

    forbidden = [
        "days_overdue",
        "pct_invoices",
        "outstanding_amount",
        "avg_invoice",
        "has_partial",
        "coef",
        "contribution",
        "feature",
        "auc",
        "logistic",
    ]
    lowered = text.lower()
    for token in forbidden:
        assert token not in lowered, f"{token!r} leaked into: {text}"


def test_business_facts_are_rendered() -> None:
    text = explain(
        score=34.0,
        contributions=_contributions(days_overdue_max=-0.5, days_overdue_mean=-0.3),
        facts=_FACTS,
    )
    assert "78" in text


def test_monetary_values_are_formatted() -> None:
    text = explain(
        score=34.0,
        contributions=_contributions(
            outstanding_amount=-0.9, days_overdue_max=-0.05, days_overdue_mean=0.0
        ),
        facts=_FACTS,
    )
    assert "18,500" in text


def test_settlement_rendered_as_a_ratio() -> None:
    """'2 de 7 facturas' is checkable by an officer; '29%' is not."""
    text = explain(
        score=34.0,
        contributions=_contributions(
            pct_invoices_settled=-0.9, days_overdue_max=-0.05, days_overdue_mean=0.0
        ),
        facts=_FACTS,
    )
    assert "de 7" in text


def test_low_score_uses_risk_framing() -> None:
    text = explain(score=25.0, contributions=_contributions(days_overdue_max=-0.6), facts=_FACTS)
    assert text.lower().startswith("riesgo alto")


def test_high_score_uses_positive_framing() -> None:
    good = {
        **_FACTS,
        "days_overdue_max": 0.0,
        "pct_invoices_settled": 1.0,
        "invoice_count": 6.0,
        "has_partial_payments": False,
    }
    text = explain(
        score=82.0,
        contributions=_contributions(
            pct_invoices_settled=0.6, days_overdue_max=0.3, days_overdue_mean=0.2
        ),
        facts=good,
    )
    assert "buen perfil" in text.lower()


def test_dominant_factor_yields_one_clause() -> None:
    """No padding survives into the prose."""
    text = explain(
        score=20.0,
        contributions=_contributions(
            days_overdue_max=-0.9,
            days_overdue_mean=-0.1,
            pct_invoices_settled=-0.01,
            outstanding_amount=-0.01,
            avg_days_late_historical=-0.005,
            invoice_count=0.002,
            has_partial_payments=-0.002,
            avg_invoice_amount=0.001,
        ),
        facts={**_FACTS, "days_overdue_max": 145.0},
    )
    assert " y " not in text


def test_explanation_is_deterministic() -> None:
    contributions = _contributions(days_overdue_max=-0.4, pct_invoices_settled=-0.35)
    assert explain(score=34.0, contributions=contributions, facts=_FACTS) == explain(
        score=34.0, contributions=contributions, facts=_FACTS
    )


def test_sentence_ends_with_a_period() -> None:
    assert explain(score=34.0, contributions=_contributions(), facts=_FACTS).endswith(".")


def test_missing_fact_does_not_crash() -> None:
    """Facts come from the feature frame; a gap must degrade, not explode."""
    text = explain(
        score=34.0,
        contributions=_contributions(days_overdue_max=-0.6, days_overdue_mean=-0.2),
        facts={"pct_invoices_settled": 0.5, "invoice_count": 4.0},
    )
    assert text.strip()


def test_favourable_ageing_is_framed_as_favourable() -> None:
    """Found by reading real output: a positive ageing contribution means the
    client is LESS overdue than average, so the bare fact must not be rendered
    as if it were a problem. 'Buen perfil de pago: facturas con hasta 40 días de
    atraso' reads as a contradiction."""
    text = explain(
        score=85.0,
        contributions=_contributions(days_overdue_max=0.5, days_overdue_mean=0.3),
        facts={**_FACTS, "days_overdue_max": 40.0},
    )

    assert "atraso contenido" in text
    assert "facturas con hasta 40 días de atraso" not in text


def test_unfavourable_ageing_is_framed_as_a_problem() -> None:
    text = explain(
        score=25.0,
        contributions=_contributions(days_overdue_max=-0.5, days_overdue_mean=-0.3),
        facts={**_FACTS, "days_overdue_max": 480.0},
    )

    assert "facturas con hasta 480 días de atraso" in text


def test_partial_payments_framing_follows_direction() -> None:
    """Same fact, opposite sense: money received vs balance outstanding."""
    good = explain(
        score=82.0,
        contributions=_contributions(has_partial_payments=0.6),
        facts={**_FACTS, "has_partial_payments": True},
    )
    bad = explain(
        score=25.0,
        contributions=_contributions(has_partial_payments=-0.6),
        facts={**_FACTS, "has_partial_payments": True},
    )

    assert "recibidos" in good
    assert "pendientes" in bad
