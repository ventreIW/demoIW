# ADR-002: Partial Unique Index for Active Scenario Constraint

**Date:** 2026-06-25
**Status:** Accepted
**Epic:** e2-data-foundation

## Context

The system must guarantee that at most one scenario is active at any time. A demo facilitator selects a scenario before any data is shown; multiple active scenarios would make "the active scenario" ambiguous and break the route guard logic in s2.3.

## Decision

Enforce the at-most-one-active constraint at the **database level** via a PostgreSQL partial unique index:

```sql
CREATE UNIQUE INDEX uix_scenarios_active
ON scenarios (status)
WHERE status = 'active';
```

## Rationale

A partial unique index on a constant predicate (`WHERE status = 'active'`) allows any number of inactive scenarios while making a second `INSERT`/`UPDATE` with `status = 'active'` fail at the DB level — not just in application code. This eliminates the TOCTOU race condition that application-level checks cannot prevent under concurrent requests.

The alternative — enforcing uniqueness in the repository with a read-then-write pattern — would require serializable transactions or advisory locks and adds complexity with no benefit for a demo system where concurrent activation is not an expected usage pattern.

## Alternatives considered

| Alternative | Reason rejected |
|---|---|
| Application-level check (read active count before insert) | TOCTOU race; harder to test; enforcement lives in one place but can be bypassed by direct DB writes |
| `CHECK` constraint | Cannot enforce cross-row constraints in standard SQL |
| Boolean `is_active` column with unique index | Indexes NULLs differently across DBs; `WHERE status = 'active'` is more readable and the status field is already needed |

## Consequences

- **Easier:** The `PATCH /scenarios/{id}/activate` endpoint can use a single SQL UPDATE + rely on the DB to reject double-activation. No application-level locking needed.
- **Harder:** Activation requires deactivating the current active scenario in the same transaction. The repository must do: `UPDATE scenarios SET status='inactive' WHERE status='active'`, then `UPDATE scenarios SET status='active' WHERE id={id}`.
- **PostgreSQL only:** The partial index is not supported by SQLite. Test fixtures that use SQLite cannot test the uniqueness constraint — integration tests against real PostgreSQL are required for this behavior.

## Traces to

- E2 scope: "Partial unique index on `scenarios.status = 'active'`"
- E2 brief success criterion: "Active scenario is persistent — activating a scenario, refreshing, shows same as active"
