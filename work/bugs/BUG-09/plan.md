# BUG-09: plan

### T1 — RED is already established
The M4 suite fails on real PostgreSQL with `DatatypeMismatchError`. No new test is needed to
prove the bug; the test that proves it is the one whose absence allowed it.
- Verify: `pytest tests/test_e2e_demo_flow.py -k "postgres or migration"` → 2 failed, 1 passed.

### T2 — Align the ORM with the migrations
`String(36)` → `Uuid(as_uuid=False)` on all seven primary keys. FKs inherit.
- Verify: `pytest tests/` on SQLite → green (no regression); `ruff`, `mypy` clean.
- Commit: `fix(BUG-09): declare id columns as Uuid so the ORM matches the migrations`

### T3 — Verify on PostgreSQL
- Verify: the M4 suite → **all green**, including migration 0004/0005 roundtrip.
- Commit: folded into T2 if no further change is needed.

### T4 — Close the mechanism, not just the defect
The root cause is that nothing compares the two declarations. Add a test that asserts the
ORM's schema and the migration-built schema agree, so a future divergence fails immediately
rather than in production.
- Commit: `test(BUG-09): assert the ORM and Alembic schemas agree`
