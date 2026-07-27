from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.persistence.mappers import (
    score_domain_to_orm,
    score_orm_to_domain,
)
from app.adapters.persistence.models import ScoreORM
from app.domain.entities.score import Score
from app.ports.repositories import IScoreRepository


class SQLAlchemyScoreRepository(IScoreRepository):
    """SQLAlchemy implementation of IScoreRepository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add_many(self, scores: list[Score]) -> list[Score]:
        """Persist multiple scores and return them.

        Unlike clients (server-assigned ids), a Score carries its own id from the
        scorer, so the provided id is persisted as-is via the mapper.
        """
        orms = [score_domain_to_orm(score) for score in scores]
        self._session.add_all(orms)
        await self._session.commit()
        return [score_orm_to_domain(orm) for orm in orms]

    async def get_by_scenario(self, scenario_id: UUID) -> list[Score]:
        """Return all scores associated with a scenario."""
        result = await self._session.execute(
            select(ScoreORM).where(ScoreORM.scenario_id == str(scenario_id))
        )
        return [score_orm_to_domain(orm) for orm in result.scalars()]
