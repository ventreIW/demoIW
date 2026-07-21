from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.persistence.mappers import (
    client_domain_to_orm,
    client_orm_to_domain,
)
from app.adapters.persistence.models import ClientORM
from app.domain.entities.client import Client
from app.ports.repositories import IClientRepository


class SQLAlchemyClientRepository(IClientRepository):
    """SQLAlchemy implementation of IClientRepository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, client: Client) -> Client:
        """Persist a new client and return it with assigned ID."""
        orm = client_domain_to_orm(client)
        # Ensure a new UUID is assigned server-side
        orm.id = str(uuid4())
        self._session.add(orm)
        await self._session.commit()
        return client_orm_to_domain(orm)

    async def add_many(self, clients: list[Client]) -> list[Client]:
        """Persist multiple new clients and return them with assigned IDs."""
        orms = []
        for client in clients:
            orm = client_domain_to_orm(client)
            orm.id = str(uuid4())
            self._session.add(orm)
            orms.append(orm)
        await self._session.commit()
        return [client_orm_to_domain(orm) for orm in orms]

    async def get_by_scenario_id(self, scenario_id: UUID) -> list[Client]:
        """Return all clients associated with a scenario."""
        result = await self._session.execute(
            select(ClientORM).where(ClientORM.scenario_id == str(scenario_id))
        )
        return [client_orm_to_domain(orm) for orm in result.scalars()]

    async def get_by_id(self, client_id: UUID) -> Client | None:
        """Return a single client by ID, or None if not found."""
        result = await self._session.execute(
            select(ClientORM).where(ClientORM.id == str(client_id))
        )
        orm = result.scalar_one_or_none()
        return client_orm_to_domain(orm) if orm else None
