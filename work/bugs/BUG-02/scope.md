# BUG-02: scope

**Reported:** 2026-08-20 · **Branch:** `bug/BUG-02/prioritized-category-filter` · **From:** `main`

WHAT:      `GET /api/v1/scenarios/{id}/prioritized?category=…` can never return a case.
           The capitalized spelling passes validation and matches nothing (HTTP 200, 0 cases);
           the lowercase spelling matches the data but is rejected by validation (HTTP 422).
           The filter is unusable in both casings — there is no input that works.

WHEN:      Every call to `/prioritized` that supplies `category`. Independent of scenario,
           seed, or data. Reproduced 2026-08-20 on `main` at `1e91446`:

             UNFILTERED: 66 cases, categories present = {'high': 66}
               ?category=High    -> HTTP 200, cases=0
               ?category=high    -> HTTP 422
               ?category=Medium  -> HTTP 200, cases=0
               ?category=medium  -> HTTP 422
               ?category=Low     -> HTTP 200, cases=0
               ?category=low     -> HTTP 422

WHERE:     `backend/app/routers/scenarios.py`
           - :388  `valid_categories = {"High", "Medium", "Low"}` — hardcoded, capitalized,
                   not derived from the enum it is supposed to validate.
           - :429  `_cat_matches` compares `cat.value` — which is `"high"` — against the
                   capitalized input, so a request that survives validation cannot match.
           - :368  docstring advertises the broken spelling: "filter by High | Medium | Low".
           Source of truth: `app/domain/enums.py:24` `ScoreCategory(StrEnum)` = high/medium/low.

           Concealed by `backend/tests/test_prioritized_endpoint.py:184` `test_category_filter`,
           which asserts inside `for case in body["cases"]:` over an empty list. A vacuous loop
           passes unconditionally, so the suite has been green the whole time. Its assertion
           (`case["category"] == "High"`) is *also* wrong — the wire format is lowercase — so
           the test would have failed had the filter ever worked.

EXPECTED:  A category filter returns exactly the cases of that category, and rejects only
           genuinely invalid values. Canonical spelling is lowercase: it is what the
           `StrEnum` holds, what the API serializes, and what the frontend's
           `ScoreCategory = 'high' | 'medium' | 'low'` already expects.

Done when: 1. `?category=high` returns every high case and nothing else (count matches the
              unfiltered tally for that category, and is > 0).
           2. `?category=High` also works — accepted case-insensitively, so no existing caller
              breaks.
           3. `?category=Nonsense` still returns 422, listing the real accepted values.
           4. The valid-value set is derived from `ScoreCategory`, not hardcoded, so the two
              can never drift again.
           5. `test_category_filter` no longer passes vacuously: it asserts a non-empty result
              before asserting the contents.
           6. Full backend suite green; no test weakened or deleted.
