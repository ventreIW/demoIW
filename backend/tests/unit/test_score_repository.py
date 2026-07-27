from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.adapters.persistence.models import Base, ScoreORM
from app.adapters.persistence.sqlalchemy_score_repo import SQLAlchemyScoreRepository
from app.domain.entities.score import Score
from app.domain.enums import ScoreCategory
from app.ports.repositories import IScoreRepository


@pytest.fixture
async def async_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)()
    yield session
    await session.close()
    await engine.dispose()


def _score(scenario_id: UUID, value: float, category: ScoreCategory) -> Score:
    return Score(
        id=uuid4(),
        client_id=uuid4(),
        scenario_id=scenario_id,
        score_value=value,
        category=category,
        explanation="Buen perfil de pago: atraso contenido.",
        scored_at=datetime(2026, 7, 27, 12, 0, tzinfo=UTC),
    )


def test_repository_is_subclass_of_port() -> None:
    assert issubclass(SQLAlchemyScoreRepository, IScoreRepository)


def test_port_declares_required_methods() -> None:
    assert IScoreRepository.add_many.__isabstractmethod__ is True
    assert IScoreRepository.get_by_scenario.__isabstractmethod__ is True


@pytest.mark.asyncio
async def test_add_many_then_get_by_scenario_round_trip(async_session) -> None:
    repo = SQLAlchemyScoreRepository(async_session)
    scenario_id = uuid4()
    scores = [
        _score(scenario_id, 82.5, ScoreCategory.HIGH),
        _score(scenario_id, 55.0, ScoreCategory.MEDIUM),
        _score(scenario_id, 12.0, ScoreCategory.LOW),
    ]
    returned = await repo.add_many(scores)
    assert len(returned) == 3

    fetched = await repo.get_by_scenario(scenario_id)
    assert len(fetched) == 3
    # All persisted rows belong to the scenario.
    result = await async_session.execute(select(ScoreORM))
    assert len(result.scalars().all()) == 3


@pytest.mark.asyncio
async def test_round_trip_preserves_fields(async_session) -> None:
    repo = SQLAlchemyScoreRepository(async_session)
    scenario_id = uuid4()
    original = _score(scenario_id, 82.5, ScoreCategory.HIGH)
    await repo.add_many([original])

    (fetched,) = await repo.get_by_scenario(scenario_id)
    assert fetched.id == original.id
    assert fetched.score_value == 82.5
    assert fetched.category is ScoreCategory.HIGH
    assert fetched.explanation == original.explanation
    assert fetched.scored_at == original.scored_at


@pytest.mark.asyncio
async def test_get_by_scenario_empty_returns_empty_list(async_session) -> None:
    repo = SQLAlchemyScoreRepository(async_session)
    assert await repo.get_by_scenario(uuid4()) == []
