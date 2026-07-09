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
| Integration test with mocked HTTP (no real OpenRouter call in CI) | s3.2 |
| Prompt template `v1_company_description.txt` | s3.3 |
| `LLMEnrichmentService` — batched calls, 20 clients/batch | s3.3 |
| `GenerateDataset` use case — wires procedural + enrichment | s3.3 |
| Tests: enrichment with mocked LLM port | s3.3 |
| `POST /api/scenarios/generate` endpoint | s3.4 |
| `IClientRepository`, `IInvoiceRepository` persistence adapters | s3.4 |
| "Generar nuevo" frontend form (sector, count, overdue rate, seed) | s3.4 |
| Loading state + success redirect | s3.4 |
| `.env.example` updated with `OPENROUTER_API_KEY`, model env vars | s3.2 ✅ |
| ADR-003 (procedural generation choice) | s3.1 ✅ |
| ADR-005 (batched enrichment) | s3.3 |

## Explicitly out of scope

| Item | Reason |
|---|---|
| Scoring / ML model | E4 |
| Communications generation | E5 |
| NL query | E6 |
| Real-time streaming progress (WebSocket) | Not in backlog; parking lot if desired |

## Acceptance gate checklist

- [ ] `POST /api/scenarios/generate` with `seed=42` called twice returns the same `client_count` and total outstanding
- [ ] Generated scenario appears in `/scenarios` and can be activated
- [ ] LLM enrichment runs (company names are not raw Faker names)
- [ ] All unit and integration tests pass (pytest + vitest)
- [ ] `mypy app/` and `npm run typecheck` pass
- [x] ADR-003 (procedural + LLM hybrid) written — s3.1
- [x] ADR-004 (pattern-driven behavioural model) written — s3.1
- [ ] ADR-005 (batched enrichment) written — s3.3
- [ ] All 4 story retrospectives written
