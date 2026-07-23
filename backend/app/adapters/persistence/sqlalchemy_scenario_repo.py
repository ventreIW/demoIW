from uuid import UUID, uuid4

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.persistence.mappers import (
    scenario_domain_to_orm,
    scenario_orm_to_domain,
)
from app.adapters.persistence.models import ClientORM, InvoiceORM, PaymentORM, ScenarioORM
from app.domain.entities.scenario import Scenario
from app.domain.enums import PaymentPattern, ScenarioStatus
from app.domain.exceptions import EntityNotFoundError
from app.domain.value_objects.raw_dataset import RawDataset
from app.ports.repositories import IScenarioRepository


class SQLAlchemyScenarioRepository(IScenarioRepository):
    """SQLAlchemy implementation of IScenarioRepository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_all(self) -> list[Scenario]:
        result = await self._session.execute(
            select(ScenarioORM).order_by(ScenarioORM.created_at.desc())
        )
        return [scenario_orm_to_domain(row) for row in result.scalars()]

    async def get_by_id(self, scenario_id: UUID) -> Scenario | None:
        result = await self._session.execute(
            select(ScenarioORM).where(ScenarioORM.id == str(scenario_id))
        )
        orm = result.scalar_one_or_none()
        return scenario_orm_to_domain(orm) if orm else None

    async def add(self, scenario: Scenario) -> Scenario:
        orm = scenario_domain_to_orm(scenario)
        # Ensure a new UUID is assigned server-side
        orm.id = str(uuid4())
        self._session.add(orm)
        await self._session.commit()
        return scenario_orm_to_domain(orm)

    async def set_active(self, scenario_id: UUID) -> Scenario:
        scenario_id_str = str(scenario_id)

        # Verify the scenario exists
        target = await self._session.execute(
            select(ScenarioORM).where(ScenarioORM.id == scenario_id_str)
        )
        target_orm = target.scalar_one_or_none()
        if target_orm is None:
            raise EntityNotFoundError("Scenario", scenario_id_str)

        # Deactivate any currently active scenario
        await self._session.execute(
            update(ScenarioORM)
            .where(ScenarioORM.status == ScenarioStatus.ACTIVE.value)
            .values(status=ScenarioStatus.INACTIVE.value)
        )

        # Activate the target
        await self._session.execute(
            update(ScenarioORM)
            .where(ScenarioORM.id == scenario_id_str)
            .values(status=ScenarioStatus.ACTIVE.value)
        )

        await self._session.commit()

        # Refresh to get updated state
        refreshed = await self._session.execute(
            select(ScenarioORM).where(ScenarioORM.id == scenario_id_str)
        )
        return scenario_orm_to_domain(refreshed.scalar_one())

    async def get_active(self) -> Scenario | None:
        result = await self._session.execute(
            select(ScenarioORM).where(ScenarioORM.status == ScenarioStatus.ACTIVE.value)
        )
        orm = result.scalar_one_or_none()
        return scenario_orm_to_domain(orm) if orm else None

    async def get_client_count(self, scenario_id: UUID) -> int:
        result = await self._session.execute(
            select(func.count()).where(ClientORM.scenario_id == str(scenario_id))
        )
        return result.scalar_one()

    async def create_from_csv(self, scenario: Scenario, rows: list[dict[str, str]]) -> Scenario:
        """Create a scenario with clients and invoices from parsed CSV rows."""
        from datetime import UTC, datetime
        orm = scenario_domain_to_orm(scenario)
        orm.id = str(uuid4())
        self._session.add(orm)
        for row in rows:
            client_id = str(uuid4())
            client_orm = ClientORM(
                id=client_id,
                scenario_id=orm.id,
                name=row["client_name"],
                sector_description=None,
                payment_history_pattern=PaymentPattern.ON_TIME.value,
            )
            self._session.add(client_orm)
            due_date = datetime.strptime(row["due_date"], "%Y-%m-%d").replace(tzinfo=UTC)
            days_overdue = max(0, (datetime.now(UTC) - due_date).days)
            invoice_orm = InvoiceORM(
                id=str(uuid4()),
                client_id=client_id,
                folio=row["invoice_id"],
                amount=float(row["amount"]),
                issue_date=datetime.now(UTC),
                due_date=due_date,
                days_overdue=days_overdue,
                status="pending",
            )
            self._session.add(invoice_orm)
        await self._session.commit()
        return scenario_orm_to_domain(orm)

    async def get_raw_dataset(self, scenario_id: UUID) -> RawDataset | None:
        """Return raw dataset (clients, invoices, payments) as DataFrames for scoring."""
        import pandas as pd
        from sqlalchemy import select

        scenario_id_str = str(scenario_id)

        # Fetch clients
        clients_result = await self._session.execute(
            select(ClientORM).where(ClientORM.scenario_id == scenario_id_str)
        )
        clients = clients_result.scalars().all()

        if not clients:
            return None

        client_ids = [str(c.id) for c in clients]

        # Fetch invoices (join through client)
        invoices_result = await self._session.execute(
            select(InvoiceORM).where(InvoiceORM.client_id.in_(client_ids))
        )
        invoices = invoices_result.scalars().all()

        invoice_ids = [str(i.id) for i in invoices]

        # Fetch payments (join through invoice)
        payments_result = await self._session.execute(
            select(PaymentORM).where(PaymentORM.invoice_id.in_(invoice_ids))
        )
        payments = payments_result.scalars().all()

        # Convert to DataFrames
        clients_df = pd.DataFrame([{
            "id": str(c.id),
            "scenario_id": str(c.scenario_id),
            "name": c.name,
            "sector_description": c.sector_description,
            "payment_history_pattern": c.payment_history_pattern,
        } for c in clients])

        invoices_df = pd.DataFrame([{
            "id": str(i.id),
            "client_id": str(i.client_id),
            "folio": i.folio,
            "amount": i.amount,
            "issue_date": i.issue_date,
            "due_date": i.due_date,
            "days_overdue": i.days_overdue,
            "status": i.status,
        } for i in invoices])

        payments_df = pd.DataFrame([{
            "id": str(p.id),
            "invoice_id": str(p.invoice_id),
            "amount": p.amount,
            "paid_date": p.payment_date,
        } for p in payments])

        return RawDataset(
            clients=clients_df,
            invoices=invoices_df,
            payments=payments_df,
        )
