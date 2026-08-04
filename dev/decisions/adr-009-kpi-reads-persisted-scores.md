# ADR-009: Executive KPIs Read Persisted Scores, Not an On-Demand Rescore

**Date:** 2026-08-04
**Status:** Accepted
**Epic:** e6-executive-panel

## Context

E6's KPI endpoint (s6.1) needs, per scenario: total overdue, expected recoverable value, case
counts by category, recovery rate, and a segmentation breakdown. Every one of those is an
aggregate over collectability scores.

There are already two ways scores reach a caller, and they disagree about where scores live:

- **`POST /api/v1/scenarios/{id}/score`** (s4.10) trains, scores, and **persists** a `Score` row per
  client. Idempotent.
- **`GET /api/v1/scenarios/{id}/prioritized`** (s4.x, consumed by E5's case list) **ignores those
  rows** and re-trains the model on every request — `backend/app/routers/scenarios.py`, where it
  calls `ScoreScenario()` then `PrioritizeScenario()` inline. The persisted table is never read.

That divergence was parked knowingly at E4 close ("prioritized endpoint reading persisted scores")
and E5 chose not to widen its scope to fix it. E6 cannot stay neutral: the executive dashboard and
the operator's queue are two views of one portfolio, shown to two people who talk to each other.

Two forces:

- **Consistency.** If the KPI endpoint re-scores independently, the director's "expected
  recoverable = $X" and the collector's queue totals are computed by two separate model fits. The
  model is trained on demand and its training set depends on labelling that shifts as contact
  results land (s5.3 → s4.6 rescore). The two numbers can differ, with no way to tell which is
  right.
- **Performance.** NFR-02 budgets 3 seconds at 500 clients / 2,000 invoices. A rescore is a feature
  extraction over the full invoice and payment set plus a logistic-regression fit. The queue pays
  that cost once per page load today; a dashboard that also re-scores pays it again, and the NL
  query layer (s6.3) would pay it per question.

## Decision

**The KPI aggregate reads persisted `Score` rows via `IScoreRepository.get_by_scenario()`. It never
trains a model.**

When a scenario has no persisted scores, `GET /kpis` returns **409 Conflict** with a message
naming the fix (`POST /{id}/score`), not an empty dashboard of zeros. A portfolio of $0 expected
recoverable is a legitimate answer for a settled book and an illegitimate one for an unscored book;
returning zeros makes those indistinguishable to the director.

**Monetary aggregates reuse `feature_extractor.outstanding_by_client()`** rather than re-deriving
"what is owed". That function is already the single definition of unsettled balance net of partial
payments, and is already shared with `outcome_labeller` for exactly this reason (ADR-006 D4). A
second definition of "total overdue" in a KPI service would drift from the scoring engine's, and
the drift would be invisible — both numbers would look plausible.

**`/prioritized` is not changed in E6.** Converging it onto persisted scores is the right end
state, but it is E5's delivered surface, it is what the demo's operator flow runs on, and rewriting
it 10 days before the demo trades a known inconsistency for an unknown regression. E6 documents the
divergence and leaves it to E7/E8.

## Consequences

**The demo flow gains a required step.** A scenario must be scored before the executive panel will
render. This is already true of the operator flow in spirit (an unscored scenario has no queue),
but here it becomes an explicit 409 the frontend must handle: s6.2 shows a "score this scenario"
empty state with an action, not an error toast. NFR-01's under-10-minutes path must include it.

**The dashboard becomes cheap.** Reading N score rows and aggregating is linear and has no model
fit, so s6.3's NL queries can execute per question without a performance cliff.

**A known inconsistency is documented rather than closed.** Until `/prioritized` converges, the
queue's scores come from a fresh fit and the dashboard's from the last persisted run. If a contact
result rescores a client and nobody re-runs `POST /score`, the dashboard is stale relative to the
queue. E6 makes this legible: the KPI response carries `scored_at` from the persisted run, and s6.2
displays it. A visibly stale timestamp is a recoverable demo moment; a silently wrong total is not.

## Alternatives considered

### KPI endpoint re-scores, mirroring `/prioritized`

Consistent with the queue by construction, since both would compute the same way from the same
inputs. Rejected on cost and on direction: it doubles the per-request model fit, puts a fit in the
path of every NL question, and entrenches the pattern we intend to remove. Consistency by "both
sides recompute identically" also only holds while the inputs are identical, which is precisely
what shifts as contact results land.

### Fix `/prioritized` to read persisted scores as part of E6

The correct end state, and it would close the divergence rather than document it. Rejected for this
epic on timing, not on merit: `/prioritized` is the spine of the delivered operator flow, its
rescore path feeds s5.3's contact-result loop, and the change lands in the same week as the demo.
Promoted to a scoped E7/E8 item rather than left in the parking lot.

### Materialize a KPI summary table on scoring

Precompute aggregates when `POST /score` runs. Rejected as YAGNI at demo scale — aggregating a few
hundred score rows in Python is not the bottleneck, and a second persisted representation is a
second thing that can go stale.
