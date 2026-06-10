# E3 Brief — Synthetic Dataset Generator

**Backlog source:** B-03, B-04  
**Status:** Proposed — pending Gustavo authorization  
**Estimated size:** M (~5–7 days)  
**Branch:** `e3-synthetic-dataset-generator` (from `main`, after E2 merges)

---

## Goal

The system can generate a complete, realistic accounts receivable portfolio from seed parameters — clients with sector-appropriate names, invoices with statistically realistic amounts and overdue distributions, payment histories that match behavioral patterns, and qualitative narrative descriptions enriched via OpenRouter.

At the end of this epic, a demo facilitator can click "Generar nuevo," choose sector + parameters, and within ~30 seconds have a fully populated scenario ready for scoring (E4). The three pre-loaded scenario slots (manufacturing, retail, professional services) can also be populated on demand.

This epic also delivers the **OpenRouter adapter** — the first LLM integration in the project. All subsequent LLM-dependent epics (E5 communications, E6 NL query) will reuse this adapter.

---

## Success criteria

| Criterion | Verifiable signal |
|---|---|
| Reproducible generation | Same seed + parameters always produces the same dataset (deterministic) |
| Realistic distributions | Overdue amounts, days overdue, and payment patterns follow configured distributions |
| LLM enrichment runs | Company names and sector descriptions are LLM-generated (not just Faker names) |
| Pre-loaded scenarios populated | Activating any of the 3 seed scenarios and clicking "Generar" fills it with data |
| End-to-end API works | `POST /api/scenarios/generate` with valid params returns a ScenarioSummary within 30 s |
| "Generar nuevo" form works | Frontend form collects sector + parameters, submits, shows progress, activates on completion |
| All tests pass | Procedural generation unit tests + OpenRouter adapter integration tests pass |

---

## Stories

| ID | Title | Size |
|---|---|---|
| s3.1 | Procedural data generation layer | M |
| s3.2 | OpenRouter adapter | S |
| s3.3 | LLM enrichment layer | S |
| s3.4 | Generate scenario endpoint & UI | S |

---

## Dependencies

- E2 must be merged to `main` before this epic branch is created.
- OpenRouter API key must be available in `.env` (team responsibility before s3.2 begins).

## Out of scope

- Scoring / ML model (E4)
- Communications generation (E5)
- NL query (E6)
- Real-time streaming progress (websocket) — loading spinner is sufficient for demo
