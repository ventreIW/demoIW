from uuid import UUID, uuid4
from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.persistence.mappers import (
    payment_domain_to_orm,
    payment_orm_to_domain,
)
from app.adapters.persistence.models import PaymentORM, InvoiceORM, ClientORM
from app.domain.entities.payment import Payment
from app.ports.repositories import IPaymentRepository


class SQLAlchemyPaymentRepository(IPaymentRepository):
    """SQLAlchemy implementation of IPaymentRepository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, payment: Payment) -> Payment:
        """Persist a new payment and return it with assigned ID."""
        orm = payment_domain_to_orm(payment)
        # Ensure a new UUID is assigned server-side
        orm.id = str(uuid4())
        self._session.add(orm)
        await self._session.commit()
        return payment_orm_to_domain(orm)

    async def add_many(self, payments: List[Payment]) -> List[Payment]:
        """Persist multiple new payments and return them with assigned IDs."""
        orms = []
        for payment in payments:
            orm = payment_domain_to_orm(payment)
            orm.id = str(uuid4())
            self._session.add(orm)
            orms.append(orm)
        await self._session.commit()
        return [payment_orm_to_domain(orm) for orm in orms]

    async def get_by_scenario_id(self, scenario_id: UUID) -> List[Payment]:
        """Return all payments associated with a scenario via invoice and client."""
        result = await self._session.execute(
            select(PaymentORM)
            .join(InvoiceORM, PaymentORM.invoice_id == InvoiceORM.id)
            .join(ClientORM, InvoiceORM.client_id == ClientORM.id)
            .where(ClientORM.scenario_id == str(scenario_id))
        )
        return [payment_orm_to_domain(orm) for orm in result.scalars()]

    async def get_by_id(self, payment_id: UUID) -> Payment | None:
        """Return a single payment by ID, or None if not found."""
        result = await self._session.execute(
            select(PaymentORM).where(PaymentORM.id == str(payment_id))
        )
        orm = result.scalar_one_or_none()
        return payment_orm_to_domain(orm) if orm else None