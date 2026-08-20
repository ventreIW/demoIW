# BUG-02: analysis

## Method: Stack-free contract tracing (the value's path through the request)

There is no exception and no stack — the endpoint returns 200. So the method was to follow the
single value (`category`) from the query string to the comparison, and ask at each hop what
spelling it is expected to have.

## The path

| Hop | Location | Spelling assumed | Source of that assumption |
|---|---|---|---|
| 1. Parameter arrives | `scenarios.py:358` `category: str \| None` | any | untyped `str` — no enum binding |
| 2. Validated | `scenarios.py:388` `{"High","Medium","Low"}` | **Capitalized** | hardcoded literal |
| 3. Data computed | `ScoreScenario` → `PrioritizedCase.category` | **lowercase** | `ScoreCategory(StrEnum)` |
| 4. Compared | `scenarios.py:429` `cat.value == category` | must match hop 2 *and* hop 3 | — |
| 5. Serialized out | response body | **lowercase** | same `StrEnum` |

Hops 2 and 3 disagree, and hop 4 requires them to agree. The set of inputs satisfying both is
empty, which is why every casing fails — one at the validator, the other at the comparator.

## Root cause

**The validator was written from the API's prose documentation rather than from the enum it
validates.** `valid_categories` is a hardcoded literal duplicating knowledge that
`ScoreCategory` already owns. Duplicated knowledge drifts; here it never even agreed at
birth. The comparison at hop 4 is correct code — `cat.value` genuinely is the right thing to
compare — it just cannot succeed against a whitelist derived from a different source.

Note the endpoint declares `category: str | None`, not `category: ScoreCategory | None`.
Had it bound the enum directly, FastAPI would have validated and coerced in one step and this
bug could not have been written.

## Why it survived four epics

`test_category_filter` (`test_prioritized_endpoint.py:184`) asserts inside
`for case in body["cases"]:`. When the filter returns nothing the loop body never executes and
the test passes unconditionally — the test is green *because* the feature is broken, which is
the strongest possible form of concealment. Its inner assertion
(`case["category"] == "High"`) is independently wrong against the lowercase wire format, so
even a correct filter would have turned this test red.

The lesson had already been learned once in this very file: the next test along is named
`test_days_overdue_min_actually_filters` with the docstring "s5.1: the filter must filter."
s5.1 hit the vacuous-filter problem, wrote a guard for `days_overdue_min`, and did not
generalize it to the sibling filter twelve lines above.

## Contributing factor

The frontend already knew. `frontend/src/types/prioritized.ts:5` carries a comment stating the
filter "validates against the capitalized spelling and therefore matches nothing (parked
follow-up)". The defect was diagnosed correctly at least once, written down in the consuming
layer, and parked rather than fixed — so the knowledge existed but never reached the code that
was wrong.

## Fix approach

Derive the accepted values from `ScoreCategory` and compare enum-to-enum rather than
string-to-string, accepting input case-insensitively so both `high` and `High` resolve.
Then repair the concealing test: assert the filtered set is non-empty and that its size equals
the tally for that category in the unfiltered response, so it can never again pass vacuously.
