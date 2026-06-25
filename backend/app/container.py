from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.persistence.sqlalchemy_scenario_repo import (
    SQLAlchemyScenarioRepository,
)
from app.infrastructure.database import get_session
from app.ports.repositories import IScenarioRepository


async def get_scenario_repo(
    session: AsyncSession = Depends(get_session),
) -> IScenarioRepository:
    """Dependency that provides an IScenarioRepository implementation."""
    return SQLAlchemyScenarioRepository(session)
