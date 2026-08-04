# E6 Scope — Executive Panel (KPI Dashboard + NL Query)

**Status:** Designed 2026-08-04 — awaiting authorization (Gustavo).
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
