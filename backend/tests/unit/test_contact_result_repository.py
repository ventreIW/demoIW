from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.adapters.persistence.models import Base, ClientORM, ScenarioORM
from app.adapters.persistence.sqlalchemy_contact_result_repo import (
    SQLAlchemyContactResultRepository,
)
from app.domain.entities.contact_result import ContactResult
from app.domain.enums import ContactResultType


@pytest.fixture
async def async_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)()
    yield session
    await session.close()
    await engine.dispose()


def _contact_result(
    client_id: UUID, result_type: ContactResultType = ContactResultType.PROMISE_TO_PAY
) -> ContactResult:
    return ContactResult(
        id=uuid4(),
        client_id=client_id,
        communication_id=None,
        result_type=result_type,
        notes="Test notes",
        recorded_at=datetime(2026, 7, 30, tzinfo=UTC),
    )


def _scenario_id() -> UUID:
    return uuid4()


def _client_id() -> UUID:
    return uuid4()


async def _create_scenario_and_client(
    async_session: AsyncSession, scenario_id: UUID, client_id: UUID
) -> None:
    await async_session.execute(
        insert(ScenarioORM).values(
            {
                "id": str(scenario_id),
                "name": "Test Scenario",
                "sector": "RETAIL",
                "seed": None,
                "parameters": {},
                "source": "manual",
                "status": "active",
                "created_at": datetime.now(UTC),
            }
        )
    )
    await async_session.execute(
        insert(ClientORM).values(
            {
                "id": str(client_id),
                "scenario_id": str(scenario_id),
                "name": "Test Client",
                "sector_description": None,
                "payment_history_pattern": "ON_TIME",
            }
        )
    )
    await async_session.commit()


def test_sqlalchemy_contact_result_repository_exists():
    assert SQLAlchemyContactResultRepository is not None


def test_sqlalchemy_contact_result_repository_is_subclass_of_irepository():
    from app.ports.repositories import IContactResultRepository

    assert issubclass(SQLAlchemyContactResultRepository, IContactResultRepository)


def test_sqlalchemy_contact_result_repository_has_required_methods():
    assert hasattr(SQLAlchemyContactResultRepository, "add")
    assert hasattr(SQLAlchemyContactResultRepository, "get_by_client_id")


@pytest.mark.asyncio
async def test_can_be_instantiated(async_session: AsyncSession):
    repo = SQLAlchemyContactResultRepository(async_session)
    assert isinstance(repo, SQLAlchemyContactResultRepository)


@pytest.mark.asyncio
async def test_add_returns_contact_result(async_session: AsyncSession):
    scenario_id = _scenario_id()
    client_id = _client_id()
    await _create_scenario_and_client(async_session, scenario_id, client_id)

    repo = SQLAlchemyContactResultRepository(async_session)
    cr = _contact_result(client_id)
    returned = await repo.add(cr)

    assert isinstance(returned, ContactResult)
    assert returned.client_id == client_id
    assert returned.result_type == ContactResultType.PROMISE_TO_PAY
    assert returned.notes == "Test notes"
    assert isinstance(returned.id, UUID)


@pytest.mark.asyncio
async def test_add_persists_to_database(async_session: AsyncSession):
    scenario_id = _scenario_id()
    client_id = _client_id()
    await _create_scenario_and_client(async_session, scenario_id, client_id)

    repo = SQLAlchemyContactResultRepository(async_session)
    cr = _contact_result(client_id)
    returned = await repo.add(cr)

    from sqlalchemy import select

    from app.adapters.persistence.models import ContactResultORM

    result = await async_session.execute(
        select(ContactResultORM).where(ContactResultORM.id == str(returned.id))
    )
    orm = result.scalar_one_or_none()
    assert orm is not None
    assert orm.client_id == str(client_id)
    assert orm.result_type == "promise_to_pay"
    assert orm.notes == "Test notes"


@pytest.mark.asyncio
async def test_get_by_client_id_returns_contact_results_sorted_by_recorded_at_desc(
    async_session: AsyncSession,
):
    scenario_id = _scenario_id()
    client_id = _client_id()
    await _create_scenario_and_client(async_session, scenario_id, client_id)

    repo = SQLAlchemyContactResultRepository(async_session)

    # Add two contact results for the same client
    cr1 = _contact_result(client_id, ContactResultType.PROMISE_TO_PAY)
    cr1 = ContactResult(
        id=uuid4(),
        client_id=client_id,
        communication_id=None,
        result_type=ContactResultType.PROMISE_TO_PAY,
        notes="First contact",
        recorded_at=datetime(2026, 7, 29, tzinfo=UTC),
    )
    cr2 = _contact_result(client_id, ContactResultType.PAID)
    cr2 = ContactResult(
        id=uuid4(),
        client_id=client_id,
        communication_id=None,
        result_type=ContactResultType.PAID,
        notes="Second contact (more recent)",
        recorded_at=datetime(2026, 7, 30, tzinfo=UTC),
    )

    await repo.add(cr1)
    await repo.add(cr2)

    results = await repo.get_by_client_id(client_id)
    assert len(results) == 2
    assert all(isinstance(r, ContactResult) for r in results)
    # Should be sorted by recorded_at desc (most recent first)
    assert results[0].result_type == ContactResultType.PAID
    assert results[1].result_type == ContactResultType.PROMISE_TO_PAY


@pytest.mark.asyncio
async def test_get_by_client_id_returns_empty_list_for_no_results(async_session: AsyncSession):
    repo = SQLAlchemyContactResultRepository(async_session)
    client_id = uuid4()
    results = await repo.get_by_client_id(client_id)
    assert results == []
