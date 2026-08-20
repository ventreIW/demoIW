# BUG-05: retrospective

## Summary
- **Root cause:** `add_many` overwrote the generator's reproducible client id with `uuid4()`,
  and two downstream consumers applied seeded/positional operations along an axis sorted by
  that now-random id.
- **Fix approach:** separate identity from ordering — `generation_index` as an explicit
  persisted ordering key (ADR-011, migration 0004).
- **Classification:** Logic / S1-High / Design / Incorrect

## The sentence that explains this bug

**A seeded draw applied along an unseeded axis is not seeded.**

Every component here is individually, verifiably correct. The generator is byte-identical
across runs. `_split_by_client` sorts its inputs and its outputs. The estimator is `lbfgs`.
Every `np.random` call goes through `default_rng(seed)`. Auditing the random sources — the
obvious first move, and the one I made — finds nothing and *actively reassures*.

The defect lived in the coupling: `rng.exponential(scale=scales.to_numpy())` emits the same
sequence every run, but `scales` was ordered by a random key, so the same draws landed on
different clients each time.

## Process Improvement

**Prevention:** determinism is not a property of components, it is a property of a pipeline,
and it must be tested end to end. Six unit tests asserting each stage is seeded would all have
passed. The one test that catches this — generate twice, compare the portfolios — did not
exist, because determinism was assumed from the presence of a `seed` parameter rather than
verified through the composition.

**Pattern:** `Origin=Design` + two layers each internally consistent → look at the *boundary*,
not at either side. Persistence asserted "identity is assigned server-side"; the domain
asserted "identity is reproducible generated data". Both are defensible; nobody reconciled
them, and the contradiction was invisible from inside either layer.

## The fix revealed a second instance of itself

Fixing `OutcomeLabeller` did not make the test pass. `BuildTrainingSet` then sorted the joined
frame by the same random `id` before taking a **positional** train/test split — the identical
shape, one stage later, and invisible until the first was fixed.

That is the most useful thing this bug taught: **when a defect is a pattern rather than a
typo, fixing the first occurrence is how you find the second.** I had already written in the
BUG-05 analysis that the labeller was "the" root cause. It was one of two. The bisection was
right about the *cause* (`add_many`) and incomplete about the *consequences*.

If this shape appears a third time, ADR-011's rejected option — per-client sub-seeds, removing
order-dependence entirely — becomes the right answer despite requiring ADR-006/007's ROC-AUC
figures to be re-measured.

## How this was found, and what that says

It was found by accident. BUG-02's verification printed the category tally twice, and the two
printouts disagreed. Nobody was looking for a determinism bug; the numbers simply did not match
across two lines of output that had no reason to differ.

Four epics of work — including ADR-006 and ADR-007, whose measured ROC-AUC figures of
0.732–0.739 presuppose a reproducible pipeline — ran on top of this. The E4 M4 checkpoint
caught a generation-layer bug no unit test saw; this is a second instance of the same lesson,
and an argument that M4-style real-path verification is worth more than the unit suites
suggest.

## Interaction with the other bugs this session

Reproducibility was broken along **two independent axes at once**:

- **Identity** — this bug.
- **Calendar** — BUG-04. Because a pinned `reference_date` crashed at persist, every scenario
  resolved its anchor to `date.today()`, so re-running stored parameters on a later day
  produced different ageing.

Fixing either alone would not have produced a reproducible pipeline, and testing either alone
would have shown a still-failing system and invited the conclusion that the fix did not work.
The reproducibility test pins `reference_date` explicitly so that identity is the only free
variable — without BUG-04's fix, that pin would have crashed.

## Heutagogical Checkpoint

1. **Learned:** `clients.id` is a random surrogate key, not the generator's id — the two are
   disjoint (`intersection = 0` over 100 clients). Anything in this codebase that treats a
   persisted id as meaningful, ordered, or reproducible is wrong.
2. **Process change:** for a non-deterministic symptom, bisect by *stage* with an explicit
   elimination table before reading any code. That found the boundary in five tests, where
   reading the random-number usage — which is what I did first — produced only false
   reassurance.
3. **Framework improvement:** `rai gate check` reporting 5 of 15 gates failed while exiting 0
   is the reason a project can carry defects of this size undetected. Determinism belongs in
   the gate set for any seeded pipeline, and a gate that cannot fail cannot enforce it.
4. **Capability gained:** can recognise the "individually seeded, jointly random" shape — and
   know to look for the ordering axis rather than the random source.

## Patterns
- **Added: none** — `rai pattern add` is a silent no-op (BUG-01 retro). Preserved here:
  - A seeded draw applied along an unseeded axis is not seeded. Audit the *ordering*, not only
    the RNG.
  - Determinism is a property of a pipeline, not of its components; test it end to end.
  - When two layers each hold a coherent but contradictory belief about ownership, the bug is
    at the boundary and invisible from inside either one.
  - When a defect is a pattern rather than a typo, fixing the first occurrence is how you find
    the second. Re-run the failing test after each fix and expect it to still fail.
