"""Score every collectable client in a scenario (RF-02.1–02.2).

Composes the pieces: build a labelled training set (s4.2), fit the model, score
every client, band each score, and return :class:`Score` entities.

**Nothing is persisted here.** ``IScoreRepository`` is s4.9 and unmerged, so this
use case hands entities back and the caller decides what to do with them. That
keeps the story shippable without taking another developer's work.

**Clients with no outstanding balance are absent, not zero.** A score of 0 would
read as "certain not to collect", which is a claim about a client that has nothing
to collect. They are counted in ``unscored_client_count`` instead.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.adapters.scoring.evaluator import evaluate
from app.adapters.scoring.sklearn_scorer import SklearnScorer
from app.application.services.score_categorizer import categorize
from app.application.use_cases.build_training_set import BuildTrainingSet
from app.domain.entities.score import Score
from app.domain.value_objects.raw_dataset import RawDataset
from app.domain.value_objects.scoring_result import EvaluationMetrics
from app.ports.scoring_port import IScoringPort


@dataclass(frozen=True)
class ScoringRun:
    """Outcome of scoring one scenario."""

    scores: list[Score]
    evaluation: EvaluationMetrics
    unscored_client_count: int


class ScoreScenario:
    """Fits a model on a scenario's own data and scores every collectable client."""

    def __init__(self, scorer: IScoringPort | None = None) -> None:
        self._scorer = scorer or SklearnScorer()
        self._builder = BuildTrainingSet()

    def execute(self, dataset: RawDataset, scenario_id: UUID, seed: int) -> ScoringRun:
        training_set = self._builder.execute(dataset, seed=seed)

        self._scorer.fit(training_set)
        scores = self._scorer.predict_scores(training_set.X)

        held_out_scores = scores.iloc[training_set.test_index]
        evaluation = evaluate(training_set.y_test, held_out_scores.reset_index(drop=True))

        scored_at = datetime.now(UTC)
        entities = [
            Score(
                id=uuid4(),
                client_id=UUID(client_id),
                scenario_id=scenario_id,
                score_value=round(float(score_value), 2),
                category=categorize(float(score_value)),
                explanation=_placeholder_explanation(float(score_value)),
                scored_at=scored_at,
            )
            for client_id, score_value in zip(training_set.client_ids, scores, strict=True)
        ]

        return ScoringRun(
            scores=entities,
            evaluation=evaluation,
            unscored_client_count=training_set.excluded_client_count,
        )


def _placeholder_explanation(score_value: float) -> str:
    """Minimal explanation text.

    s4.4 replaces this with ranked top-factor attribution from
    ``IScoringPort.feature_contributions``. Kept non-empty so the ``Score``
    contract holds and the field is never silently blank.
    """
    return f"Probabilidad estimada de cobro en 90 días: {score_value:.0f}%."
