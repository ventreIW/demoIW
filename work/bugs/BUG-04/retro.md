# BUG-04: retrospective

## Summary
- **Root cause:** a Python-mode `model_dump()` written into a JSON column. `mode="json"` is
  the overload that coerces to primitives; the defaulting one is the one that does not.
- **Fix approach:** `params.model_dump(mode="json")` at the storage boundary.
- **Classification:** Data / S2-Medium / Code / Incorrect
- One-line fix; the value was in the tests and in what they exposed.

## Process Improvement

**Prevention:** at a serialization boundary, the dump mode is part of the contract, not a
default to inherit. Anywhere a Pydantic model is written to a `JSON` column, `mode="json"` is
the only correct overload — and the failure is invisible until a field whose Python and JSON
representations differ is actually populated.

**Pattern:** `Bug Type=Data` + an optional field that defaults to `None` → the defect sits on a
codepath the caller must opt into, so it survives every test that uses defaults. Coverage of
the *line* is not coverage of the *value*. `parameters=params.model_dump()` was executed by
many tests and broken by none of them, because none pinned the date.

## What made this bug quiet

`GenerationParams` has six other fields — an `int`, a `StrEnum`, and three floats — and every
one of them round-trips identically under both dump modes. `reference_date` is the only field
whose representations differ, it is optional, and it defaults to `None`. So a defect on the
persist line required the caller to opt into the single field that exposes it. That is why a
bug in the first statement of the persist call was never hit.

**The contributing factor is the interesting part.** Because pinning crashed, every scenario
in the system was necessarily generated with `reference_date: null`, which resolves to
`date.today()` at generation. The stored `parameters` therefore never recorded the anchor
actually used, and re-running a stored parameter set on a later day produces different due
dates. The bug was quietly guaranteeing the non-reproducibility the field exists to prevent —
and it did so silently, because the *record* of the parameters looked complete.

## I got the acceptance criterion wrong, and the code told me

Scope criterion 3 originally read: "a different pinned date produces different ageing". That
is backwards. The generator draws `days_overdue` from the RNG first and derives `due_date`
backwards from the anchor:

    days_overdue = int(self._rng.exponential(profile.late_days_mean)) + 1
    due_date     = self._today - timedelta(days=days_overdue)

So the pin moves the **calendar** and leaves the **ageing distribution invariant** — and that
invariance is the whole point: it is what lets the same parameters produce the same dataset on
a different day. Had I "fixed" the code to satisfy my original criterion, I would have broken
the feature to satisfy a test that misunderstood it.

The test now asserts the real invariant: same seed + same pin gives byte-identical due dates,
a different pin shifts *every* due date by exactly the offset between anchors, and ageing is
unchanged. The exact-offset assertion is stronger than "they differ" and would catch a partial
or per-row application of the anchor.

Criterion 3 in `scope.md` has been corrected in place with the reasoning, rather than quietly
rewritten.

## Relevance to BUG-05

This bug's test produced the first hard evidence in either direction on the determinism
question: `build(date(2026,6,1))` twice in the same process gave byte-identical due dates,
ageing, and ordering. **The `ProceduralGenerator` itself is deterministic under a fixed seed.**
Whatever makes `/prioritized` vary between runs is therefore downstream of generation — in
persistence, retrieval ordering, labelling, or training — not in the generator. That narrows
BUG-05 considerably.

## Heutagogical Checkpoint

1. **Learned:** `days_overdue` is generated as the primary quantity and the calendar is derived
   from it, not the reverse. That inverts the intuition — you would expect ageing to be
   computed from dates — and it is the mechanism behind cross-day reproducibility.
2. **Process change:** when a test fails on a "should be different" assertion, check whether
   the invariant is intentional before touching the code. My first instinct was that the pin
   was being ignored; the code was right and the test was wrong.
3. **Framework improvement:** none specific. The general point — that acceptance criteria
   written before reading the implementation can encode a misunderstanding — argues for
   drafting criteria in the scope phase but re-verifying them against the code during design,
   which is what the RaiSE story flow already prescribes and what the bugfix flow does not.
4. **Capability gained:** can distinguish "the parameter is ignored" from "the parameter's
   effect is elsewhere by design" — check what the value is derived *from* before concluding
   it is unused.

## Patterns
- **Added: none** — `rai pattern add` is a silent no-op (BUG-01 retro). Preserved here:
  - At a serialization boundary, dump mode is part of the contract, not a default.
  - An optional field defaulting to `None` hides defects on its own codepath from every test
    that uses defaults; line coverage is not value coverage.
  - A failing "should differ" assertion may mean the invariant is intentional. Read the
    derivation order before changing the code.
