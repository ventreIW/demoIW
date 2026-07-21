# ADR-006: Prediction Target and Leakage Guard for the Collectability Model

**Date:** 2026-07-21
**Status:** Accepted
**Epic:** e4-intelligence-engine

## Context

E4 trains a supervised model that scores each client's collectability 0–100. It trains on the
synthetic data E3 produces. That data has a property which makes the choice of prediction
target consequential rather than routine.

Per **ADR-004**, each client is assigned a `payment_history_pattern` (`on_time`, `delayed_30`,
`delayed_60`, `delayed_90_plus`, `partial`, `default`). That pattern selects a
`_PatternProfile` — `overdue_prob`, `late_days_mean`, `partial_payer` — which then generates
**every invoice and payment for that client**. The pattern is the causal root of the entire
observable dataset, and it is persisted on the client record.

Two problems follow.

**1. Leakage.** `payment_history_pattern` is available as a column. A model given it as a
feature reaches near-perfect accuracy by reading the variable that produced the labels. The
result would look excellent and mean nothing.

**2. There is no natural outcome to predict.** The generator produces a *snapshot*, not a
history with resolutions. Invoices are either settled (with payments) or open (without). There
is no "did this client eventually pay" field, because no future is simulated.

Three candidate targets were considered.

## Decision

**The model predicts a forward-simulated collection outcome: given a client's present snapshot,
will their outstanding balance be collected within a 90-day horizon.**

- **Features** are the observable snapshot only — aggregates over invoices and payments, plus
  sector.
- **Label** is a future event simulated per client from that client's `_PatternProfile`, using
  the scenario's seeded RNG so the training set is reproducible for a fixed seed.

**`payment_history_pattern` must never enter the feature set.** Any story constructing features
must assert its absence in a test. This is a hard constraint, not a guideline.

## Alternatives considered

### Label mapped directly from `payment_history_pattern`

Map the pattern to a collectability class (`on_time`/`delayed_30` → High, `delayed_60`/`partial`
→ Medium, `delayed_90_plus`/`default` → Low), excluding the pattern from features.

Rejected. The model would be recovering a latent variable that the features were deterministically
generated from — inverting the generator rather than predicting behaviour. Accuracy would be high
and the number would not describe anything about collections. It also gives the demo a misleading
headline metric.

### Label = share of past invoices settled on time

Purely observable, no simulation required.

Rejected. The label is computed from the same payment rows the features are computed from, so it
correlates trivially with `days_overdue` and `pct_invoices_settled`. Partial leakage, and the
model would largely be learning an identity.

## Consequences

**Positive**

- The model predicts a genuine future event, which is what "propensity to pay" means in the
  domain and what makes RF-02.5 (rescore after contact) coherent.
- Features and label are separated by a time boundary, so leakage is structurally prevented
  rather than hoped for.
- The score is defensible to a non-technical audience: it is a probability of collection within
  90 days, not an abstract index.

**Negative**

- Requires a labelling component that E3 did not build (~1 day, in s4.2).
- The simulated label still descends from `_PATTERN_PROFILES`. On synthetic data this is
  unavoidable — every label ultimately comes from the generator. The guard is that the model
  sees only the *observable projection* of the cause, never the cause itself, which is exactly
  the situation a real collections model faces.
- The 90-day horizon is a modelling choice. It is aligned with the `delayed_90_plus` boundary in
  the domain enums, but a different horizon would produce a different class balance.

**Neutral**

- The labeller imports `_PATTERN_PROFILES` from the generator rather than redefining the
  constants, coupling E4's labeller to E3's behaviour model. Correct: one source of truth for
  the causal model.

## Verification

- A test asserts `payment_history_pattern` is absent from the feature frame's columns.
- The model is compared against a documented naive baseline (majority class). A model that
  cannot beat it is not delivering intelligence.
- Train/test split is by client — no client appears on both sides.
