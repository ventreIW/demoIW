"""Rescore a client's score after a contact result (s4.6).

Adjusts a client's score based on contact outcome and re-ranks the portfolio
using the existing PrioritizeScenario use case.
"""

from uuid import UUID

from app.application.services.prioritizer import prioritize
from app.application.use_cases.prioritize_scenario import PrioritizeScenario
from app.application.use_cases.score_scenario import ScoreScenario
from app.domain.value_objects.prioritized_case import PrioritizedPortfolio
from app.ports.repositories import IScenarioRepository

# Score adjustment deltas for each contact result type
# Using actual ContactResultType enum string values
_CONTACT_RESULT_DELTA = {
    "promise_to_pay": 10.0,
    "partial_payment": 5.0,
    "no_answer": 0.0,
    "disputed": 0.0,
    "paid": 0.0,
}


class RescoreScenario:
    """Adjust a client's score based on contact result and re-rank the portfolio."""

    def __init__(self) -> None:
        self._scorer = ScoreScenario()
        self._prioritizer = PrioritizeScenario()

    async def execute(
        self,
        scenario_id: UUID,
        client_id: UUID,
        contact_result: str,
        repo: IScenarioRepository,
    ) -> PrioritizedPortfolio:
        """Rescore a client and return updated portfolio.

        Args:
            scenario_id: The scenario ID
            client_id: The client ID to rescore
            contact_result: The contact result type (string matching ContactResultType)
            repo: Scenario repository for fetching raw data

        Returns:
            Updated PrioritizedPortfolio with re-ranked cases
        """
        # Fetch raw dataset
        dataset = await repo.get_raw_dataset(scenario_id)
        if dataset is None:
            raise ValueError(f"Scenario {scenario_id} has no data")

        # Score the scenario
        scoring_run = self._scorer.execute(dataset, scenario_id, seed=42)

        # Find the client's current score
        current_score = None
        for score in scoring_run.scores:
            if str(score.client_id) == str(client_id):
                current_score = score.score_value
                break

        if current_score is None:
            raise ValueError(f"Client {client_id} not found in scenario {scenario_id}")

        # Apply score adjustment
        delta = _CONTACT_RESULT_DELTA.get(contact_result, 0.0)
        adjusted_score = max(0.0, min(100.0, current_score + delta))

        # Build scores dict with adjusted score
        scores = {
            str(score.client_id): (
                adjusted_score if str(score.client_id) == str(client_id) else score.score_value
            )
            for score in scoring_run.scores
        }

        # Re-rank using prioritizer
        portfolio = prioritize(scores, scoring_run.outstanding_by_client)

        return portfolio
