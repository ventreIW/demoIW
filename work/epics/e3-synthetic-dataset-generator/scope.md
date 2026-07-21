# E3 Scope — Synthetic Dataset Generator

## In scope

| Item | Story |
|---|---|
| `GenerationParams` Pydantic model | s3.1 ✅ |
| `ProceduralGenerator` implementing `IDatasetPort` | s3.1 ✅ |
| NumPy seed-based distributions (amount, days overdue, payment patterns) | s3.1 ✅ |
| Faker es_MX synthetic identities | s3.1 ✅ |
| Pandas DataFrame assembly + `RawDataset` output | s3.1 ✅ |
| Unit tests: reproducibility, distribution sanity checks | s3.1 ✅ |
| `OpenRouterAdapter` implementing `ILLMPort` | s3.2 ✅ |
| Retry logic (3 attempts, exponential backoff) | s3.2 ✅ |
| Config-driven model selection per use case (GR-AI-002) | s3.2 ✅ |
| Structured logging for LLM calls (model, tokens, latency) | s3.2 ✅ |
| Integration test with mocked HTTP (no real OpenRouter call in CI) | s3.2 ✅ |
| Prompt template `v1_company_description.txt` | s3.3 ✅ |
| `LLMEnrichmentService` — batched calls, 20 clients/batch | s3.3 ✅ |
| `GenerateDataset` use case — wires procedural + enrichment | s3.3 ✅ |
| Tests: enrichment with mocked LLM port | s3.3 ✅ |
| `POST /api/scenarios/generate` endpoint | s3.4 ✅ |
| `IClientRepository`, `IInvoiceRepository` persistence adapters | s3.4 ✅ |
| ~~"Generar nuevo" frontend form (sector, count, **overdue rate**, seed)~~ → form ships `sector, client_count, invoice_volume, amount_mean, amount_std, seed` | s3.4 ✅ **corrected** — no overdue-rate control exists, and none should: **ADR-004** replaced the global `overdue_rate` knob with per-pattern causal behaviour. Scope line was never updated after the ADR. |
| Loading state + success redirect | s3.4 ✅ |
| `.env.example` updated with `OPENROUTER_API_KEY`, model env vars | s3.2 ✅ |
| ADR-003 (procedural generation choice) | s3.1 ✅ |
| ADR-005 (batched enrichment) | s3.3 ✅ |

## Explicitly out of scope

| Item | Reason |
|---|---|
| Scoring / ML model | E4 |
| Communications generation | E5 |
| NL query | E6 |
| Real-time streaming progress (WebSocket) | Not in backlog; parking lot if desired |

## Acceptance gate checklist

Verified at epic close, 2026-07-20. **One item descoped — see below.**

- [x] `POST /api/scenarios/generate` with `seed=42` called twice returns the same `client_count` and total outstanding — verified by `tests/integration/test_scenario_acceptance_gate.py` (added at close; nothing covered this before)
- [x] Generated scenario appears in `/scenarios` and can be activated — same file
- [ ] **DESCOPED → s4.8:** LLM enrichment runs (company names are not raw Faker names)
- [x] All unit and integration tests pass (pytest + vitest) — 106 backend, 45 frontend, green in CI
- [x] `mypy app/` and `npm run typecheck` pass
- [x] ADR-003 (procedural + LLM hybrid) written — s3.1
- [x] ADR-004 (pattern-driven behavioural model) written — s3.1
- [x] ADR-005 (batched enrichment) written — s3.3
- [x] All 4 story retrospectives written

### Descoped: LLM enrichment against a real model

**Not fulfilled. Not quietly ticked.** The team has no `OPENROUTER_API_KEY`, so the qualitative
half of this epic has only ever run against `respx` mocks.

This is silent by construction: the key defaults to `""`, enrichment degrades gracefully, and
the endpoint returns 201 on LLM failure — so a dead AI subsystem is indistinguishable from a
working one. Owned by **`work/epics/e4-intelligence-engine/stories/s4.8-scope.md`**, which also
covers making that degradation visible.

Same credential blocks **E5** (RF-04 communications) and **E6** (RF-06.3-4 NL query) — three of
six modules, against a 2026-08-14 demo date.

**Until s4.8 runs, do not describe AI enrichment as working.**
