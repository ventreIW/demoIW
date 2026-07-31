"""Record a contact result and trigger rescore (E5 s5.3).

Orchestrates: persist ContactResult -> update client status -> call RescoreScenario
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.application.use_cases.rescore_scenario import RescoreScenario
from app.domain.entities.contact_result import ContactResult
from app.domain.enums import ContactResultType
from app.domain.exceptions import EntityNotFoundError
from app.domain.value_objects.prioritized_case import PrioritizedPortfolio
from app.ports.repositories import (
    IClientRepository,
    IContactResultRepository,
    IScenarioRepository,
)


@dataclass(frozen=True)
class RecordContactResultRequest:
    """Input for recording a contact result."""

    scenario_id: UUID
    client_id: UUID
    contact_result: ContactResultType
    notes: str | None = None


@dataclass(frozen=True)
class RecordContactResultResponse:
    """Output from recording a contact result - the updated portfolio."""

    scenario_id: UUID
    client_id: UUID
    portfolio: PrioritizedPortfolio


class RecordContactResult:
    """Persist contact result and trigger portfolio rescore."""

    def __init__(
        self,
        scenario_repo: IScenarioRepository,
        client_repo: IClientRepository,
        contact_result_repo: IContactResultRepository,
        rescore_use_case: RescoreScenario,
    ) -> None:
        self._scenario_repo = scenario_repo
        self._client_repo = client_repo
        self._contact_result_repo = contact_result_repo
        self._rescore_use_case = rescore_use_case

    async def execute(self, request: RecordContactResultRequest) -> RecordContactResultResponse:
        # 1. Verify scenario exists
        scenario = await self._scenario_repo.get_by_id(request.scenario_id)
        if scenario is None:
            raise EntityNotFoundError("Scenario", str(request.scenario_id))

        # 2. Verify client exists
        client = await self._client_repo.get_by_id(request.client_id)
        if client is None:
            raise EntityNotFoundError("Client", str(request.client_id))

        # 3. Persist ContactResult
        contact_result = ContactResult(
            id=uuid4(),
            client_id=request.client_id,
            communication_id=None,  # s5.4 will link when communication is generated
            result_type=request.contact_result,
            notes=request.notes,
            recorded_at=datetime.now(UTC),
        )
        await self._contact_result_repo.add(contact_result)

        # 4. Trigger rescore (uses string enum value per RescoreScenario contract)
        portfolio = await self._rescore_use_case.execute(
            scenario_id=request.scenario_id,
            client_id=request.client_id,
            contact_result=request.contact_result.value,
            repo=self._scenario_repo,
        )

        return RecordContactResultResponse(
            scenario_id=request.scenario_id,
            client_id=request.client_id,
            portfolio=portfolio,
        )
