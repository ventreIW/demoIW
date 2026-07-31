from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.persistence.mappers import (
    contact_result_domain_to_orm,
    contact_result_orm_to_domain,
)
from app.adapters.persistence.models import ContactResultORM
from app.domain.entities.contact_result import ContactResult
from app.ports.repositories import IContactResultRepository


class SQLAlchemyContactResultRepository(IContactResultRepository):
    """SQLAlchemy implementation of IContactResultRepository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, contact_result: ContactResult) -> ContactResult:
        """Persist a new contact result and return it with assigned ID."""
        orm = contact_result_domain_to_orm(contact_result)
        orm.id = str(uuid4())
        self._session.add(orm)
        await self._session.commit()
        return contact_result_orm_to_domain(orm)

    async def get_by_client_id(self, client_id: UUID) -> list[ContactResult]:
        """Return all contact results for a client ordered by recorded_at desc."""
        result = await self._session.execute(
            select(ContactResultORM)
            .where(ContactResultORM.client_id == str(client_id))
            .order_by(ContactResultORM.recorded_at.desc())
        )
        return [contact_result_orm_to_domain(orm) for orm in result.scalars()]
