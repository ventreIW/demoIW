# TSU-DSM competency coverage — demoIW

> ⚠ **DRAFT — the six components below are INFERRED, not authoritative.**
>
> `governance/vision.md` lists as a measurable outcome: *"All six TSU-DSM profile components
> are demonstrably exercised in the codebase."* The six components are **named nowhere in this
> repository** — `vision.md` is the only file that mentions TSU-DSM at all, and it does not
> enumerate them.
>
> The headings below are inferred from the standard *TSU en Desarrollo de Software
> Multiplataforma* competency profile. **Renata or Gustavo must replace them with the actual
> six** before this document can support the vision's completion claim. The *evidence* columns
> are factual regardless of how the components are finally named — they are drawn from the
> merged codebase and can simply be re-grouped.
>
> Created 2026-08-20 during the project-completion review.

## Scale of the artifact

| | Count |
|---|---|
| Backend Python modules | 78 |
| Frontend TypeScript/TSX modules | 80 |
| Backend test modules | 58 (558 tests) |
| Frontend test modules | 30 (207 tests) |
| Database tables | 7 |
| Alembic migrations | 4 |
| Architecture decision records | 12 |
| Stories with full lifecycle artifacts | 36 |

---

## C1 — Análisis y diseño de software *(inferred)*

| Evidence | Location |
|---|---|
| Requirements traceable to implementation | `governance/prd.md` RF-01…RF-07, NFR-01…NFR-06, each traced through epic scopes to stories |
| Domain modelling | `governance/architecture/domain-model.md`; 7 entities with value objects and enums |
| Hexagonal architecture — ports and adapters | `app/ports/`, `app/adapters/`, `app/application/` |
| Twelve architecture decisions with rationale and rejected alternatives | `dev/decisions/adr-001…adr-012` |
| Per-story technical design | 36 stories, each with design, plan and retrospective |

## C2 — Desarrollo backend y APIs *(inferred)*

| Evidence | Location |
|---|---|
| REST API, 16 endpoints, OpenAPI-documented | `app/routers/` — scenarios, cases, executive |
| Async Python 3.12 with FastAPI + Pydantic v2 | `app/main.py`, request/response models throughout |
| Layered use cases independent of transport | `app/application/use_cases/` |
| Error contracts and graceful degradation | `ExternalServiceError` → 502; 409 for unscored; 422 with accepted values |

## C3 — Persistencia de datos *(inferred)*

| Evidence | Location |
|---|---|
| Relational schema, 7 tables with FKs and cascade rules | `app/adapters/persistence/models.py` |
| Async SQLAlchemy 2.0 with asyncpg | `app/infrastructure/database.py` |
| Versioned migrations incl. a data backfill | `alembic/versions/0001…0004`; `0004` uses `ROW_NUMBER() OVER (PARTITION BY …)` |
| Repository pattern over domain entities | `app/adapters/persistence/sqlalchemy_*_repo.py`, mappers |

## C4 — Desarrollo frontend multiplataforma *(inferred)*

| Evidence | Location |
|---|---|
| Next.js 15 App Router, TypeScript strict, Tailwind, shadcn/ui | `frontend/src/` |
| Installable PWA — manifest + hand-rolled service worker | `public/manifest.json`, `public/sw.js`, ADR-010 |
| Internationalisation ES/EN, 177/177 key parity | `messages/es.json`, `messages/en.json`, `LocaleSwitcher` |
| WCAG 2.1 AA — axe-core scan over 10 components, 0 violations | `src/components/__tests__/a11y-scan.test.tsx` |
| Two role-specific surfaces | operator queue + case detail; executive dashboard + NL query |

## C5 — Inteligencia artificial aplicada *(inferred)*

| Evidence | Location |
|---|---|
| Supervised ML: feature engineering, training split, logistic regression, calibrated scores | `app/application/use_cases/build_training_set.py`, `app/adapters/scoring/sklearn_scorer.py` |
| An explicit leakage guard, tested | ADR-006; `payment_history_pattern` excluded from features, asserted |
| Model choice justified by measurement, not preference | ADR-007 — ROC-AUC 0.732–0.739, `C=0.01` after a collinearity canary |
| Provider-agnostic LLM integration via OpenRouter | `app/adapters/llm/openrouter_adapter.py`, `ILLMPort` |
| Constrained NL→intent translation, refusing out-of-vocabulary questions | ADR-008, `QueryIntent` with `extra="forbid"` |
| Reproducibility as an engineering property | ADR-011, `generation_index`; regression-tested |

## C6 — Calidad, pruebas y gestión del proceso *(inferred)*

| Evidence | Location |
|---|---|
| 765 automated tests (558 backend, 207 frontend) | `backend/tests/`, `frontend/src/**/__tests__/` |
| End-to-end demo path, timed against NFR-01 | `tests/test_e2e_demo_flow.py` — 10 steps, 1.41s vs 600s |
| Performance measured against NFR-02, not assumed | `tests/test_nfr02_performance.py` — 0.222s at 500 clients / 2,073 invoices vs 3s |
| CI gating pushes and PRs across both stacks | `.github/workflows/ci.yml` — typecheck, lint, format, test, build |
| Static analysis: ruff, mypy strict, eslint, tsc | all green |
| Documented defect analysis with root cause | `work/bugs/BUG-01…BUG-07` — scope, triage, analysis, plan, retrospective each |
| Methodology record | 36 stories × (design, plan, retrospective); 7 epic retrospectives; 12 ADRs |

---

## Gaps to note before this is used as evidence

1. **The six components are inferred.** Replace with the authoritative list.
2. **NFR-06 (Auditability) is not yet implemented** — see the open item at project close.
   Until it is, C6's coverage claim has a hole the PRD itself names.
3. **The real-PostgreSQL E2E has not run**, so C3's migration evidence is verified against
   SQLite `create_all` plus review, not against an executed migration.
