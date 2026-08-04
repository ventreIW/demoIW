# E6 Design — Executive Panel

**Date:** 2026-08-04 · **Companion to:** `scope.md` · **ADRs:** 008, 009

---

## Gemba findings

Read before designing: `routers/scenarios.py`, `routers/cases.py`, `application/services/`
(`prioritizer`, `feature_extractor`, `case_aggregate_service`), `domain/entities/`, `ports/`,
`frontend/src/components/layout/MainLayout.tsx`, `frontend/package.json`.

**G1 — `/prioritized` re-scores on every request and never reads the persisted `Score` table.**
`scenarios.py` instantiates `ScoreScenario()` and fits a model inline, while `POST /{id}/score`
(s4.10) writes `Score` rows that nothing reads back. E6 must choose a side rather than inherit the
ambiguity. → ADR-009.

**G2 — Sector cannot segment a portfolio.** `Client` has `sector_description: str | None` (LLM free
text) and no sector field. `Sector` lives on `Scenario` and is one value for the whole scenario.
Confirms the s4.2 parking-lot note ("sector is constant within a scenario"). A sector breakdown is
one bar; the brief's example NL question is unanswerable in a meaningful way. → scope.md §Open
questions, dimension set below.

**G3 — There is no money-denominated record of collections activity.** `ContactResult` has
`result_type` and no amount. `record_contact_result.py` persists the result and triggers a rescore;
it creates no `Payment`. So "recovery rate (actual)" cannot mean "money collected during the demo".
→ KPI formulas below.

**G4 — The composition pattern already exists and should be followed, not reinvented.**
`case_aggregate_service.fetch_case_aggregate()` (s5.4) is a module-level async function taking
repository ports and returning a frozen dataclass, used by both a router and a use case. s6.1's
`kpi_aggregate_service` mirrors it exactly. Likewise `feature_extractor.outstanding_by_client()` is
already the shared definition of unsettled balance — KPI money reuses it (ADR-009), it is not
rewritten.

**G5 — No chart library is installed.** Dependencies are Base UI, Tailwind, lucide, next-intl,
sonner. E5 already paid for JSDOM/Base UI portal friction (PAT-R-11: Select options live in a
portal and are untestable with `getByText` until opened). → §Charting.

**G6 — `?category=High` on `/prioritized` is dead.** `scenarios.py` validates `category` against
`{"High","Medium","Low"}` then compares it to `ScoreCategory` values, which are lowercase.
Every valid input returns an empty portfolio. Two consequences for E6: the KPI category counts must
build from `ScoreCategory` members directly, and s6.3's `score_category` filter must not copy that
comparison. (The bug itself stays parked — it is E5 surface.)

**G7 — `MainLayout.tsx` has a dead `sidebar.executive` link pointing at `#`.** The nav slot for
this epic already exists; s6.2 fills it rather than adding one.

**Module health:** `governance/drift-hotspots.json` absent — check skipped.
**Graph query:** `rai graph query` fails with `OperationalError: no such column: data_json` (index
schema mismatch). No graph-sourced patterns available this session; noted for the parking lot.

---

## Target components

### Backend

```
app/application/services/kpi_aggregate_service.py   NEW  — mirrors case_aggregate_service shape
app/domain/value_objects/portfolio_kpis.py          NEW  — frozen aggregate + bucket VOs
app/domain/value_objects/query_intent.py            NEW  — QueryIntent, Metric, Dimension, Filter
app/application/services/query_executor.py          NEW  — intent → numbers, over the aggregate
app/application/use_cases/answer_nl_query.py        NEW  — translate → execute → narrate → cite
app/routers/executive.py                            NEW  — GET /kpis, POST /query
app/adapters/llm/openrouter_adapter.py              EDIT — s6.0 hardening
prompts/nl_query/v1_translate.txt                   NEW  — question → intent
prompts/nl_query/v1_narrate.txt                     NEW  — numbers → prose
```

### Frontend

```
src/app/[locale]/executive/page.tsx                 NEW
src/components/executive/KpiCard.tsx                NEW
src/components/executive/SegmentationChart.tsx      NEW  — hand-rolled, see §Charting
src/components/executive/QueryBox.tsx               NEW  — s6.4
src/components/executive/QueryAnswer.tsx            NEW  — s6.4, reuses SegmentationChart
src/lib/api/executive.ts                            NEW
src/types/executive.ts                              NEW
src/components/layout/MainLayout.tsx                EDIT — dead '#' link → /executive
messages/{es,en}.json                               EDIT
```

---

## KPI formulas

Every figure below is computed from persisted `Score` rows plus invoices and payments, per ADR-009.
The definitions are stated here so s6.1's design does not have to invent them and so the numbers
are defensible when a director asks how they were derived.

| KPI | Definition | Source |
|---|---|---|
| `total_outstanding` | `sum(outstanding_by_client(invoices, payments))` — open invoices net of partial payments | reuses `feature_extractor` |
| `total_expected_recoverable` | `Σ outstanding_c × score_c / 100` over scored clients | persisted `Score.score_value` |
| `cases_by_category` | count of clients per `ScoreCategory` member | `Score.category` |
| `collected_to_date` | `Σ payments.amount` against invoices with `status == "paid"` | historical |
| `recovery_rate_actual` | `collected_to_date / (collected_to_date + total_outstanding)` | share of the book settled |
| `recovery_rate_expected` | `total_expected_recoverable / total_outstanding` | share of the remainder the model expects |

**On "actual vs. expected" (G3).** These two rates answer different questions and are not a
before/after pair: `actual` is what the book has settled historically, `expected` is what the model
thinks the *unsettled remainder* will yield. Presenting them side by side is honest; labelling
either one "recovery rate" alone is not. s6.2 labels both explicitly in Spanish. This is a reporting
definition, not an implementation detail — flagged for Gustavo in `scope.md` §Open questions.
`collected_to_date` reflects the generator's history, so it will not move when a collector records
a contact result during the demo. Say so in the UI rather than letting the director infer causation.

### Segmentation dimensions

Sector is excluded (G2). The three shipped dimensions all vary within a scenario:

| Dimension | Buckets |
|---|---|
| `days_overdue_bucket` | 1–30, 31–60, 61–90, 90+ (max over open invoices, matching s5.1's per-case rule) |
| `amount_range` | quartiles of client outstanding, computed per scenario |
| `score_category` | high / medium / low, from `ScoreCategory` directly (never the G6 string comparison) |

Each bucket carries `client_count`, `outstanding`, and `expected_recoverable` so one chart component
serves every dimension and every NL `group_by`.

`days_overdue_bucket` uses **max** days overdue over a client's open invoices, not mean — the same
rule s5.1 established, for the same reason (a mean flatters an aged account by averaging it against
recent invoices). Two definitions of "how overdue is this client" across two panels would be a
defect the director finds and we do not.

---

## Key contracts

### `GET /api/v1/scenarios/{id}/kpis`

```jsonc
{
  "scenario": { "id": "...", "name": "...", "sector": "retail" },
  "scored_at": "2026-08-04T12:00:00Z",         // ADR-009: staleness must be visible
  "client_count": 271,
  "total_outstanding": 2841300.0,
  "total_expected_recoverable": 1615400.0,
  "collected_to_date": 934100.0,
  "recovery_rate_actual": 0.247,
  "recovery_rate_expected": 0.568,
  "cases_by_category": { "high": 88, "medium": 121, "low": 62 },
  "segmentation": {
    "days_overdue_bucket": [
      { "bucket": "1-30", "client_count": 74, "outstanding": 612000.0, "expected_recoverable": 421000.0 }
      // ...
    ],
    "amount_range": [ /* same shape */ ],
    "score_category": [ /* same shape */ ]
  }
}
```

`404` scenario not found · `409` scenario has no persisted scores (body names `POST /{id}/score`).

### `POST /api/v1/scenarios/{id}/query`

```jsonc
// request
{ "question": "¿Cuánto está vencido con los clientes de bajo score?" }

// 200
{
  "question": "...",
  "intent": { "metric": "outstanding", "group_by": null,
              "filters": [{ "dimension": "score_category", "operator": "eq", "value": "low" }],
              "limit": null },
  "result": [ { "label": "low", "value": 612000.0 } ],
  "narrative": "En el escenario «Retail Q3», los clientes de score bajo concentran $612,000 ...",
  "citation": { "scenario_id": "...", "scenario_name": "Retail Q3", "scored_at": "..." }
}

// 422 — question outside the vocabulary; body lists supported metrics/dimensions
// 502 — translation unavailable (rate limit / timeout / malformed body)
```

The `intent` is echoed deliberately: the director can see *what was asked of the data*, which is
the difference between a trustworthy answer and an oracle. It also makes translation defects
visible in the demo instead of silent.

### `QueryIntent` vocabulary (ADR-008)

```python
Metric     = outstanding | expected_recoverable | client_count | avg_days_overdue
Dimension  = days_overdue_bucket | amount_range | score_category
Operator   = eq | gt | gte | lt | lte
```

`Filter` validates `dimension` × `value` as a pair — an out-of-range bucket label is a Pydantic
error, not a query returning nothing. The executor is total over `Metric` × `Dimension | None`;
every combination is implemented or raises at construction, so there is no "unhandled combination
returns empty" path (the G6 failure species, and the s5.1 one before it).

---

## Charting

**Hand-rolled SVG/CSS bars in `SegmentationChart.tsx`. No chart library.**

Every visualization E6 needs is a labelled horizontal bar over 3–4 buckets, plus KPI cards that are
formatted numbers. Recharts would add a dependency whose React 19 support is version-sensitive, and
whose `ResponsiveContainer` requires width/height mocking to render at all under JSDOM — after E5
spent real time on Base UI portals in the same test environment (PAT-R-11), that is a cost with a
known shape and no offsetting benefit at this scale.

A `<div>` with a percentage width, or a `<rect>` in an inline `<svg>`, is testable with
`getByText`/`getByRole` and readable in the DOM. If E7 wants a genuine time series, adding a library
then is a small, additive change; removing one after two stories depend on it is not.

Currency formatting uses `es-MX`, not bare `es` — s5.1's finding: bare `es` is Spain and renders
`184.321 MXN` instead of `$184,321`.

---

## Test approach

- **Unit** — `kpi_aggregate_service` against hand-built score/invoice/payment fixtures with figures
  computed by hand, including: zero outstanding, a client with partial payments, and a scenario with
  no scores (must raise, not return zeros).
- **Unit** — `query_executor` exhaustively over `Metric` × `Dimension | None`. The enum surface is
  small enough that "every combination" is a real assertion rather than a sample.
- **Router** — 404 / 409 / 422 / 502 paths asserted by status *and* body content.
- **Translation** — a pinned fixture set of Spanish questions with expected intents, run against a
  **stubbed** `ILLMPort`. No test spends free-tier quota.
- **Frontend** — Vitest with a single shared `vi.mock` reset in `beforeEach` (E5's confirmed
  pattern, PAT-R-12 neighbourhood), fixtures captured from a **real** `curl` against the running
  API, not hand-written from the TypeScript types.

**The last point is the epic's most important process control.** s5.1 shipped a defect through
design, types, component, fixture, and green tests because every layer inherited one wrong
assumption read from the domain classes (`'High'` vs `'high'` — the same species as G6). Capture the
payload during design, not during verification. Two dead filters in one endpoint say the third is
already written.

---

## Sequencing rationale

`s6.0 ∥ (s6.1 → s6.2)` then `s6.3 → s6.4` is ordered by risk and by what survives a schedule cut.

s6.0 is first-or-parallel because it is the only story that protects the demo's headline moment from
an infrastructure failure, and it has been deferred past two epics already (E4 close, E5 close).
Doing it inside s6.3 means debugging adapter behaviour and prompt behaviour at the same time, on a
50-request daily budget.

s6.1 before s6.2 and before s6.3 because both consume it — the NL executor runs against the same
aggregate the dashboard renders (ADR-008), which is what makes the two views incapable of
disagreeing.

s6.3/s6.4 last because they are the cut line. With 10 days to the demo and E7 not started, the
honest failure mode is "the panel shipped without NL query", not "the panel is half-built". This
order guarantees that RF-06.1 and RF-06.2 are complete and demonstrable before any work starts on
RF-06.3.
