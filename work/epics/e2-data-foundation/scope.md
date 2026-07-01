# E2 Scope — Data Foundation

## In scope

| Item | Story |
|---|---|
| ~~SQLAlchemy ORM models for all 7 entity tables~~ | ~~s2.1~~ ✓ |
| ~~Domain entity Pydantic models (separate from ORM)~~ | ~~s2.1~~ ✓ |
| ~~ORM ↔ domain mappers~~ | ~~s2.1~~ ✓ |
| ~~Alembic migration `0002_domain_schema.py`~~ | ~~s2.1~~ ✓ |
| ~~Alembic data migration `0003_seed_scenarios.py` (3 blank scenarios)~~ | ~~s2.1~~ ✓ |
| ~~Partial unique index on `scenarios.status = 'active'`~~ | ~~s2.1~~ ✓ |
| ~~ADR-002: active scenario constraint~~ | ~~s2.1~~ ✓ |
| ~~`POST /api/scenarios`, `GET /api/scenarios`, `GET /api/scenarios/{id}`~~ | ~~s2.2~~ ✓ |
| ~~`PATCH /api/scenarios/{id}/activate`, `GET /api/scenarios/active`~~ | ~~s2.2~~ ✓ |
| ~~Scenario repository (SQLAlchemy implementation of IScenarioRepository)~~ | ~~s2.2~~ ✓ |
| ~~Integration tests for all scenario endpoints~~ | ~~s2.2~~ ✓ |
|| ~~Scenario selector UI at `/scenarios`~~ | ~~s2.3~~ ✓ ||
|| ~~Scenario card component (name, sector badge, status, client count)~~ | ~~s2.3~~ ✓ ||
|| ~~Route guard (redirect to `/scenarios` if no active scenario)~~ | ~~s2.3~~ ✓ |
| ~~"\"Generar nuevo\" button (stub — disabled until E3)~~ | ~~s2.3~~ ✓ |
| ~~`POST /api/v1/scenarios/upload-csv` endpoint~~ | ~~s2.5~~ ✓ |
| ~~CSV validation (required columns, error detail on 422)~~ | ~~s2.5~~ ✓ |
| ~~Scenario + Client + Invoice creation from CSV~~ | ~~s2.5~~ ✓ |
| ~~File picker UI in scenario selector~~ | ~~s2.4~~ ✓ |
| ~~Integration tests for CSV upload (4 scenarios)~~ | ~~s2.5~~ ✓ |

## Explicitly out of scope

| Item | Reason |
|---|---|
| Populating scenarios with client/invoice data | E3 — generator not built yet |
| Score, communication, contact-result rows | E4/E5 |
| Operations or executive panel pages | E5, E6 |
| Authentication | B-17 under consideration |

## Acceptance gate checklist

- [x] `alembic upgrade head` creates all 7 tables + unique index + 3 seed scenarios
- [x] All scenario API endpoints covered by integration tests (pytest, passing)
- [x] `GET /api/scenarios/active` returns the seed scenario after activating one
- [x] Scenario selector renders in browser; scenario card shows "Sin datos" badge
- [x] Route guard redirects `/` → `/scenarios` when no scenario is active
- [x] CSV upload with valid file creates a scenario; invalid file returns 422 with column errors
- [x] `mypy app/`, `npm run typecheck`, all tests pass
- [x] ADR-002 written
- [x] All 5 story retrospectives written
