"""Tests for the causal payment-behaviour model (s4.2 T1, ADR-006 D1).

These profiles were moved out of ``ProceduralGenerator`` into the domain layer so
that E3's generator and E4's outcome labeller share one definition. Duplicating
them would let the two drift apart silently — the labeller would be simulating a
different causal model than the one that produced the data.
"""

import dataclasses

import pytest

from app.domain.enums import PaymentPattern
from app.domain.value_objects.payment_behaviour import (
    PATTERN_PROFILES,
    PaymentBehaviourProfile,
)


def test_every_payment_pattern_has_a_profile() -> None:
    """A pattern without a profile would break generation and labelling alike."""
    assert set(PATTERN_PROFILES) == set(PaymentPattern)


def test_profiles_are_frozen() -> None:
    profile = PATTERN_PROFILES[PaymentPattern.ON_TIME]
    with pytest.raises(dataclasses.FrozenInstanceError):
        profile.late_days_mean = 999.0  # type: ignore[misc]


def test_lateness_is_monotonic_across_severity() -> None:
    """The gradient the collectability engine is meant to learn (ADR-004)."""
    ordered = [
        PaymentPattern.ON_TIME,
        PaymentPattern.DELAYED_30,
        PaymentPattern.DELAYED_60,
        PaymentPattern.DELAYED_90_PLUS,
    ]
    means = [PATTERN_PROFILES[p].late_days_mean for p in ordered]
    assert means == sorted(means)
    assert means[0] < means[-1]


def test_overdue_probability_is_monotonic_across_severity() -> None:
    ordered = [
        PaymentPattern.ON_TIME,
        PaymentPattern.DELAYED_30,
        PaymentPattern.DELAYED_60,
        PaymentPattern.DELAYED_90_PLUS,
    ]
    probs = [PATTERN_PROFILES[p].overdue_prob for p in ordered]
    assert probs == sorted(probs)


def test_default_is_the_worst_profile() -> None:
    """s4.2's labeller relies on DEFAULT being the least collectable cohort."""
    default = PATTERN_PROFILES[PaymentPattern.DEFAULT]
    others = [p for k, p in PATTERN_PROFILES.items() if k is not PaymentPattern.DEFAULT]
    assert default.late_days_mean > max(p.late_days_mean for p in others)
    assert default.overdue_prob >= max(p.overdue_prob for p in others)


def test_only_partial_pattern_is_a_partial_payer() -> None:
    partial_payers = {k for k, p in PATTERN_PROFILES.items() if p.partial_payer}
    assert partial_payers == {PaymentPattern.PARTIAL}


def test_probabilities_are_within_unit_interval() -> None:
    for pattern, profile in PATTERN_PROFILES.items():
        assert 0.0 <= profile.overdue_prob <= 1.0, pattern
        assert profile.late_days_mean > 0.0, pattern


def test_profile_type_is_exported_publicly() -> None:
    """The labeller (s4.2 T3) type-annotates against this, so it must be public."""
    assert PaymentBehaviourProfile.__name__ == "PaymentBehaviourProfile"
    assert not PaymentBehaviourProfile.__name__.startswith("_")
