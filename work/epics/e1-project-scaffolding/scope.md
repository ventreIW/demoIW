# E1 Scope — Project Scaffolding & CI Baseline

---

## In scope

| Item | Story |
|---|---|
| Root repo structure and `.gitignore` | ~~s1.1~~ ✓ |
| Linting + formatting configs (Ruff, mypy, ESLint, Prettier) | ~~s1.1~~ ✓ |
| GitHub Actions CI workflow (typecheck + lint + test) | ~~s1.1~~ ✓ |
| Next.js 15 App Router init with TypeScript strict | s1.2 |
| Tailwind CSS + shadcn/ui base setup | s1.2 |
| Basic layout shell (sidebar navigation placeholder + main area) | s1.2 |
| `GET /healthcheck` API route returning `{ status: "ok" }` | s1.2 |
| FastAPI app factory with lifespan context manager | s1.3 |
| Pydantic Settings v2 loading from `.env` | s1.3 |
| Async SQLAlchemy 2.0 engine + session factory | s1.3 |
| Alembic initialized (empty `versions/` directory) | s1.3 |
| `GET /health` endpoint returning `{ status: "ok", db: "connected" }` | s1.3 |
| Pytest config + one passing test (health endpoint) | s1.3 |

---

## Explicitly out of scope

| Item | Reason |
|---|---|
| Any feature UI screens | No PRD requirement mapped in this epic |
| Database tables / ORM models | E2 |
| i18n (next-intl) | B-15, later epic |
| PWA manifest / service worker | B-14, later epic |
| Authentication / role switching | B-17 (under consideration) |
| Vercel / Railway deployment config | After E2 |
| Docker / docker-compose | Not in backlog — add to parking-lot if needed |
| OpenRouter integration | E3 |

---

## Acceptance gate checklist

Before merging E1 → main, all of the following must be true:

- [ ] `cd frontend && npm run dev` starts on port 3000 without errors
- [ ] `cd frontend && npm run typecheck` exits 0
- [ ] `cd frontend && npm run lint` exits 0
- [ ] `cd frontend && npm test -- --run` all tests pass
- [ ] `cd backend && uvicorn app.main:app --reload` starts without errors
- [ ] `cd backend && alembic upgrade head` applies the init migration without errors
- [ ] `cd backend && pytest` all tests pass
- [ ] `cd backend && mypy app/` exits 0
- [ ] GitHub Actions CI is green on the epic branch PR
- [ ] All three story retrospectives are written
- [ ] ADR-001 (App Router) is written in `dev/decisions/`
