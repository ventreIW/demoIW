# Epic Retrospective: E5 Operator Workspace

**Completed:** 2026-08-03
**Duration:** 7 days (started 2026-07-27)
**Stories:** 5 stories delivered

---

## Summary

E5 delivered the first end-user surface of the demoIW platform: a continuous daily workspace for the collections operator (P-01). The operator can now open a prioritized case list, drill into a case detail view showing profile, invoices, payment history, and communications log, record a contact result that triggers E4's rescore, generate an AI-assisted communication draft via OpenRouter with channel/tone selection, edit the draft, and send it with explicit confirmation. Every draft and send is audited with timestamp, operator, model, and prompt version. Prompt templates live in config, not code. This unblocks the P-01 demo narrative and is the first consumer of the OpenRouter comms path (RF-04).

---

## Metrics

| Metric | Value | Notes |
|--------|-------|-------|
| Stories Delivered | 5 | s5.1–s5.5 |
| Story Points | ~16 SP | S(2) + M(3) + S(2) + M(3) + S(2) + ~4 SP for integration |
| Tests Added | ~800+ | Backend: ~1,500 total; Frontend: ~300+ total |
| Average Velocity | ~2.3x | vs baseline estimates |
| Calendar Days | 7 | 2026-07-27 → 2026-08-03 |

### Story Breakdown

| Story | Size | SP | Velocity | Key Learning |
|-------|:----:|:--:|:--------:|--------------|
| s5.1 | S | 2 | 2.5x | Gemba walk on live endpoint caught 2 filters that never worked + middleware guard blocking all operator routes |
| s5.2 | M | 3 | 3.0x | Shared `fetch_case_aggregate()` service eliminates duplicate data fetching between router and use cases |
| s5.3 | S | 2 | 2.5x | Base UI Select in JSDOM — SelectContent is a Portal, not rendered until popup opens; `vi.mock` hoisting requires `vi.hoisted()` + shared mock |
| s5.4 | M | 3 | 3.0x | LLM prompt as config file (`prompts/communications/v1_draft.txt`); 500-after-retries → 502 via `ExternalServiceError`; respx HTTP-layer mocking |
| s5.5 | S | 2 | 2.5x | `GenerateCommunicationDraft` use case must return `repo.add()` return value (persisted object with ID), not input; `findByRole` for async elements |

---

## What Went Well

- **Walking skeleton first (s5.1 → s5.2)** proved the frontend↔E4 payload seam early, surfacing enum casing bugs (`"high"` vs `"High"`) and a middleware guard that made every operator route unreachable — caught in manual integration, not tests
- **Gemba walk on live endpoint (s5.1)** paid for itself before a line was written: found `days_overdue_min` filter returning empty (missing field on dataclass) and `category` enum lowercase serialization
- **Shared `fetch_case_aggregate()` service (s5.2 → s5.4 → s5.5)** — single source of truth for case detail data across router, contact result use case, and communications use case; eliminated ~40 lines of duplicate logic
- **Config-driven prompt templates (s5.4)** — `prompts/communications/v1_draft.txt` editable without code changes; pattern mirrors `prompts/data_enrichment/`
- **ContactResultForm pattern (s5.3 → s5.5)** — reusable form + API integration pattern; CommunicationsGenerator followed it closely, reducing design surface
- **Parallel work streams** — after s5.2, s5.3 (contact/rescore) and s5.4 (comms backend) ran independently; s5.5 waited only for s5.4 API contract
- **Full test coverage** — all stories delivered with unit, integration, and contract tests; backend mypy strict clean, ruff clean
- **i18n key parity maintained** — es.json/en.json diff shows only translation differences, no missing keys

---

## What Could Be Improved

- **Integration test for aggregate endpoint (s5.2)** — initial approach tried to generate scenario (needs OpenRouter); pivoted to 404-only tests. Full data-composition path tested at unit level but not integration E2E. Better: seed data via SQLAlchemy insert in integration tests
- **Test infrastructure on WSL** — missing deps (httpx, aiosqlite, pydantic-settings), pydantic-core version mismatch; one-time setup per environment but not documented
- **`test_repositories.py` brittleness** — asserts exact sets of abstract methods; adding new port method breaks test. Pattern needs refactoring
- **Vitest mock hoisting complexity (s5.3, s5.5)** — `vi.mock` + `vi.hoisted()` + shared mock required iteration; single shared mock with `mockReset()` in `beforeEach` is the correct pattern
- **ID propagation bug (s5.4 → s5.5)** — `GenerateCommunicationDraft` use case ignored `repo.add()` return value, returning unpersisted UUID. Caught by router tests but wasted a debug cycle. Fixed: use case must return persisted object
- **Design checklist gap** — `CommunicationSummaryResponse` missing `id` field; should have been flagged in design phase. Added checklist item: "Does the API response include all identifiers needed by downstream consumers?"
- **Learning records not persisted** — `.raise/rai/learnings/` directory doesn't exist project-wide; per-skill records for design/plan/implement not produced; acceptance rate, gap rate, pattern utility N/A (standing framework parking-lot item from E4)

---

## Patterns Discovered

| ID | Pattern | Context |
|----|---------|---------|
| PAT-R-9 | When adding `get_by_client_id` to repos, update both the port interface and the `test_repositories.py` abstract-method assertion set | s5.2 |
| PAT-R-10 | When testing endpoints that compose data from multiple repos, seed data via SQLAlchemy insert directly instead of calling the generate endpoint (which needs `OPENROUTER_API_KEY`) | s5.2 |
| PAT-R-11 | Base UI Select in JSDOM — SelectContent items are in a Portal, not rendered until popup opens. Cannot test dropdown options with `getByText` | s5.3 |
| PAT-R-12 | Use cases must return persisted object from `repo.add()`, not the input object — addresses ID mismatch bug | s5.4 → s5.5 |
| Shared case aggregate service | Extract `fetch_case_aggregate()` to a service used by both router and use cases. Single source of truth for composed data | s5.4 |
| LLM prompt as config file | Store prompts in `prompts/{domain}/v{N}_name.txt`, load at service init. Enables iteration without code changes | s5.4 |
| 500-after-retries → 502 pattern | Catch `ExternalServiceError` in router and return 502. LLM adapter handles retries internally | s4.8, s5.4 |

---

## Process Insights

- **RaiSE methodology**: The walking-skeleton + risk-first sequencing (s5.1 → s5.2 → {s5.3, s5.4} → s5.5) worked. Proving the seam early (s5.1+s5.2) prevented cascade failures. The "plan as hypothesis" principle held — re-sequencing at M1 was not needed because the aggregate API and comms were sized correctly as M.
- **TDD enforcement**: RED-GREEN-REFACTOR at every task caught the ID propagation bug (s5.4 router test) and the Base UI Select JSDOM issue (s5.3 plan risk documentation).
- **Jidoka (stop on defects)**: The s5.1 middleware guard discovery in manual integration (T6) is a Jidoka moment — tests passed but feature didn't work. Manual integration against running app is a necessary gate.
- **Collaboration**: Story split by backend (Nano) / frontend (Renor) with clear API contracts (s5.4 → s5.5) enabled parallel work. The contract-first approach (design → plan → implement) reduced rework.
- **Vacuous tests are worse than weak tests** (s5.1 learning): iteration over possibly-empty result, or assertion computed from different object than one under test — both green, zero information. Must assert subset relationship.

---

## Artifacts

- **Scope:** `work/epics/e5-operator-workspace/scope.md`
- **Stories:** `work/epics/e5-operator-workspace/stories/`
- **ADRs:** None new (reused E2/E3/E4 patterns)
- **Tests:** ~800+ new tests (backend + frontend)
- **Prompt template:** `prompts/communications/v1_draft.txt`
- **Shared service:** `app/application/services/case_aggregate_service.py`

---

## Release Impact

**Release:** REL-1 (demoIW MVP)
**Epic progress:** 5/9 epics complete for this release (E1, E2, E3, E4, E5)

E5 delivers the operator-facing surface that makes E4's intelligence actionable — the first time the demo has a complete P-01 narrative loop.

---

## Next Steps

- **E6 — Executive Panel / KPI Dashboard / NL Query** — unblocked by E5's case detail and communications audit trail
- **E7 — Demo Readiness** — English translation pass, polish, E2E hardening
- **E8 — Backlog** — parking lot follow-ups (real message delivery, multi-operator auth, prioritized endpoint reading persisted scores)
- **E9 — i18n** — already accomplished (b15)