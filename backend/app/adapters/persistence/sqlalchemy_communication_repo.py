from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.persistence.mappers import (
    communication_domain_to_orm,
    communication_orm_to_domain,
)
from app.adapters.persistence.models import CommunicationORM
from app.domain.entities.communication import Communication
from app.ports.repositories import ICommunicationRepository


class SQLAlchemyCommunicationRepository(ICommunicationRepository):
    """SQLAlchemy implementation of ICommunicationRepository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, communication: Communication) -> Communication:
        """Persist a new communication and return it with assigned ID."""
        orm = communication_domain_to_orm(communication)
        orm.id = str(uuid4())
        self._session.add(orm)
        await self._session.commit()
        return communication_orm_to_domain(orm)

    async def get_by_id(self, communication_id: UUID) -> Communication | None:
        """Return a single communication by ID, or None if not found."""
        result = await self._session.execute(
            select(CommunicationORM).where(CommunicationORM.id == str(communication_id))
        )
        orm = result.scalar_one_or_none()
        return communication_orm_to_domain(orm) if orm else None

    async def update(self, communication: Communication) -> Communication:
        """Update an existing communication and return it."""
        orm = communication_domain_to_orm(communication)
        merged = await self._session.merge(orm)
        await self._session.commit()
        return communication_orm_to_domain(merged)

    async def get_by_client_id(self, client_id: UUID) -> list[Communication]:
        """Return all communications for a client ordered by created_at desc."""
        result = await self._session.execute(
            select(CommunicationORM)
            .where(CommunicationORM.client_id == str(client_id))
            .order_by(CommunicationORM.created_at.desc())
        )
        return [communication_orm_to_domain(orm) for orm in result.scalars()]
