# E1 Brief — Project Scaffolding & CI Baseline

**Backlog source:** B-01  
**Status:** Active — approved by Gustavo (2026-06-19)  
**Estimated size:** XS (~2 days)  
**Branch:** stories from `main` (RaiSE 3.0 convention)

---

## Goal

Establish the technical monorepo skeleton: both applications (frontend and backend) run locally without errors, tooling enforces code quality, and a CI pipeline verifies every pull request.

This epic has no user-visible features. Its output is the foundation all subsequent epics build on.

---

## Success criteria

| Criterion | Verifiable signal |
|---|---|
| Both apps start cleanly | `npm run dev` (frontend) and `uvicorn app.main:app --reload` (backend) complete without errors |
| CI is green | GitHub Actions workflow passes on a clean PR branch |
| Type systems enforced | `npm run typecheck` (TypeScript strict) and `mypy` return zero errors |
| Linters pass | ESLint + Prettier (frontend) and Ruff (backend) report no violations |
| First test passes | `pytest` finds and passes at least one test (health endpoint) |
| DB connection works | Backend connects to a local PostgreSQL instance and runs `alembic upgrade head` |

---

## Stories

| ID | Title | Size |
|---|---|---|
| s1.1 | Repository scaffold & CI pipeline | XS |
| s1.2 | Frontend skeleton | XS |
| s1.3 | Backend skeleton | XS |

---

## Dependencies

None — this is the first epic.

## Out of scope

- Feature screens of any kind
- Authentication or user roles
- i18n / PWA config (separate backlog items)
- Deployment configuration (Vercel / Railway)
- Any domain models or database tables
