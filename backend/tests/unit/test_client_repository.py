from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.adapters.persistence.models import Base, ClientORM
from app.adapters.persistence.sqlalchemy_client_repo import SQLAlchemyClientRepository
from app.domain.entities.client import Client
from app.domain.enums import PaymentPattern
from app.ports.repositories import IClientRepository


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


def test_sqlalchemy_client_repository_exists():
    assert SQLAlchemyClientRepository is not None


def test_sqlalchemy_client_repository_is_subclass_of_iclient_repository():
    assert issubclass(SQLAlchemyClientRepository, IClientRepository)


def test_sqlalchemy_client_repository_has_required_methods():
    assert hasattr(SQLAlchemyClientRepository, "add")
    assert hasattr(SQLAlchemyClientRepository, "add_many")
    assert hasattr(SQLAlchemyClientRepository, "get_by_scenario_id")
    assert hasattr(SQLAlchemyClientRepository, "get_by_id")


@pytest.mark.asyncio
async def test_sqlalchemy_client_repository_can_be_instantiated(async_session):
    repo = SQLAlchemyClientRepository(async_session)
    assert isinstance(repo, SQLAlchemyClientRepository)


@pytest.mark.asyncio
async def test_add_returns_client(async_session):
    repo = SQLAlchemyClientRepository(async_session)
    client_id = uuid4()
    scenario_id = uuid4()
    client = Client(
        id=client_id,
        scenario_id=scenario_id,
        name="Test Client",
        sector_description=None,
        payment_history_pattern=PaymentPattern.ON_TIME,
    )
    returned_client = await repo.add(client)
    assert isinstance(returned_client, Client)
    # The ID should have been generated (different from input)
    assert returned_client.id != client_id
    assert isinstance(returned_client.id, UUID)
    # Verify it's in the database
    from sqlalchemy import select

    result = await async_session.execute(
        select(ClientORM).where(ClientORM.id == str(returned_client.id))
    )
    orm = result.scalar_one_or_none()
    assert orm is not None
    assert orm.name == "Test Client"


@pytest.mark.asyncio
async def test_add_many_returns_list_of_clients(async_session):
    repo = SQLAlchemyClientRepository(async_session)
    clients = [
        Client(
            id=uuid4(),
            scenario_id=uuid4(),
            name=f"Client {i}",
            sector_description=None,
            payment_history_pattern=PaymentPattern.ON_TIME,
        )
        for i in range(2)
    ]
    returned_clients = await repo.add_many(clients)
    assert len(returned_clients) == 2
    for client in returned_clients:
        assert isinstance(client, Client)
        assert isinstance(client.id, UUID)
    # Verify both are in the database
    from sqlalchemy import select

    result = await async_session.execute(select(ClientORM))
    orms = result.scalars().all()
    assert len(orms) == 2
    names = {orm.name for orm in orms}
    assert names == {"Client 0", "Client 1"}


@pytest.mark.asyncio
async def test_get_by_scenario_id_returns_list_of_clients(async_session):
    repo = SQLAlchemyClientRepository(async_session)
    scenario_id = uuid4()
    # Create two clients directly in the DB
    from sqlalchemy import insert

    await async_session.execute(
        insert(ClientORM).values(
            [
                {
                    "id": str(uuid4()),
                    "scenario_id": str(scenario_id),
                    "name": "Client A",
                    "sector_description": None,
                    "payment_history_pattern": PaymentPattern.ON_TIME.value,
                },
                {
                    "id": str(uuid4()),
                    "scenario_id": str(scenario_id),
                    "name": "Client B",
                    "sector_description": None,
                    "payment_history_pattern": PaymentPattern.ON_TIME.value,
                },
            ]
        )
    )
    await async_session.commit()
    # Now call the method
    clients = await repo.get_by_scenario_id(scenario_id)
    assert len(clients) == 2
    assert all(isinstance(c, Client) for c in clients)
    names = {c.name for c in clients}
    assert names == {"Client A", "Client B"}


@pytest.mark.asyncio
async def test_get_by_id_returns_client_or_none(async_session):
    repo = SQLAlchemyClientRepository(async_session)
    # Create a client
    client_id = uuid4()
    from sqlalchemy import insert

    await async_session.execute(
        insert(ClientORM).values(
            {
                "id": str(client_id),
                "scenario_id": str(uuid4()),
                "name": "Client To Find",
                "sector_description": None,
                "payment_history_pattern": PaymentPattern.ON_TIME.value,
            }
        )
    )
    await async_session.commit()
    # Fetch by ID
    client = await repo.get_by_id(client_id)
    assert isinstance(client, Client)
    assert client.id == client_id
    assert client.name == "Client To Find"
    # Fetch non-existing ID
    client = await repo.get_by_id(uuid4())
    assert client is None
