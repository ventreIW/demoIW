"""Causal payment-behaviour model shared by generation and scoring.

Each :class:`~app.domain.enums.PaymentPattern` maps to the behavioural profile it
imposes on a client's invoices. ADR-004 established this as *causal* rather than
decorative: the pattern generates the observable data, which is what makes the
portfolio learnable by the collectability engine.

This lives in the domain layer, not in the generator adapter, because two
consumers need the same definition:

* ``ProceduralGenerator`` (E3) — produces invoices and payments from a profile
* ``OutcomeLabeller`` (E4) — simulates forward collection outcomes from the same
  profile, per ADR-006

Duplicating the constants would let the generator and the labeller drift apart
silently: the labeller would be simulating a different causal model than the one
that produced the data it is labelling.
"""

from dataclasses import dataclass

from app.domain.enums import PaymentPattern


@dataclass(frozen=True)
class PaymentBehaviourProfile:
    """Behavioural profile a payment pattern imposes on a client's invoices.

    ``overdue_prob``   P(an invoice is currently past-due and unsettled).
    ``late_days_mean`` Exponential scale (days) for both how overdue an open
                       invoice is and how late a settled invoice was paid. E4's
                       labeller reuses it as the scale for time-to-collection.
    ``partial_payer``  When overdue, this client makes a partial payment (balance
                       still outstanding) rather than none.
    """

    overdue_prob: float
    late_days_mean: float
    partial_payer: bool


# Pattern → behaviour. Ordered from healthiest to worst so overdue propensity is
# monotonic — this is the signal the collectability engine (E4) is meant to learn.
PATTERN_PROFILES: dict[PaymentPattern, PaymentBehaviourProfile] = {
    PaymentPattern.ON_TIME: PaymentBehaviourProfile(
        overdue_prob=0.05, late_days_mean=3.0, partial_payer=False
    ),
    PaymentPattern.DELAYED_30: PaymentBehaviourProfile(
        overdue_prob=0.25, late_days_mean=30.0, partial_payer=False
    ),
    PaymentPattern.DELAYED_60: PaymentBehaviourProfile(
        overdue_prob=0.45, late_days_mean=60.0, partial_payer=False
    ),
    PaymentPattern.DELAYED_90_PLUS: PaymentBehaviourProfile(
        overdue_prob=0.65, late_days_mean=100.0, partial_payer=False
    ),
    PaymentPattern.PARTIAL: PaymentBehaviourProfile(
        overdue_prob=0.60, late_days_mean=50.0, partial_payer=True
    ),
    PaymentPattern.DEFAULT: PaymentBehaviourProfile(
        overdue_prob=0.90, late_days_mean=160.0, partial_payer=False
    ),
}
