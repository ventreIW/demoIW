# ADR-011 — Identity is owned by persistence; ordering is owned by the domain

**Status:** Accepted · **Date:** 2026-08-20 · **Decider:** Rodrigo
**Context:** BUG-05 · **Supersedes:** nothing · **Amends:** nothing (ADR-006/007 unaffected)

## Context

`GenerationParams` declares that it "fully determines the output: the same params (including
seed and reference_date)". It did not. Two `POST /generate` calls with `seed=42` produced
different category distributions, different fitted models, and different portfolios.

Every random source in the pipeline is correctly seeded. `ProceduralGenerator` is
byte-identical across runs; scoring a fixed persisted scenario twice is identical; the
train/test split is fully sorted; the estimator is `lbfgs`, which is deterministic. The
non-determinism lived in the **coupling** between two individually-correct components:

`SQLAlchemyClientRepository.add_many` overwrote each client's id with `uuid4()`, discarding an
id the generator deliberately derives from the seeded RNG ("not `uuid.uuid4`, so identity is
reproducible too"). `OutcomeLabeller` then ordered clients by that id before applying a seeded
`rng.exponential` draw — so the same draw sequence was applied to a randomly permuted client
list on every run. `BuildTrainingSet` repeated the pattern one stage later, sorting the joined
frame by the same random id before taking a *positional* train/test split.

**A seeded draw applied along an unseeded axis is not seeded.**

## Decision

Separate the two concerns that were conflated in a single column.

- **Identity** stays owned by the persistence layer. `clients.id` remains a random surrogate
  key assigned at insert. It carries no meaning and no ordering.
- **Ordering** becomes an explicit, persisted, first-class property owned by the domain. A new
  column `clients.generation_index` records the client's position in its scenario's generation
  sequence, written by both write paths (generator order for `add_many`, CSV row order for
  `create_from_csv`).

Every consumer that applies a positional or seeded operation across clients orders by
`generation_index`, never by `id`. Both such sites are fixed: `OutcomeLabeller.label` and
`BuildTrainingSet.execute`.

`generation_index` is an **ordering key only**. `_design_matrix` selects `FEATURE_COLUMNS`
explicitly, so it can never enter the feature set — ADR-006's leakage guard is untouched, and
the existing leakage tests still pass.

## Alternatives rejected

**Honour the domain id** — delete the `uuid4()` overwrite so the generator's reproducible id
persists. Smallest diff, and it matches intent stated in three separate places. Rejected
because two generations with the same seed would then produce identical client UUIDs and
collide on the primary key. Same-seed regeneration is legal today and is exercised by the test
suite; making it an `IntegrityError` trades one defect for another.

**Namespace the id per scenario** — derive it as `uuid5(scenario_id, generator_id)`. Rejected
because the scenario's own id is random, so any id derived from it is random and the sort order
stays random. This does not address the defect at all.

**Order-free labelling** — give each client its own sub-seed so ordering stops mattering.
Genuinely the most robust option and the one most resistant to a third recurrence. Rejected
for now because it changes the labelling mathematics, which invalidates the ROC-AUC figures
measured in ADR-006/007 (0.732–0.739); those would have to be re-measured before the numbers
in those ADRs could stand. Worth revisiting if a third instance of this shape appears.

## Consequences

**Positive.** The same parameters now produce the same portfolio, verified over six
consecutive runs. The demo can be rehearsed and will behave the same way on the day. s7.4 can
assert on real values rather than only on structural invariants. ADR-006/007's measured figures
become meaningful, because they now describe a repeatable pipeline.

**Negative.** A schema change and a migration (`0004`), on a project with no local Postgres —
so `0004` is the first migration in this project whose forward *and* backward path must be
exercised as part of M4 rather than assumed. The backfill numbers existing rows by `id` within
each scenario, which reproduces the ordering those scenarios were already scored under, so
historical scores stay consistent with their data rather than being silently re-based.

**Residual risk.** The invariant is a convention, not a constraint: nothing prevents a future
consumer from sorting by `id` and reintroducing the defect a third time. The two current sites
carry comments explaining why. A stronger guarantee would require the order-free labelling
above, or a test that asserts reproducibility at the level of every consumer rather than only
end to end.

## Verification

- `backend/tests/test_scoring_reproducibility.py` — two generations with identical params must
  yield an identical score multiset and category tally. Ran 6× red before the fix, 6× green
  after. It compares portfolio *content*, not ids, since ids are random by design.
- Leakage guard re-run: `generation_index` does not appear in the feature set.
- Full backend suite: 551 passed, 1 xfailed (BUG-06), ruff and mypy clean.
