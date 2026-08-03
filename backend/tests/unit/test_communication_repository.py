from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.adapters.persistence.models import Base, ClientORM, CommunicationORM, ScenarioORM
from app.adapters.persistence.sqlalchemy_communication_repo import SQLAlchemyCommunicationRepository
from app.domain.entities.communication import Communication
from app.domain.enums import Channel, CommunicationStatus, Tone
from app.ports.repositories import ICommunicationRepository


@pytest.fixture
async def async_session():
    # Create an in-memory SQLite database for testing
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # Create a session
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)()
    yield async_session
    await async_session.close()
    await engine.dispose()


def test_sqlalchemy_communication_repository_exists():
    assert SQLAlchemyCommunicationRepository is not None


def test_sqlalchemy_communication_repository_is_subclass_of_icommunication_repository():
    assert issubclass(SQLAlchemyCommunicationRepository, ICommunicationRepository)


def test_sqlalchemy_communication_repository_has_required_methods():
    assert hasattr(SQLAlchemyCommunicationRepository, "add")
    assert hasattr(SQLAlchemyCommunicationRepository, "get_by_client_id")
    assert hasattr(SQLAlchemyCommunicationRepository, "get_by_id")
    assert hasattr(SQLAlchemyCommunicationRepository, "update")


@pytest.mark.asyncio
async def test_sqlalchemy_communication_repository_can_be_instantiated(async_session):
    repo = SQLAlchemyCommunicationRepository(async_session)
    assert isinstance(repo, SQLAlchemyCommunicationRepository)


@pytest.mark.asyncio
async def test_add_returns_communication(async_session):
    repo = SQLAlchemyCommunicationRepository(async_session)
    scenario_id = uuid4()
    client_id = uuid4()
    from datetime import UTC, datetime

    from sqlalchemy import insert

    # Need a scenario and client for the FK
    await async_session.execute(
        insert(ScenarioORM).values(
            {
                "id": str(scenario_id),
                "name": "Test Scenario",
                "sector": "TEST",
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

    comm_id = uuid4()
    comm = Communication(
        id=comm_id,
        client_id=client_id,
        scenario_id=scenario_id,
        channel=Channel.EMAIL,
        tone=Tone.FORMAL,
        draft_text="Estimado cliente, le recordamos su saldo pendiente.",
        status=CommunicationStatus.DRAFT,
        created_at=datetime.now(UTC),
    )
    returned = await repo.add(comm)
    assert isinstance(returned, Communication)
    assert returned.id != comm_id  # ID should be server-generated
    assert isinstance(returned.id, UUID)
    # Verify in DB
    from sqlalchemy import select

    result = await async_session.execute(
        select(CommunicationORM).where(CommunicationORM.id == str(returned.id))
    )
    orm = result.scalar_one_or_none()
    assert orm is not None
    assert orm.channel == "email"


@pytest.mark.asyncio
async def test_get_by_id_returns_communication(async_session):
    repo = SQLAlchemyCommunicationRepository(async_session)
    scenario_id = uuid4()
    client_id = uuid4()
    from datetime import UTC, datetime

    from sqlalchemy import insert

    # Create scenario and client
    await async_session.execute(
        insert(ScenarioORM).values(
            {
                "id": str(scenario_id),
                "name": "GetById Scenario",
                "sector": "TEST",
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
                "name": "GetById Client",
                "sector_description": None,
                "payment_history_pattern": "ON_TIME",
            }
        )
    )
    # Insert a communication
    comm_id = uuid4()
    await async_session.execute(
        insert(CommunicationORM).values(
            {
                "id": str(comm_id),
                "client_id": str(client_id),
                "scenario_id": str(scenario_id),
                "channel": "email",
                "tone": "formal",
                "draft_text": "Test communication",
                "status": "draft",
                "created_at": datetime.now(UTC),
            }
        )
    )
    await async_session.commit()

    # Call the method
    result = await repo.get_by_id(comm_id)
    assert result is not None
    assert isinstance(result, Communication)
    assert result.id == comm_id
    assert result.channel == Channel.EMAIL
    assert result.status == CommunicationStatus.DRAFT


@pytest.mark.asyncio
async def test_get_by_id_returns_none_for_missing(async_session):
    repo = SQLAlchemyCommunicationRepository(async_session)
    result = await repo.get_by_id(uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_update_communication_status(async_session):
    repo = SQLAlchemyCommunicationRepository(async_session)
    scenario_id = uuid4()
    client_id = uuid4()
    from datetime import UTC, datetime

    from sqlalchemy import insert

    # Create scenario and client
    await async_session.execute(
        insert(ScenarioORM).values(
            {
                "id": str(scenario_id),
                "name": "Update Scenario",
                "sector": "TEST",
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
                "name": "Update Client",
                "sector_description": None,
                "payment_history_pattern": "ON_TIME",
            }
        )
    )
    # Insert a communication in draft status
    comm_id = uuid4()
    await async_session.execute(
        insert(CommunicationORM).values(
            {
                "id": str(comm_id),
                "client_id": str(client_id),
                "scenario_id": str(scenario_id),
                "channel": "whatsapp",
                "tone": "urgent",
                "draft_text": "Urgent reminder",
                "status": "draft",
                "created_at": datetime.now(UTC),
            }
        )
    )
    await async_session.commit()

    # Create updated communication with SENT status
    updated = Communication(
        id=comm_id,
        client_id=client_id,
        scenario_id=scenario_id,
        channel=Channel.WHATSAPP,
        tone=Tone.URGENT,
        draft_text="Urgent reminder",
        status=CommunicationStatus.SENT,
        created_at=datetime.now(UTC),
    )
    result = await repo.update(updated)
    assert isinstance(result, Communication)
    assert result.id == comm_id
    assert result.status == CommunicationStatus.SENT
    assert result.channel == Channel.WHATSAPP

    # Verify in DB
    from sqlalchemy import select

    row = await async_session.execute(
        select(CommunicationORM).where(CommunicationORM.id == str(comm_id))
    )
    orm = row.scalar_one_or_none()
    assert orm is not None
    assert orm.status == "sent"


@pytest.mark.asyncio
async def test_get_by_client_id_returns_communications_sorted_by_created_at_desc(async_session):
    repo = SQLAlchemyCommunicationRepository(async_session)
    scenario_id = uuid4()
    client_id = uuid4()
    from datetime import UTC, datetime, timedelta

    from sqlalchemy import insert

    # Create scenario and client
    await async_session.execute(
        insert(ScenarioORM).values(
            {
                "id": str(scenario_id),
                "name": "Scenario Comm",
                "sector": "TEST",
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
                "name": "Comm Client",
                "sector_description": None,
                "payment_history_pattern": "ON_TIME",
            }
        )
    )
    # Insert two communications for this client
    comm_id_1 = uuid4()
    comm_id_2 = uuid4()
    await async_session.execute(
        insert(CommunicationORM).values(
            [
                {
                    "id": str(comm_id_1),
                    "client_id": str(client_id),
                    "scenario_id": str(scenario_id),
                    "channel": "email",
                    "tone": "formal",
                    "draft_text": "First communication",
                    "status": "draft",
                    "created_at": datetime.now(UTC) - timedelta(hours=2),
                },
                {
                    "id": str(comm_id_2),
                    "client_id": str(client_id),
                    "scenario_id": str(scenario_id),
                    "channel": "whatsapp",
                    "tone": "urgent",
                    "draft_text": "Second communication (more recent)",
                    "status": "sent",
                    "created_at": datetime.now(UTC),
                },
            ]
        )
    )
    await async_session.commit()

    # Call the method
    comms = await repo.get_by_client_id(client_id)
    assert len(comms) == 2
    assert all(isinstance(c, Communication) for c in comms)
    # Should be sorted by created_at desc (most recent first)
    assert comms[0].id == comm_id_2
    assert comms[1].id == comm_id_1
    assert comms[0].status == CommunicationStatus.SENT
    assert comms[1].channel == Channel.EMAIL


@pytest.mark.asyncio
async def test_get_by_client_id_returns_empty_list_for_no_comms(async_session):
    repo = SQLAlchemyCommunicationRepository(async_session)
    client_id = uuid4()
    comms = await repo.get_by_client_id(client_id)
    assert comms == []
