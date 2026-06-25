# E1 Retrospective — Project Scaffolding & CI Baseline

**Dates:** 2026-06-19 → 2026-06-23
**Stories:** s1.1, s1.2, s1.3 (3 of 3 complete)
**Team:** Rodrigo (s1.1), Nano + Renata (s1.2, s1.3)
**Gates:** All passing — frontend (typecheck ✓, lint ✓, test ✓) | backend (ruff ✓, mypy ✓, pytest ✓)

---

## Scope verification

| In-scope item | Status | Evidence |
|---|---|---|
| Root repo structure + `.gitignore` | Fulfilled | `frontend/`, `backend/`, `.gitignore` in repo root |
| Linting + formatting configs (Ruff, mypy, ESLint, Prettier) | Fulfilled | `pyproject.toml` (ruff/mypy), `eslint.config.mjs`, `prettier.config.js` |
| GitHub Actions CI workflow | Fulfilled | `.github/workflows/ci.yml` — parallel frontend/backend jobs |
| Next.js 15 App Router init with TypeScript strict | Fulfilled | `frontend/tsconfig.json` strict mode, App Router structure |
| Tailwind CSS + shadcn/ui base setup | Fulfilled | `tailwind.config.ts`, `components.json`, `frontend/src/components/ui/` |
| Basic layout shell (sidebar + main area) | Fulfilled | `src/components/layout/MainLayout.tsx` |
| `GET /healthcheck` API route returning `{ status: "ok" }` | Fulfilled | `src/app/api/healthcheck/route.ts` |
| FastAPI app factory with lifespan context manager | Fulfilled | `backend/app/main.py` |
| Pydantic Settings v2 loading from `.env` | Fulfilled | `backend/app/config.py` |
| Async SQLAlchemy 2.0 engine + session factory | Fulfilled | `backend/app/infrastructure/database.py` |
| Alembic initialized | Fulfilled | `backend/alembic/`, `backend/alembic/versions/0001_init.py` |
| `GET /health` endpoint with DB connectivity check | Fulfilled | `backend/app/routers/health.py` |
| Pytest config + one passing test (health endpoint) | Fulfilled | `backend/tests/test_health.py` — 2 tests pass |

All 13 in-scope items fulfilled. No elimination commitments in this epic (greenfield build).

---

## Summary

E1 established the full technical foundation for the demoIW project: monorepo structure, parallel CI pipeline, frontend skeleton (Next.js 15 + Tailwind + shadcn/ui), and backend skeleton (FastAPI + async SQLAlchemy + Alembic). Three stories, three developers, delivered across 5 days. The platform is now in a state where any subsequent epic can start feature work without scaffold setup.

---

## Metrics

| Metric | Value |
|---|---|
| Planned stories | 3 |
| Completed stories | 3 |
| Estimated duration | ~2 days |
| Actual duration | 5 days (2026-06-19 → 2026-06-23) |
| Patterns added | 6 (PAT-1 through PAT-6) |
| Patterns reinforced | BASE-001, BASE-009, BASE-015, BASE-053 (multiple times) |
| Deferred items resolved at epic close | 2 (`orjson` in requirements.txt, `aiosqlite` in dev deps) |
| ADRs written | 1 (ADR-001: Next.js App Router) |

---

## What went well

1. **TDD cycle caught issues early across all stories** — the healthcheck test in s1.2 caught the route path mismatch (`/healthcheck` vs `/api/healthcheck`) immediately during RED phase. The DB-unavailable test in s1.3 exposed a FastAPI DI edge case before merge.
2. **Parallel CI design** — frontend and backend jobs run independently; CI runtime is bounded by the slower job, not both combined.
3. **Script-based gate approach (PAT-1)** — once adopted in s1.1, it eliminated all subsequent YAML quoting issues in gate configuration.
4. **SQLite in-memory for CI (PAT-5/s1.3)** — tests run without a real PostgreSQL instance in CI while exercising real SQLAlchemy code paths.
5. **Team velocity on s1.3** — Nano/Renata delivered the backend skeleton in ~25 min actual vs 40 min estimated with a clean design doc and no structural surprises.

---

## What to improve

1. **Deferred deps created gate failures at close** — `orjson` and `aiosqlite` were installed locally but not added to requirements files. Both failed acceptance gates at epic close. Rule for future epics: never defer a requirements file addition past the story boundary.
2. **Design doc had wrong route path (s1.2)** — `s1.2-design.md` specified `src/app/healthcheck/route.ts` but the acceptance criteria said `GET /api/healthcheck`. The `rai-story-design` prompt should verify URL paths against acceptance criteria.
3. **shadcn/ui version not pinned in design** — s1.2 assumed v3 but `npx shadcn@latest` installed v4.11.0. Version pinning for fast-moving ecosystem tools should be explicit in the design doc.
4. **WSL `/mnt/c/` npm performance (PAT-4) not in README** — discovered in s1.2, deferred twice. Added to README as part of this epic close.
5. **Pull board stale after s1.3** — pull-board.md said "2/3 stories complete" after s1.3 merged. Pull board ownership should be explicit in story-close checklist.

---

## Process improvements applied this epic

| Applied | Description |
|---|---|
| ✓ | PAT-1 registered: YAML gate commands → `scripts/*.sh`, not inline bash |
| ✓ | PAT-2 registered: Bootstrapping gate exception — wire gates as final task |
| ✓ | PAT-3 registered: Next.js 15 ESM config requires `"type": "module"` |
| ✓ | PAT-4 registered: WSL npm workaround — native ext4 filesystem |
| ✓ | PAT-5 registered: Next.js App Router `/api/*` route mapping |
| ✓ | PAT-6 registered: ESLint + Prettier must explicitly ignore `.next/` |
| ✓ | ADR-001 written: Next.js App Router rationale |
| Deferred → Done at epic close | `orjson` added to `requirements.txt` |

---

## Heutagogical checkpoint

**What did the team learn as a whole?**

The full stack wiring for this exact project (Next.js 15 App Router + FastAPI async + shadcn/ui v4) is now mapped and pattern-captured. Future epics start from this baseline without re-discovering any of PAT-1 through PAT-6. FastAPI dependency injection scope is a subtle distinction affecting test fixture design — captured and applicable to all subsequent backend tests.

**What should E2 design account for?**

- PostgreSQL must be running locally before E2 work begins (`alembic upgrade head` requires a live DB).
- `uv venv --python 3.12` is the correct venv command on this system.
- shadcn/ui v4 uses `@base-ui/react`; Radix imports will not work — verify in any design that adds new shadcn components.
- `orjson` and `aiosqlite` are now in requirements files — no reinstall needed.
