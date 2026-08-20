# BUG-08: retrospective

## Summary
- **Root cause:** two distinct ones. Three of the four mandated fields were *discarded* rather
  than missing — model, prompt version and send time were all in scope where the record is
  written. The fourth, operator identifier, had **no source**: this product has no auth.
- **Fix approach:** widen the record (migration 0005); read model and prompt version back from
  the service that used them; stamp `sent_at` at the send seam; take the operator from a
  header with a self-describing default.
- **Classification:** Functional / S2-Medium / Design / **Missing**

## The interesting failure shape: all-or-nothing on a mixed-cost requirement

NFR-06 names four fields. Three were free — the values were already in scope at the moment the
record was constructed, and the fix for each is a keyword argument. The fourth needed a
decision this project had deliberately deferred (B-17, role-based access, still under
*Under consideration* in the backlog).

**One field with no source blocked all four.** Nobody wrote three-quarters of an audit record
and flagged the gap; the requirement simply stayed unimplemented. That is worth naming: a
requirement whose parts have very different costs will be read as a single unit and dropped
whole, unless someone splits it. The right move in s5.4 would have been to implement the three
free fields and record the operator question as an explicit open item — which is exactly what
this fix does, a year of project-time later.

## The honesty constraint was the only real design decision

The tempting implementation is `operator_id = "operator"`. It satisfies the schema, passes any
test asserting non-null, and **falsifies the audit record**. An audit trail with invented
provenance is worse than no audit trail, because it looks authoritative.

The codebase already had the right pattern in two places, and both were followed here:
- s4.8's `EnrichmentOutcome` — report honestly that enrichment did not run, rather than
  claiming the AI enriched data it did not touch.
- ADR-009's `scored_at` — surface staleness rather than silently reconciling it.

So the default is `"demo-operator (unauthenticated)"`, which states what it is. The test asserts
the string contains "demo", not that it equals a particular value — the requirement is that it
identifies itself as a placeholder, not that it has a specific spelling. When B-17 lands, the
`X-Operator-Id` header becomes the authenticated principal and nothing else changes.

## Deriving prompt_version from the filename

`prompt_version` reads from `TEMPLATE_FILENAME.split("_")[0]` — the file actually loaded —
rather than from a constant maintained beside it. This is a direct application of what BUG-02
and BUG-03 cost: both were a hand-maintained copy of a value that another piece of code owned,
and both drifted. A `PROMPT_VERSION = "v1"` constant next to a `v1_draft.txt` load is the same
shape, and would silently lie the first time someone adds `v2_draft.txt`.

## What the gates caught, and what that says

Two things broke that I did not anticipate, and both were caught by tooling rather than by me:

- **Three unit tests failed** because the mocked draft service returned `AsyncMock` objects for
  the two new properties and Pydantic rejected them. That is the correct failure — a widened
  contract should break incomplete test doubles.
- **`tsc` failed** on `case-detail-fixture.ts` the moment the frontend type gained the fields.
  This is the fixture↔API alignment that E6's M4 check verified by hand earlier today, working
  automatically because the fixture is typed against the interface.

Both are arguments for the strictness already in place. Neither would have surfaced in a
codebase with looser types or untyped fixtures.

## Why it survived to project close

E5's scope lists "draft persistence + audit log" as in-scope, and that was satisfied by a
persisted `CommunicationORM` row existing. **The word matched; the requirement did not.** No
acceptance criterion in s5.4 or s5.5 referenced NFR-06's field list.

And nothing checked. NFR-01 through NFR-05 each acquired a verifying test during E7 — the E2E
demo path, the performance test, the axe scan, the manifest, the key-parity guard. NFR-06
acquired none and was the only PRD requirement nothing tested. It surfaced only when the
project-completion review enumerated the PRD line by line rather than trusting the epic
tracker.

**This is the fourth distinct instance this session of "the test observed a proxy for the
outcome":** here the proxy was the *word* "audit" in an epic scope.

## Heutagogical Checkpoint

1. **Learned:** every non-functional requirement in this project that has a test is met, and
   the one without a test was not. That correlation is perfect across six NFRs, and it is not
   a coincidence — it is the strongest argument available for writing the verifier when the
   requirement is written, not when the epic closes.
2. **Process change:** when a requirement enumerates fields, put the enumeration in the
   acceptance criteria verbatim. "Audit log" is not a criterion; "timestamp, operator
   identifier, model used, prompt version" is.
3. **Framework improvement:** an NFR-to-test traceability check would have found this in one
   pass — for each NFR in the PRD, which test asserts it? Five of six had an answer.
4. **More capable of now:** can spot the mixed-cost requirement that gets dropped whole. If
   three parts are free and one needs a decision, ship the three and escalate the one.

## Patterns
- **Added: none** — `rai pattern add` is a verified no-op (BUG-01 retro). Preserved here:
  - A requirement whose parts have different costs gets read as one unit and dropped whole.
    Split it; ship the free parts; escalate the expensive one.
  - An audit field with invented provenance is worse than a null one. Make placeholders
    self-describing.
  - Derive a version from the artifact actually loaded, never from a constant maintained
    beside it.
  - Matching a *word* in a scope document is not satisfying a requirement.
