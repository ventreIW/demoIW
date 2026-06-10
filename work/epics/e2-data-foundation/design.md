# E2 Design — Data Foundation

Traces to: `governance/architecture/domain-model.md`, `governance/architecture/modules/`

---

## Backend: ORM models and migration

SQLAlchemy 2.0 mapped-column style. ORM models live in `app/adapters/persistence/models.py`. They are **not** the domain entities — mappers convert between the two.

### Table overview

```
scenarios          ← Scenario
clients            ← Client (FK → scenarios)
invoices           ← Invoice (FK → clients)
payments           ← Payment (FK → invoices)
scores             ← Score (FK → clients, scenarios)
communications     ← Communication (FK → clients, scenarios)
contact_results    ← ContactResult (FK → clients, communications)
```

All tables use `UUID` primary keys (PostgreSQL `gen_random_uuid()`). All timestamps are `TIMESTAMP WITH TIME ZONE`.

### Alembic strategy

One migration per epic that adds new tables — no column-level migrations at this stage (data model is still stabilizing). Migration file: `0002_domain_schema.py`.

---

## Backend: Scenario management API

REST resource: `/api/scenarios`

| Method | Path | Description |
|---|---|---|
| POST | `/api/scenarios` | Create a blank scenario shell (no data yet) |
| GET | `/api/scenarios` | List all scenarios with summary |
| GET | `/api/scenarios/{id}` | Get one scenario with status |
| PATCH | `/api/scenarios/{id}/activate` | Set as active (deactivates current active) |
| GET | `/api/scenarios/active` | Get the currently active scenario |
| POST | `/api/scenarios/upload-csv` | Create scenario from CSV upload |

Request/response models: Pydantic v2 schemas in `app/routers/scenarios.py` (or `app/schemas/scenario.py`).

### Active scenario — persistence strategy

`scenarios.status` column (enum: `active`, `inactive`). Only one row may be `active` at a time — enforced by a partial unique index:

```sql
CREATE UNIQUE INDEX uix_scenarios_active
  ON scenarios (status)
  WHERE status = 'active';
```

This is a DB-level constraint, not just application logic.

---

## Frontend: Scenario selector

Entry-point screen at `/` (or `/scenarios`). Redirects to this screen if no active scenario exists.

### Layout

```
┌──────────────────────────────────────────────┐
│  Seleccionar escenario de demostración        │
│                                               │
│  ┌────────────┐  ┌────────────┐  ┌────────┐  │
│  │ Manufactura│  │  Retail    │  │  Serv. │  │
│  │  [activo]  │  │            │  │ Profes.│  │
│  └────────────┘  └────────────┘  └────────┘  │
│                                               │
│  [+ Subir CSV]   [+ Generar nuevo]            │
└──────────────────────────────────────────────┘
```

Each scenario card shows: name, sector, client count (0 until E3), status badge (Activo / Sin datos / Con datos).

"Generar nuevo" navigates to the scenario generator form (implemented in E3 — stub/disabled in E2).

### Route guard

Middleware or layout component: if no active scenario, redirect any `/operations` or `/executive` URL back to `/scenarios`.

---

## CSV upload design

- `POST /api/scenarios/upload-csv` accepts `multipart/form-data` with `file: UploadFile`
- Backend validates: required columns (`client_name`, `amount`, `due_date`, `invoice_id` minimum set)
- On validation failure: 422 with column-level error detail
- On success: creates Scenario + Client + Invoice rows, returns ScenarioSummary
- CSV format documented in `README.md`

---

## Seed data

An Alembic data migration (`0003_seed_scenarios.py`) inserts three blank scenarios on first `upgrade head`:
- Sector: MANUFACTURING, name: "Manufactura — Demo"
- Sector: RETAIL, name: "Retail — Demo"  
- Sector: PROFESSIONAL_SERVICES, name: "Servicios Profesionales — Demo"

`source = GENERATED`, `status = inactive`, no clients yet.

---

## ADR to be written

- **ADR-002:** Partial unique index for active scenario — DB-level constraint vs application-level lock.
