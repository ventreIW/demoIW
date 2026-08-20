# BUG-02: plan

3 tasks, TDD order.

### T1: Regression test — the filter must actually filter (RED)
- Rewrite `test_category_filter` so it cannot pass vacuously: read the unfiltered response,
  tally cases per category, then for each category present assert the filtered call returns
  exactly that tally and that every returned case carries that category. Assert the tally is
  > 0 before using it, so an empty portfolio fails the test rather than skipping it.
- Add a case-insensitivity case (`High` and `high` return identical bodies) and keep a
  negative case (`Nonsense` → 422).
- Fix the inner assertion's casing: the wire format is lowercase.
- Verify: `pytest tests/test_prioritized_endpoint.py -k category` → **FAILS** (proves the bug).
- Commit: `test(BUG-02): add non-vacuous regression test for category filter`

### T2: Derive the accepted values from ScoreCategory and compare enum-to-enum (GREEN)
- Replace the hardcoded `{"High","Medium","Low"}` with a set built from `ScoreCategory`.
- Resolve the input case-insensitively to a `ScoreCategory` member; on failure raise 422
  listing the real accepted values.
- Compare the resolved enum against `c.category` rather than string-vs-`cat.value`.
- Update the docstring at :368, which currently advertises the broken spelling.
- Verify: `pytest tests/test_prioritized_endpoint.py` → all green, T1 included.
- Commit: `fix(BUG-02): derive category filter values from ScoreCategory`

### T3: Sweep for the same vacuous-loop shape elsewhere (REFACTOR)
- The concealing pattern, not the casing, is what let this live four epics. Grep the backend
  suite for `for … in …:` blocks whose only content is an assertion, and check each for the
  same empty-collection blind spot.
- Report findings; fix only those that are genuinely vacuous *and* in scope for a filter this
  bug touches. Anything else becomes a recorded finding, not a silent edit.
- Verify: full backend suite green.
- Commit: `test(BUG-02): guard remaining vacuous filter assertions`

## Done when (from scope.md)
1. `?category=high` returns all high cases, count > 0 · 2. `?category=High` works too ·
3. invalid → 422 with real values · 4. valid set derived from the enum ·
5. test asserts non-empty first · 6. full suite green, nothing weakened.
