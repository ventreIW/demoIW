# BUG-09: retrospective

## Summary
- **Root cause:** two independent declarations of one schema, maintained in parallel with
  nothing forcing agreement, in a test environment that could not express the difference.
- **Fix approach:** align the ORM with the migrations on identifiers and timestamps; relax one
  over-strict migration constraint forward (0006); then add the comparison that was missing.
- **Classification:** Data / **S0-Critical** / Design / Incorrect
- **Three divergences, not one**, and they did not all point the same way.

## What was actually wrong

| # | Divergence | Authoritative side |
|---|---|---|
| 1 | 16 identifier columns: `postgresql.UUID` vs `String(36)` | **migrations** — native uuid is correct |
| 2 | 8 timestamps: `TIMESTAMP(timezone=True)` vs naive `DateTime` | **migrations** — the app writes `datetime.now(UTC)` |
| 3 | `contact_results.communication_id`: `NOT NULL` vs nullable | **the ORM** — a phone call precedes any draft |

The third matters disproportionately. After fixing two divergences where the migration was
right, the tempting generalisation is "migrations are authoritative". The third is the
counter-example: requiring a linked communication makes the ordinary operator workflow
impossible. **Each divergence needed a judgment about the domain, not a rule about which file
wins.**

## This is what M4 was for

E6's scope justified M4 as mandatory because "E4's M4 caught a generation-layer bug no unit
test saw, and E5's M4 repeated the lesson." This is the third instance and it is categorically
worse than the first two: they found bugs in features, this found that **the product could not
persist anything to the database it is built for.** A deployment to Railway or Fly.io would
have failed on its first request.

Everything else was green throughout: 563 tests, mypy, ruff, CI, and `alembic upgrade head`
itself. That last one is the trap — *creating* a schema exercises the migrations; only
*writing* exercises them against the ORM. The two declarations had never met in the life of
the project, because `conftest.py` builds the schema from `Base.metadata` on SQLite and the
migrations therefore never execute at all.

**The gate that would have caught this was deferred six times** — E4, E5, s6.2, s6.3, s6.4,
E7 — and each deferral cited the previous one's blocker rather than re-testing it. The blocker
was real (no PostgreSQL, no Docker, no sudo) right up until it was checked properly: a
userspace PostgreSQL was one `pip install pgserver` away, needed no root, and took four
minutes.

**That is the most useful thing in this retrospective.** The obstacle was never re-examined
after it was first recorded. "No Postgres available" was true on 2026-08-07 and repeated as
fact for two weeks without anyone asking whether it was still true, or whether it was true in
the form stated.

## Process improvement

**Prevention:** the comparison now exists (`tests/test_schema_agreement.py`) and runs whenever
PostgreSQL is reachable. More generally: if two artifacts describe the same thing, something
must compare them, and that something has to run in an environment where a difference is
expressible.

**Pattern:** `Origin=Design` + a second source of truth + a test environment weaker than
production → the defect is invisible by construction, not by oversight. No amount of care in
review finds it, because both sides are correct in isolation.

## The guard I wrote did not catch the bug it was written for

Worth recording plainly. The first version of `test_column_types_agree_between_orm_and_migrations`
keyed its expectations on `type(column.type).__name__`, which for `String(36)` is `STRING` —
and `STRING` was not in the map, so every String column hit the "type this test does not
model" branch and was skipped. Reintroducing the exact BUG-09 divergence produced **5 passed**.

I only found that out because I deliberately reinjected the defect to check, which is the same
discipline s7.4's AC2 imposed. Writing the guard was not the work; proving it fails was.
Unmodelled types are now an assertion rather than a silent skip, because a silent skip is
precisely how the first version passed.

An earlier version also mis-read reflected types and reported every timezone-aware column as
naive — a **false alarm**, and the more dangerous failure mode, because the natural response to
a noisy new test is to weaken it.

## Heutagogical Checkpoint

1. **Learned:** `alembic upgrade head` succeeding says nothing about whether the application
   can use the resulting schema. Migrations and ORM meet only on write. Also learned that
   PostgreSQL is installable in userspace via `pgserver` — no root, no Docker, four minutes.
2. **Process change:** re-test a recorded blocker before inheriting it. Six deferrals repeated
   "no Postgres" without anyone checking whether that was still, or ever, the whole truth.
3. **Framework improvement:** the schema-agreement check belongs in CI, gated on a service
   container. CI runs the same SQLite suite that cannot see any of this, so CI is currently
   green on a backend that could not write to its own database.
4. **More capable of now:** can spot the environment-shaped blind spot — where the test
   environment is *weaker* than production in a way that makes a class of defect
   inexpressible rather than merely unobserved.

## Patterns
- **Added: none** — `rai pattern add` is a verified no-op. Preserved here:
  - Two artifacts describing one thing need a comparator, running where differences are
    expressible.
  - A test environment weaker than production makes some defects invisible by construction.
  - Re-test an inherited blocker; "unavailable" decays into folklore.
  - After writing a guard, reintroduce the defect. A guard that has only ever passed is
    unverified — mine skipped the exact case it existed for.
  - Applying a migration is not using it.
