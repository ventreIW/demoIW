from uuid import UUID, uuid4
from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.persistence.mappers import (
    invoice_domain_to_orm,
    invoice_orm_to_domain,
)
from app.adapters.persistence.models import ClientORM, InvoiceORM
from app.domain.entities.invoice import Invoice
from app.ports.repositories import IInvoiceRepository


class SQLAlchemyInvoiceRepository(IInvoiceRepository):
    """SQLAlchemy implementation of IInvoiceRepository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, invoice: Invoice) -> Invoice:
        """Persist a new invoice and return it with assigned ID."""
        orm = invoice_domain_to_orm(invoice)
        # Ensure a new UUID is assigned server-side
        orm.id = str(uuid4())
        self._session.add(orm)
        await self._session.commit()
        return invoice_orm_to_domain(orm)

    async def add_many(self, invoices: List[Invoice]) -> List[Invoice]:
        """Persist multiple new invoices and return them with assigned IDs."""
        orms = []
        for invoice in invoices:
            orm = invoice_domain_to_orm(invoice)
            orm.id = str(uuid4())
            self._session.add(orm)
            orms.append(orm)
        await self._session.commit()
        return [invoice_orm_to_domain(orm) for orm in orms]

    async def get_by_scenario_id(self, scenario_id: UUID) -> List[Invoice]:
        """Return all invoices associated with a scenario via their client."""
        result = await self._session.execute(
            select(InvoiceORM)
            .join(ClientORM, InvoiceORM.client_id == ClientORM.id)
            .where(ClientORM.scenario_id == str(scenario_id))
        )
        return [invoice_orm_to_domain(orm) for orm in result.scalars()]

    async def get_by_id(self, invoice_id: UUID) -> Invoice | None:
        """Return a single invoice by ID, or None if not found."""
        result = await self._session.execute(
            select(InvoiceORM).where(InvoiceORM.id == str(invoice_id))
        )
        orm = result.scalar_one_or_none()
        return invoice_orm_to_domain(orm) if orm else None