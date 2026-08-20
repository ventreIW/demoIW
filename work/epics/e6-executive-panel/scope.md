# E6 Scope — Executive Panel (KPI Dashboard + NL Query)

**Status:** **CLOSED 2026-08-20** — 5 of 5 stories delivered; M4 verified 3 of 4 with the real-PostgreSQL run open by explicit decision. See `retrospective.md`.
**Backlog:** B-12, B-13 · **Stories:** s6.0–s6.4 · **Size:** L
**Branch model:** logical container; stories branch from `main`.
**Designed after:** E5 closed (`87b1b85`).

## Objective

Give the finance director (P-02) a portfolio-intelligence view: a KPI dashboard that states what
the book is worth and where the value sits, and a natural-language query layer that answers plain
questions about it with a chart, a narrative, and a citation of the active scenario.

## Value

E4 produced the intelligence and E5 made it actionable for one collector at a time. E6 is the first
surface that shows the *portfolio* — the view that justifies the system to the person who funds it.
The NL query is the demo's headline moment.

## In scope (MUST)

| Item | Story | New surface |
|---|---|---|
| OpenRouter adapter hardening — missing `choices` and `ReadTimeout` degrade to `ExternalServiceError` → 502, not `KeyError`/500 | s6.0 | `adapters/llm/openrouter_adapter.py` |
| KPI aggregation API — total overdue, expected recoverable, counts by category, recovery rate, segmentation buckets | s6.1 | **new** `GET /api/v1/scenarios/{id}/kpis` + `kpi_aggregate_service` |
| Executive dashboard — KPI cards + segmentation charts, ES-first | s6.2 | **new** `/[locale]/executive` page + chart components + api client |
| NL query API — question → constrained `QueryIntent` → safe execution → narrative + citation | s6.3 | **new** `POST /api/v1/scenarios/{id}/query` + intent model + builder + prompt template |
| NL query UI — question input, result chart (reuses s6.2 components), narrative, citation | s6.4 | frontend flow on the executive page |

## SHOULD

- Executive sidebar link stops pointing at `#` (`MainLayout.tsx` currently has a dead
  `sidebar.executive` entry awaiting this epic).
- KPI response carries `scored_at` so a stale dashboard is visible rather than silently wrong
  (ADR-009).

## Out of scope

| Item | Reason / destination |
|---|---|
| Converging `/prioritized` onto persisted scores | ADR-009 — correct end state, wrong week. E7/E8. |
| **Sector as a segmentation dimension** | Structurally impossible today — see Gemba G2 and §Open questions. Not deferred work; a spec correction. |
| Write-back or actions from NL query | Read-only analytics per brief |
| English translation pass, PWA, accessibility audit | E7 |
| Saved dashboards, drill-through, export | Beyond demo needs; parking lot |
| Real-Postgres E2E verification | Standing environment blocker inherited from E4 → E5. E7. |

## Architecture decisions

| ADR | Decision |
|---|---|
| [ADR-008](../../../dev/decisions/adr-008-nl-query-constrained-intent.md) | NL query translates to a constrained `QueryIntent` over an allow-listed vocabulary. The LLM never emits SQL and no model string reaches the database. |
| [ADR-009](../../../dev/decisions/adr-009-kpi-reads-persisted-scores.md) | KPIs read persisted `Score` rows; no on-demand rescore. 409 when unscored. Money reuses `outstanding_by_client()`. |

Charting is **not** an ADR — see `design.md` §Charting. Hand-rolled SVG/CSS, no new dependency.

## Stories

| ID | Title | Size | Depends on |
|---|---|---|---|
| s6.0 | OpenRouter adapter hardening | XS | — |
| s6.1 | KPI aggregation — backend | S | E4 s4.10 persisted scores (done) |
| s6.2 | Executive dashboard + segmentation — frontend | M | s6.1 |
| s6.3 | NL query — backend (intent + safe execution) | M | s6.1, s6.0 |
| s6.4 | NL query — frontend | S | s6.2, s6.3 |

Execution: `s6.0 ∥ (s6.1 → s6.2)`, then `s6.3 → s6.4`.

s6.1 is the hub: s6.2 renders its aggregate and s6.3 executes intents *against* it (ADR-008), so
the dashboard and the NL answer cannot disagree. The two tracks are parallelizable across the
backend/frontend split that worked in E5.

## Done when

- [ ] Dashboard shows total overdue, expected recoverable, cases by category, recovery rate (RF-06.1)
- [ ] Breakdown by ≥2 dimensions that actually vary within a scenario (RF-06.2) — days-overdue
      bucket, amount range, score category
- [ ] A plain-language question is translated into a validated structured intent and executed (RF-06.3)
- [ ] Answer returns a chart **and** a narrative computed from the same numbers (RF-06.3)
- [ ] Every NL response cites the active scenario by name and id (RF-06.4)
- [ ] Dashboard renders within NFR-02 budget at 500 clients / 2,000 invoices
- [ ] An unscored scenario produces an actionable empty state, not zeros (ADR-009)
- [ ] Translation failure produces an honest "cannot answer" with supported vocabulary — never a
      fabricated number and never a raw query (ADR-008)
- [ ] `pytest` + `vitest` green; no TypeScript errors; OpenAPI schema valid
- [ ] All story retrospectives written; epic retrospective written

## Risks

| Risk | L | I | Mitigation |
|---|---|---|---|
| NL translation quality on a free-tier model — plausible questions map to wrong intents | M | H | Intent is a small enum surface, so wrong ≠ unsafe. s6.3 pins a fixture set of questions with expected intents as tests. s6.4 surfaces example questions so the director stays inside the vocabulary. |
| OpenRouter 50 req/day cap exhausted mid-demo | M | H | s6.0 hardening + dashboard works with zero LLM calls. NL failure degrades to a working KPI view. |
| Demo date is 2026-08-14 — 10 days, and E7 has not started | H | H | s6.0/s6.1/s6.2 deliver a complete RF-06.1–06.2 panel on their own. If time runs out, s6.3/s6.4 are the cut line, not a half-built dashboard. Sequence protects that. |
| Timestamp divergence between queue (fresh fit) and dashboard (persisted run) | M | M | ADR-009: surface `scored_at` in the UI. Visible staleness over silent inconsistency. |
| Segmentation reads as thin because the generator's amounts are not heavy-tailed | M | M | Known and measured (parking lot, 2026-07-21): top 20% of clients hold ~40% of value. Report measured concentration; do not claim Pareto. |

## Open questions

1. **RF-06.2 names "sector" as a segmentation dimension; the data model cannot express it.**
   `Sector` is an attribute of `Scenario`, not `Client` — every client in a scenario shares one
   sector (`domain/entities/client.py` has only free-text `sector_description`). A sector breakdown
   would be a single bar, and the brief's example question "¿Cuánto está vencido en retail?" would
   return either the whole portfolio or nothing. RF-06.2 says "e.g.", so shipping three other
   dimensions satisfies it. **Confirm with Gustavo** that this reading is accepted, or a per-client
   sector becomes an E3 generator change with fixture impact.

2. **"Recovery rate (actual vs. expected)" has no money-denominated actual.** `ContactResult`
   carries a `result_type` and no amount; `Payment` rows are the generator's history, not demo
   actions. Proposed definition in `design.md` §KPI formulas. **Needs Gustavo's confirmation** —
   it is a reporting definition, not an implementation detail.

3. Standing from E4: maximise-recovery vs. prevent-write-offs in queue ordering, and nobody in
   collections has read the Spanish copy. Both now also apply to the director-facing narrative
   text s6.3 generates.

---

## Story sequence

> Added by `/rai-epic-plan` — 2026-08-04

| # | Story | Size | Depends on | Rationale | Unblocks |
|---|---|---|---|---|---|
| 1 | s6.0 OpenRouter adapter hardening | XS | — | **Risk-first.** Deferred past two epic closes; the only story protecting the demo's headline moment from a free-tier hiccup. Doing it inside s6.3 means debugging adapter and prompt behaviour simultaneously on a 50-request daily budget | s6.3 |
| 1 | s6.1 KPI aggregation — backend | S | E4 s4.10 persisted scores (done) | **The hub.** Both s6.2 and s6.3 consume this aggregate (ADR-008), which is what makes the dashboard and the NL answer incapable of disagreeing. Parallel with s6.0 — different files, no shared surface | s6.2, s6.3 |
| 2 | s6.2 Executive dashboard — frontend | M | s6.1 | Completes RF-06.1 + RF-06.2 on its own. After this the epic has a demonstrable executive panel even if nothing else lands | s6.4 |
| 3 | s6.3 NL query — backend | M | s6.1, s6.0 | **Highest-risk story** (translation quality on a free-tier model + safety surface). Sequenced after the panel is demonstrable so its risk cannot take the epic down with it | s6.4 |
| 4 | s6.4 NL query — frontend | S | s6.2, s6.3 | Reuses s6.2's chart component; adds question box, narrative, citation | — |

**Critical path:** s6.1 → s6.2 → s6.4, with s6.3 joining before s6.4. s6.0 runs beside s6.1 and only gates s6.3.

**Sequencing strategy:** risk-first for s6.0, dependency-driven for s6.1, then *cut-line-first* for the rest — see M3 below. This is not the usual "hardest thing first": with 10 days to the demo the ordering optimises for **what survives a schedule cut**, and a complete RF-06.1/06.2 panel is worth more than a half-built RF-06.3.

## Parallel work streams

```
Backend-led    s6.1 ──┬────────────────▶ s6.3 ─────┐
                      │                            ├─▶ s6.4
Frontend-led          └─▶ s6.2 ──────────────────  ┘

Independent    s6.0 ──────────────────▶ (gates s6.3)
```

s6.0 and s6.1 start together — separate files (`adapters/llm/` vs `application/services/`), no shared
surface. After s6.1 merges, s6.2 (frontend) and s6.3 (backend) are the E5 split that worked.

**Merge points:** s6.1 lands the aggregate contract both tracks build on. s6.3's response contract
must be agreed with s6.4's author *at s6.3 design time*, not at integration — E5's s5.4→s5.5 ID
propagation bug is what that costs when it slips.

## Milestones

### M1 — Aggregate + hardened adapter
**Stories:** s6.0, s6.1 · **Target:** 2026-08-06
- [ ] `GET /{id}/kpis` returns every RF-06.1 figure plus three segmentation dimensions
- [ ] Unscored scenario returns 409 naming `POST /{id}/score` — not a dashboard of zeros (ADR-009)
- [ ] Money figures come from `outstanding_by_client()`, not a second definition
- [ ] Adapter returns `ExternalServiceError` → 502 on missing `choices` and on `ReadTimeout`; neither raises `KeyError` nor 500
- [ ] Real payload captured with `curl` and committed as the frontend fixture source
**Demo:** `curl` the KPI endpoint against a scored scenario.

### M2 — Executive panel is demonstrable
**Stories:** + s6.2 · **Target:** 2026-08-09
- [ ] KPI cards render total overdue, expected recoverable, counts by category, both recovery rates
- [ ] Segmentation charts for days-overdue bucket, amount range, score category
- [ ] `scored_at` visible, so a stale dashboard is legible rather than silently wrong
- [ ] Unscored scenario shows an actionable empty state with a "score this scenario" action
- [ ] Sidebar `executive` link goes to the page instead of `#`; `es.json`/`en.json` key parity held
**Demo:** RF-06.1 + RF-06.2 complete. **This is the point after which E6 is worth showing.**

### M3 — NL query (the cut line)
**Stories:** + s6.3, s6.4 · **Target:** 2026-08-12
- [x] A Spanish question is translated into a validated `QueryIntent` and executed against the s6.1 aggregate (s6.3)
- [x] Answer returns a chart and a narrative computed from the same numbers (s6.3 backend + s6.4 chart/narrative UI)
- [x] Every response cites the active scenario by name and id (RF-06.4)
- [x] Out-of-vocabulary questions return an honest "cannot answer" listing what is supported — never a fabricated number, never a raw query
- [x] Translation failure degrades to a working KPI view, not a blank page
**Demo:** the full P-02 loop — dashboard → ask a question → chart + narrative + citation. **Demoable 2026-08-11 (M3 complete).**

~~**If the schedule slips, this milestone is what gets cut**, and M2 is what ships.~~

**Resolved 2026-08-11 — M3 is NOT cut.** M2 landed 2026-08-07, inside the 08-09 condition, and the
2026-08-14 demo date turned out to be movable (confirmed by Rodrigo). The cut line was built on a
fixed date that does not exist, so it never fired. E6 runs to completion: s6.3 → s6.4 → M4.

### M4 — E2E integration checkpoint + epic close
**Stories:** none new — verification only. **(Mandatory: E4's M4 caught a generation-layer bug no unit test saw, and E5's M4 repeated the lesson.)** · **Target:** 2026-08-13
- [x] Full path verified against a running app — `test_e2e_demo_flow.py` (s7.4), ten steps, 1.41s
- [x] Frontend consumes each new API with **real** payloads — real payloads captured and
      structurally diffed against `src/test-utils/*-fixture.ts`; 4 of 4 surfaces match, 0 drift
- [x] NFR-02 measured, not assumed — **0.222s** priority queue at 500 clients / 2,073 invoices
      against a 3s budget (`test_nfr02_performance.py`). It never needed Postgres
- [x] All story retrospectives written; parking-lot follow-ups filed 2026-08-20; epic
      retrospective written
- [ ] ⛔ **Real-PostgreSQL run — OPEN.** No PostgreSQL on this host. Harness written and ready
      (`postgres_client` fixture + 3 tests incl. migration 0004 up/down/up); skips loudly on
      every run. Epic closed with this open by explicit decision (Rodrigo, 2026-08-20)

## Progress tracking

|| Story | Owner | Status | Started | Merged | Notes ||
||---|---|---|---|---|---|---|
|| s6.0 | — | **done** ✓ | 2026-08-04 | 2026-08-04 | Hardened OpenRouterAdapter: missing/empty choices + ReadTimeout now raise ExternalServiceError → 502. 3 new tests, 453 total. Integration test confirms 502 path. |
|| s6.1 | Rodrigo | **done** ✓ | 2026-08-04 | 2026-08-04 | Gemba cut the composition from five repos to two — `get_raw_dataset()` already returns the DataFrames `outstanding_by_client()` consumes. 38 new tests, 450 total. Verified live at 149 ms on 120 clients; payload captured as `s6.1-payload.json` for s6.2 to type against |
|| s6.2 | — | **done** ✓ | 2026-08-06 | 2026-08-07 | Typed from `s6.1-payload.json` as instructed — no enum-case seam bug. 4 KPI cards, 3 hand-rolled CSS charts (no new dependency), 409-unscored CTA per ADR-009, `scored_at` visible, sidebar link wired. 133/133 frontend tests, `tsc` clean. **AC3 (NFR-02 at 500 clients) unverified — no Postgres.** Retrospective 2026-08-11 |
|| s6.3 | Rodrigo | **done** ✓ | 2026-08-11 | 2026-08-11 | Constrained-intent NL query per ADR-008. Security is structural — `execute()` takes a `QueryIntent`, which cannot hold a non-enum string, so there is no check to forget. 92 new tests (545 total), zero spending quota. **Live-verified 9/9** on the real free-tier model incl. 3 correct refusals and an injection attempt. Live run found what no stub could: the reasoning model returned its chain of thought as the narrative — fixed with a `RESPUESTA:` marker contract. ADR-008 amended (drops `avg_days_overdue` and `limit`). **Real-Postgres E2E still open** |
||| s6.4 | — | **done** ✓ | 2026-08-11 | 2026-08-11 | NL query frontend. `NlQueryPanel` on the executive page: POST to `/query`, renders chart (hand-rolled, reuses s6.2 idiom) + narrative + citation for answerable=true; honest refusal with examples from API `supported` vocabulary (no hardcoded list) for answerable=false; null narrative renders chart without paragraph; 409 reuses unscored CTA. 151/151 frontend tests, tsc/lint/format clean. Live E2E open — no Postgres. Retrospective written. **M3 complete** |

## Sequencing risks

| Risk | L/I | Mitigation |
|---|---|---|
| **10 days to demo and E7 has not started.** This plan consumes 9 of them; E7 (English pass, PWA, accessibility, real-Postgres E2E) has effectively no room | H/H | M3 is a declared cut line, not a hope. If M2 lands by 2026-08-09, decide there whether E6 finishes or E7 starts — do not discover it on the 12th |
| s6.3 translation quality is unknown until an LLM is in the loop; a free-tier model may map plausible Spanish questions to wrong intents | M/H | The intent surface is a small enum, so wrong ≠ unsafe. s6.3's design pins a fixture set of questions with expected intents as tests against a **stubbed** port — no test spends quota. s6.4 shows example questions so the director stays inside the vocabulary |
| Two open questions (sector segmentation, recovery-rate definition) are unanswered by Gustavo and both touch s6.1 | M/M | Both are stated as assumptions in §Open questions with the reasoning written down. Each is one formula or one dimension list in a single service — reversible in an hour if the answer differs. Not blocking |
| s6.1 balloons — six KPIs, three dimensions, a new service | M/M | It composes existing repos and reuses `outstanding_by_client()`; no new persistence, no model fitting. Sized S deliberately. If it exceeds that, the segmentation dimensions are the part to defer, not the KPIs |
| Plans are hypotheses | — | Re-sequence at M1 if the aggregate proves harder than sized, or if s6.0 uncovers more adapter damage than the two known defects |
