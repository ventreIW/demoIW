"""Score an active scenario and persist every client's Score (E4 gate #1).

Thin orchestration: scoring (`ScoreScenario`) and persistence (`IScoreRepository`)
already exist; this wires them so scores are durable, not just computed in-memory
by the prioritized endpoint. Idempotent — re-running does not duplicate rows.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.application.use_cases.score_scenario import ScoreScenario
from app.domain.exceptions import EntityNotFoundError
from app.ports.repositories import IScenarioRepository, IScoreRepository


@dataclass(frozen=True)
class ScorePersistResult:
    scored_count: int
    unscored_count: int
    already_persisted: bool


class ScoreAndPersistScenario:
    def __init__(
        self,
        scenario_repo: IScenarioRepository,
        score_repo: IScoreRepository,
        scorer: ScoreScenario | None = None,
    ) -> None:
        self._scenario_repo = scenario_repo
        self._score_repo = score_repo
        self._scorer = scorer or ScoreScenario()

    async def execute(self, scenario_id: UUID) -> ScorePersistResult:
        scenario = await self._scenario_repo.get_by_id(scenario_id)
        if scenario is None:
            raise EntityNotFoundError("Scenario", str(scenario_id))

        # Idempotency: if scores already exist, return them without re-inserting.
        existing = await self._score_repo.get_by_scenario(scenario_id)
        if existing:
            return ScorePersistResult(
                scored_count=len(existing), unscored_count=0, already_persisted=True
            )

        dataset = await self._scenario_repo.get_raw_dataset(scenario_id)
        if dataset is None:
            raise EntityNotFoundError("Scenario dataset", str(scenario_id))

        run = self._scorer.execute(dataset, scenario_id, seed=scenario.seed or 42)
        await self._score_repo.add_many(run.scores)
        return ScorePersistResult(
            scored_count=len(run.scores),
            unscored_count=run.unscored_client_count,
            already_persisted=False,
        )
