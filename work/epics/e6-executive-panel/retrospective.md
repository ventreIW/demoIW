# Retrospective: E6 — Executive Panel (KPI Dashboard + NL Query)

**Designed:** 2026-08-04 · **Stories merged:** 2026-08-04 → 2026-08-11 · **Closed:** 2026-08-20
**Stories:** s6.0–s6.4, 5 of 5 delivered · **Backlog:** B-12, B-13

## Summary

E6 gave the finance director (P-02) a portfolio view: a KPI dashboard with segmentation, and a
natural-language query layer that answers plain questions with a chart, a narrative, and a
citation of the active scenario. All five stories merged inside eight days, and M3 — the full
P-02 loop, dashboard → ask → chart + narrative + citation — was demoable on 2026-08-11.

The epic then sat unclosed for nine days on M4, its own mandatory verification checkpoint.
Closing it required a separate session that found and fixed five defects on the path M4 was
supposed to check.

## Milestones

| Milestone | Status | Note |
|---|---|---|
| M1 — aggregate + hardened adapter | ✅ | s6.0 + s6.1, 2026-08-04 |
| M2 — panel demonstrable | ✅ | s6.2, 2026-08-07, ahead of the 08-09 cut-line condition |
| M3 — NL query | ✅ | s6.3 + s6.4, 2026-08-11. Cut line resolved: not cut |
| **M4 — E2E checkpoint** | **⚠ 3 of 4** | See below |

### M4 — what was verified, and what was not

| Item | Status | Evidence |
|---|---|---|
| Full path verified against a running app | ✅ | `test_e2e_demo_flow.py` (s7.4) — ten steps through the real ASGI app and real repositories, 1.41s |
| Frontend consumes each API with **real** payloads | ✅ | Real payloads captured and structurally diffed against `src/test-utils/*-fixture.ts`; KPIs, CaseDetail, PrioritizedCase and Portfolio all match, 0 drift |
| **NFR-02 measured, not assumed** | ✅ | `test_nfr02_performance.py` — priority queue **0.222s** and KPI dashboard 0.134s at 500 clients / 2,073 invoices, against a 3s budget |
| Retrospectives + parking-lot follow-ups | ✅ | s6.0–s6.4 all written; 4 resolutions marked and 5 new items filed 2026-08-20 |
| **Real-PostgreSQL run** | ❌ **OPEN** | No PostgreSQL on this host — port 5432 refused, `apt install` needs a password only the developer can supply |

**NFR-02 deserves a note.** s6.2 deferred it citing "no Postgres". It never needed Postgres — it
needed a scenario at the stated size and a clock. The deferral was inherited from a neighbouring
blocker rather than examined, and it cost nine days of a "mandatory" item being open for a
measurement that took four minutes and passed with 12.5× headroom.

## The real finding: M4 was right, and the cost of deferring it was five defects

E6's scope declared M4 mandatory on the grounds that "E4's M4 caught a generation-layer bug no
unit test saw, and E5's M4 repeated the lesson." Closing it produced the third and largest
instance. Five defects were found on the demo path, all of them invisible to 546 passing tests:

| Bug | Severity | What it was |
|---|---|---|
| BUG-01 | S1 | Production build red for 13 days; CI red on every push since 2026-08-07 and normalized |
| BUG-02 | S2 | `/prioritized?category=` matched nothing in **any** casing — hidden by a test that asserted inside a loop over an empty list |
| BUG-03 | S1 | CSV scenarios unscorable — `status="pending"` matched no consumer; **partial**, BUG-06 escalated |
| BUG-04 | S2 | Pinned `reference_date` crashed persist, silently guaranteeing the non-reproducibility it exists to prevent |
| **BUG-05** | **S1** | **Scoring was non-deterministic under a fixed seed** |

**BUG-05 is the one that matters for this epic.** Two `POST /generate` calls with `seed=42`
produced different models and different portfolios. Every component was individually and
verifiably seeded; the defect was in the coupling — `add_many` overwrote the generator's
reproducible client id with `uuid4()`, and two consumers applied seeded or positional
operations along an axis sorted by that now-random id. *A seeded draw applied along an unseeded
axis is not seeded.*

It had survived four epics. ADR-006 and ADR-007's measured ROC-AUC figures of 0.732–0.739
presuppose a reproducible pipeline and were measured on one that was not. Fixed under ADR-011
with `generation_index` as an explicit persisted ordering key.

And it was found **by accident** — BUG-02's verification printed the category tally twice, and
the two lines disagreed. Nobody was looking for it.

## What went well

**The cut line worked as designed.** s6.3/s6.4 were declared a schedule cut line rather than a
hope, with an explicit condition (M2 by 2026-08-09). M2 landed on 08-07, the condition was
evaluated rather than forgotten, and the resolution was written down on 08-11. Compare the
"demo date is 2026-08-14" risk in the same table, which was framed against a fixed date that
turned out to be movable and therefore never fired.

**s6.3's live verification was worth more than its 541 tests.** It spent one real model call
and found that the reasoning model was returning its entire chain of thought as the
director-facing narrative — with every stubbed test green, because a stub returns whatever
prose it is handed. That produced the `RESPUESTA:` marker, and s7.4 now asserts the extraction
strips the reasoning trace, so the lesson is a regression guard rather than a docstring.

**ADR-009's visible staleness held up.** Surfacing `scored_at` rather than silently reconciling
the queue's fresh fit with the dashboard's persisted scores was the right call, and the field
is now asserted in the E2E path.

## What to improve

**A deferral needs a reason of its own.** NFR-02 was deferred for a blocker it did not have.
"Deferred, no Postgres" was carried forward across stories without anyone re-testing whether
Postgres was actually the obstacle. A deferred item should record *what specifically is
missing*, so the next reader can check whether it is still true.

**A gate that cannot fail is worse than no gate, and this epic had three.** `rai gate check`
exits 0 even while printing `FAILED: 5 of 15 gates failed`. `scripts/lint.sh` short-circuits on
the frontend, so backend `ruff` never ran while eslint was red. And CI was red on every push
since 2026-08-07, which made red the expected state and destroyed its signal — that is
precisely how s7.2 added two more lint errors without anyone noticing.

**Parking a known failure without pinning it is what caused BUG-01.** s6.2's decision to park 8
eslint errors was locally reasonable and globally expensive: it converted a binary gate into a
known-red baseline carrying zero information. Either fix the failure or pin it so the gate
returns to green and can fail meaningfully again.

## Patterns

`rai pattern add` reports success and writes nothing — verified this session (no DB, no JSONL,
no file under `.raise/`). Nothing was persisted. Preserved here:

- A seeded draw applied along an unseeded axis is not seeded. Audit the *ordering*, not only
  the RNG. Determinism is a property of a pipeline, not of its components.
- A gate allowed to stay red stops being a gate; the real defect is the second one that
  entered while the gate was dark.
- When a defect is a pattern rather than a typo, fixing the first occurrence is how you find
  the second — BUG-05 needed two fixes, and the second was invisible until the first landed.
- A deferral inherits its predecessor's stated blocker unless someone re-checks it.

## Learning chain

Empty, for the fourth consecutive epic. `.raise/rai/learnings/` does not exist; `rai graph
query` fails with `no such column: data_json`; `rai signal query` returns nothing for any
phase. Acceptance rate, gap rate and pattern utility are **undefined rather than zero** — no
patterns were primed, none were retrievable, and none are writable.

## Status at close

**E6 is closed with M4's real-PostgreSQL run OPEN**, on an explicit decision (Rodrigo,
2026-08-20) rather than by omission.

What has changed since the previous five deferrals is that the gap is now executable and loud
instead of a sentence in a docstring. `backend/tests/test_e2e_demo_flow.py` contains the
harness; every run prints that M4 is unverified, names the five stories that deferred it, and
states that a skip is an open gate and not a pass. It runs on one command:

```bash
export DEMOIW_TEST_POSTGRES_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/demoiw_test
cd backend && .venv/bin/pytest tests/test_e2e_demo_flow.py -k postgres -v
```

It now also covers migration `0004` (added by BUG-05), whose `ROW_NUMBER() OVER (PARTITION BY
…)` backfill has never executed against any database — no test in this project has ever run an
Alembic migration, because `conftest.py` builds the schema with `Base.metadata.create_all`.

**Carried forward:** BUG-06 (needs an ADR on scoring unlabelled uploads), the 13 `format:check`
failures with the gate absent from CI, and the three RaiSE tooling defects above. All filed in
`dev/parking-lot.md`.
