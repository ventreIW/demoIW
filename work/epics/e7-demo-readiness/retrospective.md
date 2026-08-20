# Retrospective: E7 — Demo Readiness (PWA · Accessibility · EN · E2E)

**Stories:** s7.1–s7.4, 4 of 4 delivered · **Closed:** 2026-08-20
**Backlog:** B-14, B-15 (EN pass), B-16 · **NFRs:** NFR-01, NFR-03, NFR-04, NFR-05

## Summary

E7 was scoped as "the trimmable buffer" — real polish that would flex if the schedule tightened
toward 2026-08-14. It did not need to flex: the demo date turned out to be movable, and all
four stories shipped. The product is installable, accessible, bilingual, and its demo path is
now proven by an automated test rather than asserted in a brief.

The epic's character changed completely at s7.4. The first three stories were polish. The
fourth opened the path to actual verification, and verification found that the path was broken
in five places.

## Success criteria — verified against observable state

| Criterion | Signal | Verified |
|---|---|---|
| **Installable PWA** (NFR-04) | `public/manifest.json` with `id`, `scope`, `lang`, `start_url`, 4 icons including a maskable one; hardened hand-rolled `sw.js` (ADR-010) | ✅ |
| **Accessible** (NFR-05) | axe-core WCAG 2.1 AA scan across **10 components**, 0 violations; contrast fixes; skip-link, landmarks, `aria-current`, focus-visible | ✅ |
| **Bilingual** (NFR-03) | 177/177 key parity between `en.json` and `es.json`. The 15 identical values are proper nouns (`demoIW`, `WhatsApp`), true ES/EN cognates (`Total`, `Sector`, `Formal`, `Retail`, `Score`, `Folio`), symbols and a format string — checked individually, none is an untranslated leak | ✅ |
| **Demo flow proven** (NFR-01, B-16) | `test_e2e_demo_flow.py` drives all ten steps in **1.41s** against a 600s budget; proven able to fail via two deliberate breakages | ✅ |

The a11y count is 10, not the 9 s7.2 reported: s7.4's BUG-01 work found `caseDetailFixture`
imported but never used in the scan file — a fossil of an intended-but-omitted scan of
`CaseDetail`, a primary operator surface. The obvious lint fix (delete the unused import) would
have destroyed the only remaining evidence of the gap. The scan was added instead and passes.

## Story-by-story

| Story | Outcome |
|---|---|
| s7.1 PWA | Manifest completed, service worker hardened with versioned precache and locale-aware offline fallback (ADR-010, no `next-pwa`). Found the build blocker that became BUG-01 |
| s7.2 Accessibility | WCAG 2.1 AA contrast + keyboard nav, axe scan. Also *added* 2 of the lint errors that kept the build red — into a gate that was already red and therefore silent |
| s7.3 English pass | 172/172 EN keys reviewed; the identical-value leak it introduced was caught and guarded in s7.1 |
| s7.4 E2E validation | The full demo path, repeatability, CSV boundary, both LLM paths, and the M4 Postgres harness |

## The finding: this epic's value was almost entirely in its last story

s7.1 found the build blocker and recorded it. s7.2 then added two more errors to the same
already-red gate without anyone noticing — the clearest possible demonstration of why a
permanently failing gate is worse than no gate. And s7.4, the story that finally *ran* the demo
path, found five defects that 546 passing tests could not see:

| Bug | What 546 green tests could not see |
|---|---|
| BUG-01 | The production build had not worked for 13 days |
| BUG-02 | A filter that returned nothing for every possible input |
| BUG-03 | An entire shipped feature (CSV upload) producing unusable scenarios |
| BUG-04 | The reproducibility parameter crashing on use |
| BUG-05 | The scoring model being different on every run |

All five share one shape: **the tests observed a proxy for the outcome rather than the
outcome.** A gate nobody ran. A loop that asserted nothing when empty. A feature tested up to
persistence and not one step past it. A parameter never exercised because it defaulted to
`None`. A pipeline whose components were each verifiably seeded while their composition was
not.

That is the argument for B-16 having existed from the start, and the reason E7's own trim
guidance ranked s7.4 first among the four ("Priority order to keep: s7.4 (proves the demo
works) > s7.1 > s7.2 > s7.3"). That ranking was correct.

## What went well

**The trim guidance was written before it was needed, and it was right.** E7's brief ranked the
stories by what to keep under schedule pressure, and put the verification story first. When the
pressure evaporated the ranking still held — s7.4 delivered by far the most value.

**s7.1's blocker report was specific enough to act on nine days later.** It named the commit
(`2fc1501`), the count, the split between s6.2 and s7.2, and where to look. That is why BUG-01
took one pipeline rather than an investigation. (Its count was off by one — 11 vs the actual
10 — corrected during BUG-01.)

**Non-vacuity became a design constraint rather than a review note.** After BUG-02, s7.4 was
written so that no assertion *can* pass over an empty collection, and an AST sweep checked the
existing backend suite for the same shape. That is the difference between fixing a bug and
closing a defect class.

## What to improve

**"Demo-ready" was being judged by story completion rather than by running the demo.** Three
stories were marked done, the epic was 3/4, and the product had no working production build,
a filter that always returned nothing, and a model that changed on every run. Nothing in the
process was wrong — each story met its own criteria. The gap is that no criterion belonged to
the *whole*, until s7.4 created one.

**Acceptance criteria written before reading the code encode assumptions.** It happened twice
in one session: s7.4's story artifact had three wrong API contracts, and BUG-04's criterion 3
asserted against the generator's design (had it been satisfied, the feature would have broken).
Both were caught by the design phase's gemba walk. The lesson is that gemba is where criteria
get *re-verified*, not merely elaborated.

## Open at close

- ⛔ **E6 M4's real-PostgreSQL run** — the single remaining gate. Harness written, skips loudly,
  runs on one command. Now also covers migration `0004`, which no test has ever executed.
- **BUG-06** — CSV uploads unscorable for an architectural reason; needs an ADR, held as a
  strict `xfail` plus an explicit boundary assertion.
- **13 `format:check` failures**, with the gate absent from CI — the same pathology as BUG-01
  one layer down.
- **Three RaiSE tooling defects**: `rai gate check` exits 0 while reporting failures;
  `rai pattern add` writes nothing while reporting success; `rai graph query` has been broken
  for four epics. All filed in `dev/parking-lot.md`.

## Patterns

Not persisted — `rai pattern add` is a verified no-op. Preserved here:

- A permanently red gate is worse than no gate: it is where the *next* defect hides.
- Proving a test can fail is worth more than writing it. Break a step deliberately and read the
  message.
- A stub that always fails proves degradation, not function. A readiness test needs both paths.
- An unused import can be a fossil of missing work. Ask what a flagged binding was *for* before
  deleting it.
- A skip must name what it did not verify; "skipped" and "passed" look identical in a summary.
