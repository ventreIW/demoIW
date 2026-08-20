# ADR-012 — Scoring unlabelled CSV uploads

**Status:** **PROPOSED — awaiting team decision (Gustavo / Rodrigo)** · **Date:** 2026-08-20
**Context:** BUG-06 · **Relates to:** ADR-006 (prediction target and leakage guard), ADR-007
**Author:** Rai. This is a proposal, not a decision — §1, human defines, machine executes.

## Context

`POST /api/v1/scenarios/upload-csv` is a shipped feature (B-07 / RF-07) that produces
scenarios nothing downstream can score. BUG-03 fixed the first cause (an invoice status no
consumer recognised). A second, deeper cause remains.

`create_from_csv` assigns `PaymentPattern.ON_TIME` to every client, because a CSV of
receivables carries `client_name, amount, due_date, invoice_id` and no payment history.
`OutcomeLabeller` then simulates each client's outcome *from* that pattern:

```python
scales = clients["payment_history_pattern"].map(lambda v: PATTERN_PROFILES[v].late_days_mean)
days_to_collect = rng.exponential(scale=scales.to_numpy())
```

A constant pattern gives a constant scale, every draw lands the same side of the 90-day
horizon, `BuildTrainingSet` sees one label class, and training aborts:

    InsufficientTrainingDataError: training set has a single label class
    (collected_within_90d=1); both classes are needed to train.

**The root issue is architectural, not a bug in `create_from_csv`.** ADR-006 chose to train
per scenario on labels simulated from a hidden generative `_PatternProfile` — machinery that
exists only because E3 *generated* the data. Uploaded data has no hidden truth to simulate
from. The design is sound for synthetic scenarios and undefined for real ones.

## The two obvious fixes are both wrong

**Derive the pattern from observable ageing** (e.g. heavily overdue → a later-paying profile).
This makes the label a deterministic function of `days_overdue`, which is a **feature**. That
is exactly the leakage ADR-006 declares non-negotiable — the model would invert the mapping
and score near-perfectly while learning nothing. It would also pass every existing leakage
test, because those assert `payment_history_pattern` is excluded from the feature set, not
that the label is independent of the features.

**Assign patterns pseudo-randomly** so both classes appear. Training would succeed and produce
a model fitted to noise. This is worse than failing: the demo would show a director confident
per-client scores with no relationship to the uploaded data. A visible error beats an
invisible fabrication (§2, stop on defects).

## Options

### Option A — Score uploads with a pre-trained model (recommended)

Train once on a reference generated scenario, persist the fitted pipeline, and *apply* it to
uploaded data rather than training on it.

This is the textbook shape of the problem: you have labelled data (synthetic) and unlabelled
data (uploads), and scoring unlabelled data with a model fitted on labelled data is what a
trained model is *for*. It also removes the per-request re-fit that ADR-009 already flags as a
divergence between the operator queue and the dashboard.

- **Cost:** model persistence and versioning; a decision about which scenario is the reference;
  `ScoreScenario` gains a "fit" vs "apply" split.
- **Honesty requirement:** the UI must state that an uploaded portfolio is scored by a model
  trained on synthetic data. It is a demonstrative product; the provenance should be visible.
- **Risk:** feature distributions in an uploaded file may sit far outside the training
  distribution, making scores unreliable in a way the number itself does not show.

### Option B — Refuse to score uploads, and say so well

Keep uploads as a data-loading convenience: list them, browse invoices, compute outstanding
totals and ageing — all of which work today and need no model. `/prioritized` and `/kpis`
return a clear, actionable 409 explaining that scoring requires a generated scenario.

- **Cost:** near zero. The 409 already exists; it needs copy and a UI state.
- **Benefit:** no fabricated intelligence, and the demo narrative stays truthful.
- **Loss:** "upload your own portfolio and see it prioritized" is a strong demo moment, and
  this forecloses it.

### Option C — Collect the missing signal at upload

Extend the CSV contract with an optional payment-history column so uploads can carry the field
the labeller needs.

- **Cost:** changes the published CSV contract; asks the demo facilitator for data they may not
  have; still trains per scenario on a tiny sample (`MIN_CLIENTS` is 20, and s4.3 measured
  AUC 0.286–1.000 at n=100 — a 30-row upload would be noise).
- **Assessment:** solves the mechanism and not the problem. Not recommended.

## Recommendation

**Option A**, with Option B's honest 409 as the fallback whenever no reference model exists.
A is the only option that makes the shipped feature deliver its advertised value without
fabricating anything, and it subsumes the ADR-009 convergence item already in the parking lot.

If the demo does not need CSV scoring, **Option B is entirely respectable** and costs a day
rather than a story — say so explicitly and the epic closes clean.

## Consequences if deferred

The current state is Option B *without the copy*: uploads persist, `/kpis` returns a bare 409,
and `/prioritized` raises. It is held visible by a strict `xfail` in `test_csv_upload.py` and
by `test_e2e_demo_flow.py::test_csv_upload_limit_is_explicit`, both of which fail loudly the
moment the boundary moves. Nothing degrades silently; the feature is simply half-delivered and
the demo should avoid it until this is decided.
