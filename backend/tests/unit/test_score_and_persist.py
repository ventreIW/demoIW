from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pandas as pd
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.adapters.persistence.models import Base
from app.adapters.persistence.sqlalchemy_score_repo import SQLAlchemyScoreRepository
from app.application.use_cases.score_and_persist_scenario import (
    ScoreAndPersistScenario,
    ScorePersistResult,
)
from app.application.use_cases.score_scenario import ScoringRun
from app.domain.entities.score import Score
from app.domain.enums import ScenarioStatus, ScoreCategory, Sector
from app.domain.exceptions import EntityNotFoundError
from app.domain.value_objects.raw_dataset import RawDataset


@pytest.fixture
async def async_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)()
    yield session
    await session.close()
    await engine.dispose()


def _scenario(scenario_id: UUID):
    from app.domain.entities.scenario import Scenario

    return Scenario(
        id=scenario_id,
        name="S",
        sector=Sector.RETAIL,
        seed=42,
        parameters={},
        source="procedural",
        status=ScenarioStatus.ACTIVE,
        created_at=datetime.now(UTC),
    )


def _scores(scenario_id: UUID, n: int) -> list[Score]:
    return [
        Score(
            id=uuid4(),
            client_id=uuid4(),
            scenario_id=scenario_id,
            score_value=float(50 + i),
            category=ScoreCategory.MEDIUM,
            explanation="x",
            scored_at=datetime(2026, 7, 27, tzinfo=UTC),
        )
        for i in range(n)
    ]


def _fake_scorer(scores: list[Score], unscored: int) -> MagicMock:
    scorer = MagicMock()
    scorer.execute.return_value = ScoringRun(
        scores=scores,
        evaluation=MagicMock(),
        unscored_client_count=unscored,
        outstanding_by_client={},
        name_by_client={},
        days_overdue_by_client={},
    )
    return scorer


def _empty_dataset() -> RawDataset:
    return RawDataset(clients=pd.DataFrame(), invoices=pd.DataFrame(), payments=pd.DataFrame())


@pytest.mark.asyncio
async def test_scores_and_persists_all_clients(async_session) -> None:
    scenario_id = uuid4()
    scores = _scores(scenario_id, 3)
    scenario_repo = AsyncMock()
    scenario_repo.get_by_id.return_value = _scenario(scenario_id)
    scenario_repo.get_raw_dataset.return_value = _empty_dataset()
    score_repo = SQLAlchemyScoreRepository(async_session)

    use_case = ScoreAndPersistScenario(
        scenario_repo=scenario_repo,
        score_repo=score_repo,
        scorer=_fake_scorer(scores, unscored=2),
    )
    result = await use_case.execute(scenario_id)

    assert isinstance(result, ScorePersistResult)
    assert result.scored_count == 3
    assert result.unscored_count == 2
    assert result.already_persisted is False
    persisted = await score_repo.get_by_scenario(scenario_id)
    assert len(persisted) == 3


@pytest.mark.asyncio
async def test_idempotent_no_duplicate_rows(async_session) -> None:
    scenario_id = uuid4()
    scores = _scores(scenario_id, 3)
    scenario_repo = AsyncMock()
    scenario_repo.get_by_id.return_value = _scenario(scenario_id)
    scenario_repo.get_raw_dataset.return_value = _empty_dataset()
    score_repo = SQLAlchemyScoreRepository(async_session)
    use_case = ScoreAndPersistScenario(
        scenario_repo=scenario_repo, score_repo=score_repo, scorer=_fake_scorer(scores, 0)
    )

    await use_case.execute(scenario_id)
    second = await use_case.execute(scenario_id)

    assert second.already_persisted is True
    assert second.scored_count == 3
    assert len(await score_repo.get_by_scenario(scenario_id)) == 3  # no duplicates


@pytest.mark.asyncio
async def test_missing_scenario_raises_not_found(async_session) -> None:
    scenario_repo = AsyncMock()
    scenario_repo.get_by_id.return_value = None
    use_case = ScoreAndPersistScenario(
        scenario_repo=scenario_repo,
        score_repo=SQLAlchemyScoreRepository(async_session),
        scorer=_fake_scorer([], 0),
    )
    with pytest.raises(EntityNotFoundError):
        await use_case.execute(uuid4())


@pytest.mark.asyncio
async def test_no_dataset_raises_not_found(async_session) -> None:
    scenario_id = uuid4()
    scenario_repo = AsyncMock()
    scenario_repo.get_by_id.return_value = _scenario(scenario_id)
    scenario_repo.get_raw_dataset.return_value = None
    use_case = ScoreAndPersistScenario(
        scenario_repo=scenario_repo,
        score_repo=SQLAlchemyScoreRepository(async_session),
        scorer=_fake_scorer([], 0),
    )
    with pytest.raises(EntityNotFoundError):
        await use_case.execute(scenario_id)
