"""Turn a scored scenario into a collections queue (RF-03.1–03.2).

Thin by design: the arithmetic lives in ``prioritizer`` and the contract in
``prioritized_case``. This use case exists to bind them to a :class:`ScoringRun`,
which is the single object s4.5-API receives.

Deliberately separate from ``ScoreScenario``. E5's rescore-after-contact flow
(s4.6) needs to re-rank a portfolio without re-fitting a model, and merging the
two would make that impossible without either re-scoring or reaching past the
use case.
"""

from app.application.services.prioritizer import prioritize
from app.application.use_cases.score_scenario import ScoringRun
from app.domain.value_objects.prioritized_case import (
    DEFAULT_PARETO_THRESHOLD,
    PrioritizedPortfolio,
)


class PrioritizeScenario:
    """Ranks a scored portfolio and identifies where its value concentrates."""

    def execute(
        self, scoring_run: ScoringRun, threshold: float = DEFAULT_PARETO_THRESHOLD
    ) -> PrioritizedPortfolio:
        """Return the ranked portfolio and its value-concentrating subset.

        Clients with no outstanding balance never reach here: they are absent from
        ``scoring_run.scores`` by ADR-006 D4, because "will this be collected" is
        undefined when there is nothing to collect. They are therefore absent from
        the queue rather than ranked last, which would imply they had been
        assessed and found hopeless.
        """
        scores = {str(score.client_id): score.score_value for score in scoring_run.scores}
        return prioritize(scores, scoring_run.outstanding_by_client, threshold=threshold)
