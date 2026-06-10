# E1 Design — Project Scaffolding & CI Baseline

Traces to: `e1-project-scaffolding/brief.md`, `governance/architecture/system-design.md`

---

## Repository layout

```
demoIW/                        ← git root
  frontend/                    ← Next.js 15 app
    src/
      app/                     ← App Router
        layout.tsx
        page.tsx
        healthcheck/
          route.ts             ← GET /healthcheck → { status: "ok" }
      components/
        ui/                    ← shadcn/ui generated components
        layout/
          Sidebar.tsx
          MainLayout.tsx
      lib/
      styles/
    public/
    package.json
    tsconfig.json              ← strict: true
    tailwind.config.ts
    .eslintrc.json
    prettier.config.js
    vitest.config.ts
  backend/                     ← FastAPI app
    app/
      main.py                  ← FastAPI app factory + lifespan
      config.py                ← Pydantic Settings v2
      infrastructure/
        database.py            ← async engine + session factory
      routers/
        health.py              ← GET /health
    alembic/
      env.py
      versions/                ← empty at E1 close
    alembic.ini
    pyproject.toml             ← Ruff + mypy + pytest config
    requirements.txt
    requirements-dev.txt
  .github/
    workflows/
      ci.yml
  .gitignore
  README.md
```

---

## Frontend decisions

| Decision | Choice | Rationale |
|---|---|---|
| Router | App Router (Next.js 15) | Server components + streaming; required for PWA layout patterns |
| Component library | shadcn/ui (slate theme) | Accessible, Tailwind-native, composable — no runtime dependency |
| CSS | Tailwind CSS 3.x | Utility-first, matches shadcn/ui; consistent with team skillset |
| TypeScript | strict: true | GR-CODE-001 — enforced from day one |
| Test runner | Vitest | Fast, ESM-native, Vite-based — replaces Jest for Next.js 15 |

`shadcn/ui` init components for E1: `Button`, `Card`, `Separator`, `Skeleton` (needed for layout shell only).

---

## Backend decisions

| Decision | Choice | Rationale |
|---|---|---|
| FastAPI version | 0.115.x | Latest stable; built-in async, lifespan context |
| Pydantic | v2 (BaseSettings) | GR-CODE-001 — type safety; v2 is mandatory for FastAPI 0.115+ |
| ORM | SQLAlchemy 2.0 (async, mapped_column) | Async-native; matches hexagonal adapter pattern |
| Migrations | Alembic | Standard Python migration tool; integrates with SQLAlchemy models |
| Linter | Ruff | Fast, replaces flake8 + isort + pyupgrade in one tool |
| Type checker | mypy (strict) | GR-CODE-001 |
| DB driver | asyncpg | Async PostgreSQL driver required by SQLAlchemy async engine |

---

## CI pipeline (GitHub Actions)

```yaml
# .github/workflows/ci.yml — structure
on: [pull_request]
jobs:
  frontend:
    - npm ci
    - npm run typecheck
    - npm run lint
    - npm run test (vitest --run)
  backend:
    - pip install -r requirements-dev.txt
    - ruff check .
    - mypy app/
    - pytest tests/ -v
```

Both jobs run in parallel. CI must pass before any story or epic branch is merged (quality gate).

---

## ADR to be written in this epic

- **ADR-001:** App Router over Pages Router — confirmed above; write the ADR as part of s1.2.
