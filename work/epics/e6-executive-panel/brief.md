# E6 Brief — Executive Panel (KPI Dashboard + NL Query)

**Backlog source:** B-12, B-13
**Status:** Proposed — not yet authorized
**Estimated size:** L (~7–10 days)
**Branch model:** logical container; stories branch from `main` after E5 merges

---

## Goal

Give the finance director (P-02) a portfolio-intelligence view. A **KPI dashboard** surfaces
total overdue, expected recoverable value, cases by category, and recovery rate (actual vs.
expected), plus **segmentation** by at least two dimensions (sector, days-overdue bucket, amount
range). A **natural-language query layer** lets the director ask a plain question ("¿Cuánto está
vencido en retail?"), translates it to a safe structured query, and answers with a visualization
and a narrative that **cites the active scenario**.

The NL query is the demo's headline moment — the "ask your data anything" wow — so it gets its
own focused stories with careful safety design.

---

## Success criteria

| Criterion | Verifiable signal | RF |
|---|---|---|
| Portfolio KPIs | Dashboard shows total overdue, expected recoverable, cases by category, recovery rate | RF-06.1 |
| Segmentation | Breakdown by ≥2 dimensions (sector / days-overdue bucket / amount range) | RF-06.2 |
| NL → query | A plain question is translated into a structured DB query and executed | RF-06.3 |
| Answer with viz + narrative | Result returned as visualization + narrative explanation | RF-06.3 |
| Data-source citation | NL responses cite the active dataset/scenario | RF-06.4 |
| Performant | Dashboard loads within NFR-02 limits for a 500-client / 2,000-invoice scenario | NFR-02 |

---

## Stories

| ID | Title | Size | Notes |
|---|---|---|---|
| s6.1 | KPI aggregation — backend | S | Portfolio metric endpoints (overdue, recoverable, category counts, recovery rate) |
| s6.2 | KPI dashboard + segmentation — frontend | M | Dashboard UI + segmentation charts (ES-first) |
| s6.3 | NL query — backend (NL→SQL, safe execution) | M | OpenRouter translates question → read-only parameterized query; narrative + citation |
| s6.4 | NL query — frontend | S | Query input, result visualization + narrative display |

---

## Execution order

```
s6.1 → s6.2
s6.3 → s6.4
```

The KPI track (s6.1→s6.2) and the NL track (s6.3→s6.4) are independent and parallelizable. s6.3
needs the OpenRouter adapter (s3.2).

## Dependencies

- **E4** — scores + expected recoverable value feed the KPIs.
- **E5** — recorded contact results / payments feed *recovery rate (actual vs. expected)*.
- **E3 · s3.2 (OpenRouter adapter)** — required for NL→query translation (s6.3).
- **s4.1** — i18n foundation.

## Risks

- **HIGH RISK — NL→SQL safety.** LLM-generated queries must be **read-only, parameterized, and
  scoped to the active scenario**; never execute raw model output. Design an allow-listed query
  surface or a constrained query builder, not free-form SQL. This is the single biggest risk in
  the epic and should be shaped with `/rai-research` before design.
- **KPI correctness** — "expected recoverable value" and "recovery rate" definitions must trace to
  RF-06.1 unambiguously; agree formulas at design time.

## Out of scope

- Write-back or actions from NL query (read-only analytics)
- PWA, accessibility, English translation (E7)
- Advanced BI (drill-through, saved dashboards) — beyond demo needs
