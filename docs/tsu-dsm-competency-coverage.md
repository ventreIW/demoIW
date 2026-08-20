# TSU-DSM competency coverage — demoIW

> **Status: headings grounded in the published *perfil de egreso*; the six-item framing still
> needs confirmation.**
>
> `governance/vision.md` lists as a measurable outcome: *"All six TSU-DSM profile components
> are demonstrably exercised in the codebase."* It does not enumerate them, and it is the only
> file in this repository that mentions TSU-DSM.
>
> The headings below are no longer invented. They are drawn from the published graduate
> profile of the *TSU en Tecnologías de la Información, área Desarrollo de Software
> Multiplataforma* — which describes graduates as capable of *"análisis, diseño, desarrollo,
> evaluación e implementación de software a la medida en diferentes plataformas"*, developing
> *"soluciones tecnológicas para entornos Web mediante fundamentos de programación orientada a
> objetos, base de datos y redes"*, and applying *"bases de datos, Internet de las cosas,
> cómputo en la nube y seguridad de la información"*. Sources at the foot of this document.
>
> **What still needs Renata or Gustavo:** the published profile is prose, not a numbered list
> of six. The grouping into exactly six headings below is a reasonable reading of that prose,
> not a citation. If the program's own documentation enumerates them differently, re-group the
> evidence — the evidence rows are factual and survive any regrouping.
>
> Last updated 2026-08-20.

## Scale of the artifact

| | Count |
|---|---|
| Backend Python modules | 78 |
| Frontend TypeScript/TSX modules | 80 |
| Backend test modules | 59 (562 tests) |
| Frontend test modules | 30 (207 tests) |
| Database tables | 7 |
| Alembic migrations | 4 |
| Architecture decision records | 12 (ADR-012 proposed) |
| Stories with full lifecycle artifacts | 36 |

---

## C1 — Análisis y diseño de sistemas de información

*Profile: "análisis y diseño de Sistemas de Información", "capacidad de análisis, diseño".*

| Evidence | Location |
|---|---|
| Requirements traceable to implementation | `governance/prd.md` RF-01…RF-07, NFR-01…NFR-06, each traced through epic scopes to stories |
| Domain modelling | `governance/architecture/domain-model.md`; 7 entities with value objects and enums |
| Hexagonal architecture — ports and adapters | `app/ports/`, `app/adapters/`, `app/application/` |
| Twelve architecture decisions with rationale and rejected alternatives | `dev/decisions/adr-001…adr-012` |
| Per-story technical design | 36 stories, each with design, plan and retrospective |

## C2 — Programación y desarrollo de software a la medida

*Profile: "programar en diversos lenguajes", "desarrollo… de software a la medida", "fundamentos de programación orientada a objetos".*

| Evidence | Location |
|---|---|
| REST API, 16 endpoints, OpenAPI-documented | `app/routers/` — scenarios, cases, executive |
| Async Python 3.12 with FastAPI + Pydantic v2 | `app/main.py`, request/response models throughout |
| Layered use cases independent of transport | `app/application/use_cases/` |
| Error contracts and graceful degradation | `ExternalServiceError` → 502; 409 for unscored; 422 with accepted values |

## C3 — Bases de datos

*Profile: "base de datos" named explicitly as a core concept in the graduate profile.*

| Evidence | Location |
|---|---|
| Relational schema, 7 tables with FKs and cascade rules | `app/adapters/persistence/models.py` |
| Async SQLAlchemy 2.0 with asyncpg | `app/infrastructure/database.py` |
| Versioned migrations incl. a data backfill | `alembic/versions/0001…0004`; `0004` uses `ROW_NUMBER() OVER (PARTITION BY …)` |
| Repository pattern over domain entities | `app/adapters/persistence/sqlalchemy_*_repo.py`, mappers |

## C4 — Desarrollo multiplataforma (web, móvil, escritorio)

*Profile: "aplicaciones de escritorio, desarrollo web o dispositivos móviles", "soluciones tecnológicas para entornos Web".*

| Evidence | Location |
|---|---|
| Next.js 15 App Router, TypeScript strict, Tailwind, shadcn/ui | `frontend/src/` |
| Installable PWA — manifest + hand-rolled service worker | `public/manifest.json`, `public/sw.js`, ADR-010 |
| Internationalisation ES/EN, 177/177 key parity | `messages/es.json`, `messages/en.json`, `LocaleSwitcher` |
| WCAG 2.1 AA — axe-core scan over 10 components, 0 violations | `src/components/__tests__/a11y-scan.test.tsx` |
| Two role-specific surfaces | operator queue + case detail; executive dashboard + NL query |

## C5 — Cómputo en la nube y tecnologías emergentes

*Profile: "Internet de las cosas, cómputo en la nube". Exercised here as applied AI through a cloud LLM gateway and a supervised ML pipeline — the emerging-technology component of this project.*

| Evidence | Location |
|---|---|
| Supervised ML: feature engineering, training split, logistic regression, calibrated scores | `app/application/use_cases/build_training_set.py`, `app/adapters/scoring/sklearn_scorer.py` |
| An explicit leakage guard, tested | ADR-006; `payment_history_pattern` excluded from features, asserted |
| Model choice justified by measurement, not preference | ADR-007 — ROC-AUC 0.732–0.739, `C=0.01` after a collinearity canary |
| Provider-agnostic LLM integration via OpenRouter | `app/adapters/llm/openrouter_adapter.py`, `ILLMPort` |
| Constrained NL→intent translation, refusing out-of-vocabulary questions | ADR-008, `QueryIntent` with `extra="forbid"` |
| Reproducibility as an engineering property | ADR-011, `generation_index`; regression-tested |

## C6 — Evaluación, implementación y seguridad

*Profile: "evaluación e implementación", "seguridad de la información", plus "mantenimiento preventivo y correctivo".*

| Evidence | Location |
|---|---|
| 765 automated tests (558 backend, 207 frontend) | `backend/tests/`, `frontend/src/**/__tests__/` |
| End-to-end demo path, timed against NFR-01 | `tests/test_e2e_demo_flow.py` — 10 steps, 1.41s vs 600s |
| Performance measured against NFR-02, not assumed | `tests/test_nfr02_performance.py` — 0.222s at 500 clients / 2,073 invoices vs 3s |
| CI gating pushes and PRs across both stacks | `.github/workflows/ci.yml` — typecheck, lint, format, test, build |
| Static analysis: ruff, mypy strict, eslint, tsc | all green |
| Documented defect analysis with root cause | `work/bugs/BUG-01…BUG-07` — scope, triage, analysis, plan, retrospective each |
| Auditability of AI-generated output (NFR-06) | `communications` records operator, model, prompt version, drafted-at and sent-at; migration 0005 |
| Methodology record | 36 stories × (design, plan, retrospective); 9 epic retrospectives; 12 ADRs |

---

## Gaps to note before this is used as evidence

1. **The six-item grouping is a reading of the published profile, not a citation.** The
   profile is prose. Confirm against the program's own competency framework.
2. **Security (C6) is the thinnest area.** The profile names *"seguridad de la información"*
   and this project has no authentication — B-17 (role-based access) is still under
   consideration, and NFR-06's operator identifier is a self-described placeholder because of
   it. This is an honest gap, not an oversight: the project is demonstrative and explicitly
   out of scope for production deployment.
3. **IoT is not exercised at all.** The profile names *"Internet de las cosas"*; nothing in
   this codebase touches it. C5 is covered through cloud and applied AI instead.

## Sources

- [TSU en TI Desarrollo de Software Multiplataforma — Universidad Tecnológica de Nayarit](https://vinculos.utn.edu.mx/planes_programas/view/TIDesarrollodeSoftwareMultiplataforma.php)
- [TSU Tecnologías de la Información área Desarrollo de Software Multiplataforma — Universidad Tecnológica de Jalisco](https://www.utj.edu.mx/programas-educativos/dgs/tsu-tiadsm/)
- [TSU en Desarrollo de Software Multiplataforma — Universidad Tecnológica de Durango](https://utd.edu.mx/oferta-educativa/tsu-en-tecnologias-de-la-informacion/)
- [T.S.U. Desarrollo de Software Multiplataforma — Universidad Tecnológica de Xicotepec de Juárez](https://utxicotepec.edu.mx/tsu-dsm/)
