from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from app.application.use_cases.record_contact_result import (
    RecordContactResult,
    RecordContactResultRequest,
    RecordContactResultResponse,
)
from app.domain.entities.client import Client
from app.domain.entities.contact_result import ContactResult
from app.domain.enums import (
    ContactResultType,
    PaymentPattern,
    ScenarioStatus,
    ScoreCategory,
    Sector,
)
from app.domain.exceptions import EntityNotFoundError
from app.domain.value_objects.prioritized_case import PrioritizedCase, PrioritizedPortfolio


def _scenario(scenario_id: UUID):
    from app.domain.entities.scenario import Scenario

    return Scenario(
        id=scenario_id,
        name="Test Scenario",
        sector=Sector.RETAIL,
        seed=42,
        parameters={},
        source="procedural",
        status=ScenarioStatus.ACTIVE,
        created_at=datetime.now(UTC),
    )


def _client(client_id: UUID, scenario_id: UUID):
    return Client(
        id=client_id,
        scenario_id=scenario_id,
        name="Test Client",
        sector_description=None,
        payment_history_pattern=PaymentPattern.ON_TIME,
    )


def _portfolio(cases=None):
    if cases is None:
        cases = []
    return PrioritizedPortfolio(
        cases=cases,
        pareto_subset=[],
        threshold=0.8,
    )


def _prioritized_case(client_id: UUID, score: float = 50.0):
    return PrioritizedCase(
        client_id=str(client_id),
        client_name="Test Client",
        score=score,
        outstanding=1000.0,
        days_overdue=30,
        rank=1,
        category=ScoreCategory.MEDIUM,
    )


class FakeScenarioRepo:
    def __init__(self, scenario=None, dataset=None):
        self._scenario = scenario
        self._dataset = dataset

    async def get_by_id(self, scenario_id: UUID):
        return self._scenario

    async def get_raw_dataset(self, scenario_id: UUID):
        return self._dataset


class FakeClientRepo:
    def __init__(self, client=None):
        self._client = client

    async def get_by_id(self, client_id: UUID):
        return self._client


class FakeContactResultRepo:
    def __init__(self):
        self.added = []

    async def add(self, contact_result: ContactResult) -> ContactResult:
        self.added.append(contact_result)
        return contact_result

    async def get_by_client_id(self, client_id: UUID):
        return [c for c in self.added if c.client_id == client_id]


class FakeRescoreScenario:
    def __init__(self, portfolio=None):
        self._portfolio = portfolio or _portfolio()
        self.called_with = None

    async def execute(
        self, scenario_id: UUID, client_id: UUID, contact_result: str, repo
    ) -> PrioritizedPortfolio:
        self.called_with = (scenario_id, client_id, contact_result, repo)
        return self._portfolio


@pytest.mark.asyncio
async def test_record_contact_result_persists_and_calls_rescore():
    scenario_id = uuid4()
    client_id = uuid4()

    scenario_repo = FakeScenarioRepo(scenario=_scenario(scenario_id))
    client_repo = FakeClientRepo(client=_client(client_id, scenario_id))
    contact_result_repo = FakeContactResultRepo()
    rescore = FakeRescoreScenario()

    use_case = RecordContactResult(
        scenario_repo=scenario_repo,
        client_repo=client_repo,
        contact_result_repo=contact_result_repo,
        rescore_use_case=rescore,
    )

    request = RecordContactResultRequest(
        scenario_id=scenario_id,
        client_id=client_id,
        contact_result=ContactResultType.PROMISE_TO_PAY,
        notes="Client promised to pay Friday",
    )

    response = await use_case.execute(request)

    # Contact result persisted
    assert len(contact_result_repo.added) == 1
    cr = contact_result_repo.added[0]
    assert cr.client_id == client_id
    assert cr.result_type == ContactResultType.PROMISE_TO_PAY
    assert cr.notes == "Client promised to pay Friday"

    # Rescore called with correct params
    assert rescore.called_with is not None
    assert rescore.called_with[0] == scenario_id
    assert rescore.called_with[1] == client_id
    assert rescore.called_with[2] == "promise_to_pay"

    # Response contains updated portfolio
    assert isinstance(response, RecordContactResultResponse)
    assert response.scenario_id == scenario_id
    assert response.client_id == client_id


@pytest.mark.asyncio
async def test_record_contact_result_scenario_not_found():
    scenario_id = uuid4()
    client_id = uuid4()

    scenario_repo = FakeScenarioRepo(scenario=None)
    client_repo = FakeClientRepo()
    contact_result_repo = FakeContactResultRepo()
    rescore = FakeRescoreScenario()

    use_case = RecordContactResult(
        scenario_repo=scenario_repo,
        client_repo=client_repo,
        contact_result_repo=contact_result_repo,
        rescore_use_case=rescore,
    )

    request = RecordContactResultRequest(
        scenario_id=scenario_id,
        client_id=client_id,
        contact_result=ContactResultType.PROMISE_TO_PAY,
    )

    with pytest.raises(EntityNotFoundError):
        await use_case.execute(request)


@pytest.mark.asyncio
async def test_record_contact_result_client_not_found():
    scenario_id = uuid4()
    client_id = uuid4()

    scenario_repo = FakeScenarioRepo(scenario=_scenario(scenario_id))
    client_repo = FakeClientRepo(client=None)
    contact_result_repo = FakeContactResultRepo()
    rescore = FakeRescoreScenario()

    use_case = RecordContactResult(
        scenario_repo=scenario_repo,
        client_repo=client_repo,
        contact_result_repo=contact_result_repo,
        rescore_use_case=rescore,
    )

    request = RecordContactResultRequest(
        scenario_id=scenario_id,
        client_id=client_id,
        contact_result=ContactResultType.PROMISE_TO_PAY,
    )

    with pytest.raises(EntityNotFoundError):
        await use_case.execute(request)
