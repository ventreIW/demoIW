# ADR-004: Pattern-Driven Behavioural Model for Synthetic AR Data

**Date:** 2026-07-02
**Status:** Accepted
**Epic:** e3-synthetic-dataset-generator
**Supersedes:** the independent-knob generation model in the first s3.1 draft

## Context

The first s3.1 implementation drew overdue status from a single global `overdue_rate`
(Bernoulli) and days-overdue from a global `days_overdue_lambda`, **independent of each
client's `payment_history_pattern`**. That made the pattern label decorative: an `ON_TIME`
client could have an all-overdue portfolio and a `DEFAULT` client a pristine one.

This breaks the epic's own success criteria ("payment histories that match behavioural
patterns") and, more importantly for a catalog demo, leaves **no signal for the collectability
engine (E4) to learn** — a scoring model trained on noise demos poorly.

Additionally, `days_overdue_lambda` was a misnomer: `numpy.Generator.exponential(x)` treats
`x` as the scale (the mean), not the rate λ, so the parameter's name lied about its effect.

## Decision

Make the payment pattern **causal**. Each `PaymentPattern` maps to a `_PatternProfile` that
governs its clients' invoice outcomes; the global `overdue_rate` and `days_overdue_lambda`
knobs are removed. A portfolio's overall overdue rate is now an **emergent** property of its
sector's pattern mix.

| Pattern | overdue_prob | late_days_mean | payment behaviour when overdue |
|---|---|---|---|
| ON_TIME | 0.05 | 3 | — (rarely overdue) |
| DELAYED_30 | 0.25 | 30 | no payment yet |
| DELAYED_60 | 0.45 | 60 | no payment yet |
| DELAYED_90_PLUS | 0.65 | 100 | no payment yet |
| PARTIAL | 0.60 | 50 | **partial** payment (20–60% of amount) |
| DEFAULT | 0.90 | 160 | no payment |

Invoice lifecycle per invoice of a client with profile *P*:

- **Overdue** (prob `P.overdue_prob`): `status="overdue"`, `days_overdue = Exp(P.late_days_mean)+1`,
  `due_date = today − days_overdue`. A payment row exists only for PARTIAL payers (fraction of amount).
- **Settled** (otherwise): `status="paid"`, `days_overdue=0`, a full-amount payment whose
  lateness is `Exp(P.late_days_mean)` days after the due date. Captures "pays, but late" history.

Common to both: `amount ~ Normal(mean, std)` floored at 100; `issue_date = due_date − 30d`
(net-30 terms); sequential `folio`; RNG-derived UUIDs.

`late_days_mean` is now correctly named (it is the exponential scale = mean days).
A `reference_date` param anchors ageing so generation is reproducible across calendar days.

## Rationale

- **Learnable signal.** Overdue propensity and ageing rise monotonically with pattern severity
  (verified: ON_TIME ≈ 0.05 → DEFAULT ≈ 0.85), so E4 has a real relationship to model.
- **Coherent records.** A "paid" invoice always has a full payment; an overdue DEFAULT invoice
  never has one; a PARTIAL client shows an outstanding balance. No self-contradicting rows.
- **Emergent realism.** Overall overdue rate falls out of the sector's behavioural mix (~0.3 for
  MANUFACTURING) rather than being dialled in, which is how real AR portfolios behave.
- **Honest parameters.** Removing the mislabelled `days_overdue_lambda` avoids a semantic trap;
  `reference_date` makes determinism a property of the params, not the wall clock.

## Assumptions & limitations (explicit, for a demo asset)

- **Profile numbers are hand-authored, not fitted to real data.** They are plausible and
  internally consistent, tuned to produce clear inter-pattern separation for demonstrations —
  not calibrated against any real portfolio. They are the first thing to revisit if a client
  wants sector-accurate figures.
- Two invoice states only (`paid` / `overdue`); no `disputed`, `written_off`, or `not_yet_due`.
- One payment per invoice (full, or a single partial for PARTIAL payers) — no instalment plans.
- Amounts are pattern-independent (only overdue behaviour depends on pattern).
- Net-30 terms are fixed for all sectors.

## Alternatives considered

| Alternative | Reason rejected |
|---|---|
| Keep global `overdue_rate`, add a per-pattern multiplier | Still not truly causal; two knobs fight each other; harder to reason about |
| Fit profiles to a public AR dataset | Out of scope for a demo asset; no licensed dataset on hand; adds a data dependency |
| Add `not_yet_due` / `disputed` states | Extra states with no consumer yet (E4 scores binary collectability) — YAGNI |

## Consequences

- **Easier:** E4 gets a dataset with genuine, monotonic signal; demos of "why this client scores
  low" have a real explanation (their pattern).
- **Harder:** `GenerationParams` changed shape (dropped `overdue_rate`/`days_overdue_lambda`,
  added `reference_date`) — any earlier caller must migrate. None exist yet (s3.1 is net-new).
- **Profiles are a tuning surface:** the `_PATTERN_PROFILES` table is the single place to adjust
  behavioural realism; documented as such in code.

## Traces to

- E3 brief: "payment histories that match behavioural patterns", "realistic distributions".
- ADR-003 (procedural + LLM hybrid) — this refines the *procedural* half.
- s3.1 tests: `test_pattern_drives_overdue_propensity`, `test_settled_invoice_has_full_payment`,
  `test_partial_payers_make_partial_payments_on_overdue`, `test_default_overdue_invoices_have_no_payment`.
