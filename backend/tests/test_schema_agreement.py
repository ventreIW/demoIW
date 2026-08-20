"""The ORM and the Alembic migrations must describe the same schema (BUG-09).

Two independent declarations of one schema were maintained for the life of this project with
nothing forcing agreement, and they diverged in three ways at once: identifier types,
timestamp timezone-awareness, and one nullability constraint. None was expressible on SQLite,
where `Base.metadata.create_all` builds the schema *from the ORM* and the migrations never
execute at all.

Every other gate passed throughout: 563 tests, mypy, ruff, CI, and `alembic upgrade head`
itself — because creating a schema is not the same as writing to it.

This test is the mechanism that was missing. It compares the live schema built by the
migrations against `Base.metadata`, so a future divergence fails here instead of in
production. It requires PostgreSQL and skips loudly without it.
"""

import pytest
from sqlalchemy import create_engine

from app.adapters.persistence.models import Base
from tests.conftest import _postgres_url, _run_alembic

#: PostgreSQL type names for the SQLAlchemy types this schema uses. Compared by name because
#: the two sides spell them differently (``Uuid`` vs ``uuid``, ``TIMESTAMP(timezone=True)``
#: vs ``timestamp with time zone``).
_EXPECTED_PG_TYPE = {
    "UUID": {"uuid"},
    # Keyed on type(column.type).__name__, so SQLAlchemy's ``String`` is "STRING", not
    # "VARCHAR". Omitting it made this test skip every String column as "not modelled" —
    # including the ones BUG-09 was about. Verified by reintroducing the divergence and
    # watching the test go red.
    "STRING": {"character varying", "text"},
    "VARCHAR": {"character varying"},
    "TEXT": {"text"},
    "INTEGER": {"integer"},
    "FLOAT": {"double precision", "real"},
    "BOOLEAN": {"boolean"},
    "DATETIME": {"timestamp with time zone", "timestamp without time zone"},
    "TIMESTAMP": {"timestamp with time zone", "timestamp without time zone"},
    "JSON": {"json", "jsonb"},
}


def _live_schema(url: str) -> dict[str, dict[str, tuple[str, bool]]]:
    """Build the schema from the migrations and reflect what they actually created."""
    sync_url = url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
    engine = create_engine(sync_url)
    with engine.begin() as conn:
        conn.exec_driver_sql("DROP SCHEMA public CASCADE")
        conn.exec_driver_sql("CREATE SCHEMA public")
    engine.dispose()

    _run_alembic(url, "upgrade head")

    # Read information_schema rather than SQLAlchemy's reflected type objects. Reflection
    # renders TIMESTAMP WITH TIME ZONE as plain "TIMESTAMP" — the timezone flag is carried on
    # the type object, not in its string form — so comparing str(reflected_type) reports
    # every aware column as naive. information_schema.data_type is what the database itself
    # says, which is the whole point of this test.
    engine = create_engine(sync_url)
    schema: dict[str, dict[str, tuple[str, bool]]] = {}
    with engine.begin() as conn:
        rows = conn.exec_driver_sql(
            """
            SELECT table_name, column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_schema = 'public'
            ORDER BY table_name, ordinal_position
            """
        ).fetchall()
    engine.dispose()
    for table_name, column_name, data_type, is_nullable in rows:
        schema.setdefault(table_name, {})[column_name] = (
            data_type.lower(),
            is_nullable == "YES",
        )
    return schema


@pytest.fixture(scope="module")
def live_schema() -> dict[str, dict[str, tuple[str, bool]]]:
    url = _postgres_url()
    return _live_schema(url)


def test_every_orm_table_exists_in_the_migrated_schema(live_schema) -> None:
    orm_tables = {t.name for t in Base.metadata.sorted_tables}
    missing = orm_tables - set(live_schema)
    assert not missing, f"the ORM declares tables the migrations never create: {sorted(missing)}"


def test_every_orm_column_exists_in_the_migrated_schema(live_schema) -> None:
    missing: list[str] = []
    for table in Base.metadata.sorted_tables:
        if table.name not in live_schema:
            continue
        for column in table.columns:
            if column.name not in live_schema[table.name]:
                missing.append(f"{table.name}.{column.name}")
    assert not missing, (
        f"the ORM declares columns the migrations never create: {sorted(missing)}. "
        "A missing column fails at runtime on the first query that touches it."
    )


def test_nullability_agrees_between_orm_and_migrations(live_schema) -> None:
    """The BUG-09 case: contact_results.communication_id was NOT NULL in the migration and
    nullable in the ORM, so the ordinary operator workflow was impossible on PostgreSQL."""
    disagreements: list[str] = []
    for table in Base.metadata.sorted_tables:
        if table.name not in live_schema:
            continue
        for column in table.columns:
            if column.name not in live_schema[table.name]:
                continue
            _, db_nullable = live_schema[table.name][column.name]
            if bool(column.nullable) != db_nullable:
                disagreements.append(
                    f"{table.name}.{column.name}: orm nullable={column.nullable}, "
                    f"migration nullable={db_nullable}"
                )
    assert not disagreements, "ORM and migrations disagree on nullability:\n  " + "\n  ".join(
        disagreements
    )


def test_column_types_agree_between_orm_and_migrations(live_schema) -> None:
    """The other two BUG-09 cases: uuid vs varchar, and naive vs aware timestamps."""
    disagreements: list[str] = []
    unmodelled: set[str] = set()
    for table in Base.metadata.sorted_tables:
        if table.name not in live_schema:
            continue
        for column in table.columns:
            if column.name not in live_schema[table.name]:
                continue
            db_type, _ = live_schema[table.name][column.name]
            orm_type = type(column.type).__name__.upper()
            expected = _EXPECTED_PG_TYPE.get(orm_type)
            if expected is None:
                # Surfaced rather than skipped: a silent skip is exactly how the first
                # version of this test passed while the divergence it exists to catch was
                # sitting in front of it.
                unmodelled.add(orm_type)
                continue
            if not any(db_type.startswith(e) for e in expected):
                disagreements.append(
                    f"{table.name}.{column.name}: orm {orm_type} -> expected one of "
                    f"{sorted(expected)}, migration created {db_type!r}"
                )
    assert not disagreements, "ORM and migrations disagree on column types:\n  " + "\n  ".join(
        disagreements
    )
    assert not unmodelled, (
        f"_EXPECTED_PG_TYPE does not model these ORM types, so their columns were never "
        f"compared: {sorted(unmodelled)}. Add them — an unmodelled type is an unchecked one."
    )


def test_timestamps_are_timezone_aware(live_schema) -> None:
    """The application writes datetime.now(UTC); naive columns reject it on PostgreSQL."""
    naive: list[str] = []
    for table, columns in live_schema.items():
        for name, (db_type, _) in columns.items():
            if db_type.startswith("timestamp") and "with time zone" not in db_type:
                naive.append(f"{table}.{name}: {db_type}")
    assert not naive, (
        "these columns are timezone-naive but the application writes aware datetimes:\n  "
        + "\n  ".join(naive)
    )
