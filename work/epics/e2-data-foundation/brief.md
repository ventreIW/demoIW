# E2 Brief — Data Foundation

**Backlog source:** B-02, B-07  
**Status:** Active — started 2026-06-25  
**Estimated size:** S (~3–4 days)  
**Branch:** `e2-data-foundation` (from `main`, after E1 merges)

---

## Goal

Establish the complete PostgreSQL schema for all domain entities and a working scenario management system: the API layer that creates, lists, and activates scenarios, and the frontend entry-point screen the demo facilitator uses to choose a dataset before anything else.

At the end of this epic, the application has a real database with all tables, the scenario selector works in the browser, and three pre-loaded sector scenarios are seeded on first launch. The dataset generator (E3) will populate those scenario slots with actual synthetic data.

---

## Success criteria

| Criterion | Verifiable signal |
|---|---|
| All domain tables exist | `alembic upgrade head` creates all 7 entity tables without errors |
| Scenario CRUD works | `POST /api/scenarios`, `GET /api/scenarios`, `GET /api/scenarios/{id}`, `PATCH /api/scenarios/{id}/activate` return correct responses |
| Scenario selector renders | Navigating to the app root shows the scenario list; no scenario is preselected until the facilitator picks one |
| Active scenario is persistent | Activating a scenario, refreshing the page, and returning to the selector shows the same scenario as active |
| Pre-loaded scenarios exist | On first startup (`alembic upgrade head`) three seed scenarios appear (manufacturing, retail, professional services) — with no client data yet |
| CSV upload accepted | `POST /api/scenarios/upload-csv` with a valid CSV returns a scenario summary; invalid CSV returns 422 |
| Entry-point enforced | Routes that require an active scenario redirect to the selector if none is active |

---

## Stories

| ID | Title | Size |
|---|---|---|
| s2.1 | Domain schema & migrations | S |
| s2.2 | Scenario management API | S |
| s2.3 | Scenario selector UI | S |
| s2.4 | CSV upload | XS |

---

## Dependencies

- E1 must be merged to `main` before this epic branch is created.

## Out of scope

- Populating scenarios with client/invoice data (E3)
- Scoring or prioritization (E4)
- Any operations or executive panel screens (E5, E6)
