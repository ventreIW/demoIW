from uuid import UUID, uuid4

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.persistence.mappers import (
    scenario_domain_to_orm,
    scenario_orm_to_domain,
)
from app.adapters.persistence.models import ClientORM, ScenarioORM
from app.domain.entities.scenario import Scenario
from app.domain.enums import ScenarioStatus
from app.domain.exceptions import EntityNotFoundError
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
            select(ScenarioORM).where(
                ScenarioORM.status == ScenarioStatus.ACTIVE.value
            )
        )
        orm = result.scalar_one_or_none()
        return scenario_orm_to_domain(orm) if orm else None

    async def get_client_count(self, scenario_id: UUID) -> int:
        result = await self._session.execute(
            select(func.count()).where(
                ClientORM.scenario_id == str(scenario_id)
            )
        )
        return result.scalar_one()
