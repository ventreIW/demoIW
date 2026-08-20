# BUG-02: retrospective

## Summary
- **Root cause:** the validator was written from the endpoint's prose documentation rather
  than from the enum it validates. A hardcoded `{"High","Medium","Low"}` duplicated knowledge
  `ScoreCategory` already owned, and the two never agreed even at birth.
- **Fix approach:** derive accepted values from `ScoreCategory`, resolve input
  case-insensitively to a member, compare enum-to-enum.
- **Classification:** Interface / S2-Medium / Code / Incorrect

## Process Improvement

**Prevention:** bind the enum in the signature. Had the parameter been declared
`category: ScoreCategory | None = None` instead of `str | None = None`, FastAPI would have
validated and coerced in one step and this bug could not have been expressed. The general rule
is that a hand-written whitelist next to an existing enum is a duplication defect waiting to
happen — the whitelist should be *derived*, or better, never exist.

**Pattern:** `Bug Type=Interface` + a hand-maintained copy of an enum's values → the copy and
the enum disagree, and the disagreement is invisible because each side is internally
consistent. Search for the second source of truth, not for the wrong value.

## The concealment is the real story

The casing mismatch is a one-line defect. It survived four epics because
`test_category_filter` asserted inside `for case in body["cases"]:` — a loop whose body never
executes when the list is empty. **The test was green precisely because the feature was
broken.** That is the strongest form of concealment there is: the harder the bug bites, the
more reliably the test passes.

Two details make it worse:
- The test's inner assertion (`case["category"] == "High"`) was *also* wrong against the
  lowercase wire format, so even a working filter would have turned it red. Both halves were
  broken, and they cancelled.
- **The lesson had already been learned in this exact file.** The very next test is
  `test_days_overdue_min_actually_filters`, docstring "s5.1: the filter must filter." s5.1 hit
  the vacuous-filter problem on `days_overdue_min`, wrote a guard for it, and did not look
  twelve lines up at the sibling filter with the identical shape.

An AST sweep of the backend suite found 23 assert-only loops. Most iterate compile-time
constants (`FEATURE_COLUMNS`, `_FORBIDDEN_TOKENS`, literal tuples) and cannot be vacuous. One
in scope was genuinely unguarded — the `pareto_subset` half of
`test_every_case_carries_operator_facing_fields` — and is now guarded. The remainder iterate
runtime collections that are non-empty in practice; they are recorded below rather than edited,
to keep this diff one logical change.

## Recorded, not fixed here
Unguarded assert-only loops over runtime collections, low risk but same shape:
`test_prioritize_scenario_integration.py:154`, `test_score_scenario_integration.py:167,177`,
`test_score_scenario.py:92,190,204`, `test_sklearn_scorer.py:196`, `test_kpi_endpoint.py:180`,
`test_client_repository.py:91`, `test_invoice_repository.py:98`,
`test_payment_repository.py:209`, `test_build_training_set_integration.py:133`.

## ⚠ New defect discovered while verifying this fix — NOT part of BUG-02

**Scoring is non-deterministic under a fixed seed.** Three identical runs of the same request
(`seed=42`, same generate params, same endpoint) produced three different category
distributions:

    run 1: {'high': 66}
    run 2: {'high': 66}
    run 3: {'high': 61, 'medium': 5}

This is unrelated to the casing fix — it reproduces on both sides of it, and was visible only
because this bug's verification printed the tally twice.

Ruled out so far: every `np.random` use in `app/` goes through `default_rng(seed)`;
`_split_by_client` is fully deterministic (`sorted(y.unique())`, seeded permutation, sorted
outputs); LLM enrichment batches are processed sequentially in a plain `for` loop, so batch
completion order cannot vary. Not yet investigated: whether row order reaching the training
split can vary, which would change the split composition despite the stable seed.

Consequences if left: s7.4's demo smoke test cannot assert stable numbers; the executive demo
can show a director two different answers to the same question; and ADR-006/007's
reproducibility claims do not hold. Escalated as its own bug rather than absorbed here.

## Heutagogical Checkpoint

1. **Learned:** the wire format for `ScoreCategory` is lowercase everywhere — enum, response
   body, and the frontend's `ScoreCategory = 'high' | 'medium' | 'low'`. The frontend had
   already diagnosed this exact bug in a type comment (`types/prioritized.ts:5`, "validates
   against the capitalized spelling and therefore matches nothing (parked follow-up)"). The
   knowledge existed, written down, in the consuming layer — and never reached the wrong code.
2. **Process change:** when a test covers a filter, assert the filtered count against a tally
   derived from unfiltered data. "Every returned item matches" is not a test of a filter; it
   is satisfied by returning nothing.
3. **Framework improvement:** a lint/gate rule for assert-only loops over runtime collections
   without a preceding emptiness guard would have caught this in s4.5 and again in s5.1. This
   is the third distinct instance of the shape in one project.
4. **Capability gained:** can spot the "green because broken" test — where the failure mode
   and the passing condition are the same state.

## Patterns
- **Added: none.** `rai pattern add` remains a silent no-op (see BUG-01 retro); not re-attempted.
- Reinforced: none — PRIME retrieval still returns zero (`rai graph query`: `no such column: data_json`).

Preserved here instead:
- A hand-maintained copy of an enum's values is a second source of truth; derive it or bind
  the enum in the signature so the duplicate cannot exist.
- A test that asserts *inside* a loop over a filtered collection passes hardest when the
  filter is most broken. Guard emptiness before iterating.
