# BUG-09: scope

**Reported:** 2026-08-20 · **Branch:** `bug/BUG-09/orm-migration-type-divergence` · **From:** `main`
**Found by:** E6 M4 — the real-PostgreSQL E2E, on its **first ever execution**.

WHAT:      **The application cannot write to a real PostgreSQL database.** Every `INSERT`
           fails:

             sqlalchemy.exc.ProgrammingError: (asyncpg.exceptions.DatatypeMismatchError)
             column "id" is of type uuid but expression is of type character varying
             HINT: You will need to rewrite or cast the expression.

           This is not an edge case. `POST /scenarios/generate` — the first step of the demo —
           fails on its first statement.

WHEN:      Every write, against any database whose schema was built by the Alembic migrations,
           i.e. every real deployment. Never observed before because **no test has ever run
           against PostgreSQL**: `conftest.py` builds the schema with
           `Base.metadata.create_all` on SQLite, where every column is VARCHAR and the
           mismatch cannot exist.

WHERE:     Two declarations of the same columns disagree.

           `alembic/versions/0002_domain_schema.py` — 16 columns as
           `postgresql.UUID(as_uuid=False)`: the primary key of all 7 tables plus every
           foreign key.

           `app/adapters/persistence/models.py` — the same columns as
           `Mapped[str] = mapped_column(String(36))`, and the FKs inheriting `String` from
           their referenced column.

           SQLAlchemy therefore emits `$1::VARCHAR` against a `uuid` column, and PostgreSQL
           refuses the implicit cast.

EXPECTED:  The ORM and the migrations describe the same schema, and the application writes
           successfully to a database built by its own migrations.

Done when: 1. The full demo path completes against **real PostgreSQL** with the schema built
              by `alembic upgrade head` from zero.
           2. Reproducibility (BUG-05) holds on PostgreSQL, not only on SQLite.
           3. Migration `0004` and `0005` still apply and reverse cleanly.
           4. The existing SQLite suite stays green — the fix must not trade one backend for
              the other.
           5. `ruff`, `ruff format`, `mypy` clean.

TRIAGE:
  Bug Type:    Data
  Severity:    **S0-Critical**
  Origin:      Design
  Qualifier:   Incorrect

  Rationale:
  - **S0, and this is the first S0 in the project.** Not "a feature is broken" — the backend
    cannot persist anything to the database it is built for. Every prior severity call this
    session was bounded by "the demo still runs"; this one is not. A deployment to Railway or
    Fly.io would have failed on its first request.
  - Origin=Design: two schema declarations were maintained in parallel with nothing forcing
    agreement. Neither is a typo; each is internally coherent.
  - Data: the defect is in the type of a persisted column.
  - Qualifier=Incorrect: the columns exist and their types disagree.
