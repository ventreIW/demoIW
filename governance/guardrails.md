# Guardrails

Guardrails are enforceable rules derived from project principles and requirements. Each rule has a level:

- **MUST** — Non-negotiable. Violation is a defect that blocks merging.
- **SHOULD** — Recommended. Skipping requires explicit justification in the story retrospective.

Each rule traces to a principle (§) or requirement (RF, defined in prd.md).

---

## Data & Privacy

**GR-DATA-001 — MUST** (§6)  
No real customer, invoice, or organizational data may be committed to the repository, used in development, or loaded into the application at any time. All datasets must be synthetically generated.

**GR-DATA-002 — MUST** (§6)  
Generated synthetic data must not include names, tax IDs (RFC), addresses, or any identifiers traceable to real legal entities in Mexico or elsewhere.

**GR-DATA-003 — MUST** (§6)  
InterWare client information (names, use cases, project details) must not appear in any project file, commit message, or documentation.

---

## AI Integration

**GR-AI-001 — MUST** (§5)  
All LLM calls must route through OpenRouter. Direct calls to vendor APIs (Anthropic, OpenAI, etc.) are not permitted in production code.

**GR-AI-002 — MUST** (§5)  
The model name used for any LLM call must be read from configuration (environment variable or config file). It must not be hardcoded in business logic.

**GR-AI-003 — MUST** (§4)  
The communications generator must implement human-in-the-loop: the LLM proposes a draft, the operator reviews and may edit, and the send action requires explicit operator confirmation. Automated sending without human approval is not permitted.

**GR-AI-004 — SHOULD** (§4)  
Generated communication drafts must be reviewed for tone before the prompt template is finalized. Prompts must instruct the model to produce professional, respectful, and proportionate language. No threatening, demeaning, or legally questionable language.

**GR-AI-005 — SHOULD** (§5)  
For synthetic data generation and analytics queries, prefer cost-effective models available on OpenRouter. Reserve high-capability (and higher-cost) models for the communications generator where quality directly affects the demo.

---

## Architecture

**GR-ARCH-001 — MUST** (§1)  
Frontend and backend must be fully decoupled applications communicating only through the defined REST API. No shared code between frontend and backend beyond API type contracts.

**GR-ARCH-002 — MUST** (§1)  
The backend must expose an OpenAPI-valid schema. The schema must be verified (`rai gate check`) before any backend merge.

**GR-ARCH-003 — MUST** (§1)  
No business logic in the frontend. The frontend is responsible only for presentation, user interaction, and calling backend endpoints.

**GR-ARCH-004 — SHOULD**  
Follow hexagonal architecture (ports and adapters) in the backend. External dependencies (database, OpenRouter, file I/O) must be accessed through port interfaces, not called directly from use case code.

**GR-ARCH-005 — MUST**  
Any significant architectural decision (choice of library, design pattern, data model trade-off) must be documented as an ADR in `dev/decisions/adr-{N}-{slug}.md` before the end of the epic in which the decision was made.

---

## Code quality

**GR-CODE-001 — MUST**  
All code must pass their respective type-checkers before merging: TypeScript strict mode for frontend, Pydantic + mypy for backend.

**GR-CODE-002 — MUST**  
All tests must pass before merging any branch. A broken test is a stop signal (§2), not a deferral.

**GR-CODE-003 — MUST**  
Backend: unit tests for all scoring, prioritization, and prompt-building logic. Integration tests for all API endpoints.  
Frontend: unit tests for utility functions; component tests for panels with non-trivial state.

**GR-CODE-004 — SHOULD**  
Test coverage for business logic modules (scoring, prioritization, communication generator) must not fall below 80%.

**GR-CODE-005 — SHOULD**  
Functions longer than 40 lines should be decomposed. A function should do one thing.

**GR-CODE-006 — MUST**  
No commented-out code in committed files. Use git history, not inline comments, as the record of removed code.

---

## Git & branching

**GR-GIT-001 — MUST**  
No direct commits to `main`. All changes arrive via merge from an epic or story branch.

**GR-GIT-002 — MUST**  
Story branches must be created from their parent epic branch, not from `main`.

**GR-GIT-003 — MUST**  
Each commit must represent one logical, self-contained change. Commit message must describe what changed and why (not just what).

**GR-GIT-004 — SHOULD**  
Commit after each completed task in a story plan. Do not accumulate multiple tasks in a single commit.

---

## Process & documentation

**GR-PROC-001 — MUST**  
Every story must have a completed retrospective (`s{N}.{M}-retrospective.md`) before the story branch is merged.

**GR-PROC-002 — MUST**  
Implementation cannot begin (`/rai-story-implement`) without a completed story plan (`s{N}.{M}-plan.md`).

**GR-PROC-003 — MUST**  
The epic pull board (`pull-board.md`) must be updated as stories move state. It is the team's single source of truth for current work.

**GR-PROC-004 — SHOULD**  
Session start must include `rai session start --context` to load governance primes and memory before any development work.

---

## Scope & demonstrative focus

**GR-SCOPE-001 — MUST** (§3)  
No feature may be implemented that does not trace to a module defined in `governance/prd.md`. New ideas go to `dev/parking-lot.md` first.

**GR-SCOPE-002 — MUST** (§3)  
The system must not require real integrations (ERP, CRM, email service) to function. All external interactions during demonstration are simulated or logged, not executed.

**GR-SCOPE-003 — SHOULD** (§3)  
Every user-facing screen must be demonstrable end-to-end within the 14-week timeline. Partially built screens should not ship in the demo build.
