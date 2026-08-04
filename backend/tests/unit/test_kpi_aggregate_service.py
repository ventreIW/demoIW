"""KPI aggregate service over stub ports (s6.1 T2).

Stubs rather than a database: this layer's job is composition and refusal, and
the arithmetic it composes is already pinned by ``test_portfolio_kpis.py``. The
seeded end-to-end path is ``tests/integration/test_kpi_endpoint.py``.
"""

import ast
import inspect
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pandas as pd
import pytest

from app.application.services import kpi_aggregate_service
from app.application.services.kpi_aggregate_service import fetch_portfolio_kpis
from app.domain.entities.scenario import Scenario
from app.domain.entities.score import Score
from app.domain.enums import ScenarioStatus, ScoreCategory, Sector
from app.domain.exceptions import EntityNotFoundError, PortfolioNotScoredError
from app.domain.value_objects.raw_dataset import RawDataset

_SCENARIO_ID = UUID("3f2b1c4d-5e6f-4a7b-8c9d-0e1f2a3b4c5d")
_A = UUID("11111111-1111-4111-8111-111111111111")
_B = UUID("22222222-2222-4222-8222-222222222222")
_C = UUID("33333333-3333-4333-8333-333333333333")


def _scenario() -> Scenario:
    return Scenario(
        id=_SCENARIO_ID,
        name="Retail Q3",
        sector=Sector.RETAIL,
        seed=42,
        parameters={},
        source="generated",
        status=ScenarioStatus.ACTIVE,
        created_at=datetime(2026, 8, 1, tzinfo=UTC),
    )


def _score(client_id: UUID, value: float, category: ScoreCategory, day: int = 4) -> Score:
    return Score(
        id=uuid4(),
        client_id=client_id,
        scenario_id=_SCENARIO_ID,
        score_value=value,
        category=category,
        explanation="—",
        scored_at=datetime(2026, 8, day, 18, 22, 41, tzinfo=UTC),
    )


def _dataset(*, with_payments: bool = True) -> RawDataset:
    """The worked example from s6.1-story.md, as the repo would return it.

    A — 10,000 open, 4,000 paid · B — 20,000 open · C — 5,000 settled.
    """
    clients = pd.DataFrame(
        [
            {"id": str(_A), "name": "Acme"},
            {"id": str(_B), "name": "Borges"},
            {"id": str(_C), "name": "Cielo"},
        ]
    )
    invoices = pd.DataFrame(
        [
            {
                "id": "i1",
                "client_id": str(_A),
                "amount": 10_000.0,
                "status": "overdue",
                "days_overdue": 95,
                "due_date": datetime(2026, 5, 1, tzinfo=UTC),
            },
            {
                "id": "i2",
                "client_id": str(_B),
                "amount": 20_000.0,
                "status": "overdue",
                "days_overdue": 20,
                "due_date": datetime(2026, 7, 15, tzinfo=UTC),
            },
            {
                "id": "i3",
                "client_id": str(_C),
                "amount": 5_000.0,
                "status": "paid",
                "days_overdue": 0,
                "due_date": datetime(2026, 6, 1, tzinfo=UTC),
            },
        ]
    )
    if with_payments:
        payments = pd.DataFrame(
            [
                {
                    "id": "p1",
                    "invoice_id": "i1",
                    "amount": 4_000.0,
                    "paid_date": datetime(2026, 6, 1, tzinfo=UTC),
                },
                {
                    "id": "p2",
                    "invoice_id": "i3",
                    "amount": 5_000.0,
                    "paid_date": datetime(2026, 6, 10, tzinfo=UTC),
                },
            ]
        )
    else:
        # This is what the repo actually returns when a scenario has no payments:
        # a frame with no columns at all, not an empty frame with a schema.
        payments = pd.DataFrame([])
    return RawDataset(clients=clients, invoices=invoices, payments=payments)


class _StubScenarioRepo:
    def __init__(self, scenario: Scenario | None, dataset: RawDataset | None) -> None:
        self._scenario = scenario
        self._dataset = dataset

    async def get_by_id(self, scenario_id: UUID) -> Scenario | None:
        return self._scenario

    async def get_raw_dataset(self, scenario_id: UUID) -> RawDataset | None:
        return self._dataset


class _StubScoreRepo:
    def __init__(self, scores: list[Score]) -> None:
        self._scores = scores

    async def get_by_scenario(self, scenario_id: UUID) -> list[Score]:
        return self._scores


def _all_scored() -> list[Score]:
    return [
        _score(_A, 80.0, ScoreCategory.HIGH),
        _score(_B, 40.0, ScoreCategory.LOW),
        _score(_C, 90.0, ScoreCategory.HIGH, day=3),
    ]


#: Distinguishes "argument omitted" from "explicitly None", which is the case the
#: no-data test exercises.
_UNSET = object()


async def _fetch(
    *,
    scenario: Scenario | None = None,
    dataset: RawDataset | None | object = _UNSET,
    scores: list[Score] | None = None,
):
    resolved = _dataset() if dataset is _UNSET else dataset
    return await fetch_portfolio_kpis(
        _SCENARIO_ID,
        _StubScenarioRepo(scenario or _scenario(), resolved),  # type: ignore[arg-type]
        _StubScoreRepo(scores if scores is not None else _all_scored()),
    )


# -- refusals ----------------------------------------------------------------


@pytest.mark.anyio
async def test_unknown_scenario_raises_entity_not_found() -> None:
    with pytest.raises(EntityNotFoundError):
        await fetch_portfolio_kpis(_SCENARIO_ID, _StubScenarioRepo(None, None), _StubScoreRepo([]))


@pytest.mark.anyio
async def test_scenario_without_scores_is_refused_not_zeroed() -> None:
    """ADR-009 — an unscored book and a settled book must not look alike."""
    with pytest.raises(PortfolioNotScoredError) as exc:
        await _fetch(scores=[])

    assert str(_SCENARIO_ID) in str(exc.value)
    assert "/score" in str(exc.value)


@pytest.mark.anyio
async def test_scenario_with_no_data_is_refused_not_an_attribute_error() -> None:
    """get_raw_dataset returns None for a scenario with no clients."""
    with pytest.raises(PortfolioNotScoredError):
        await _fetch(dataset=None)


# -- composition -------------------------------------------------------------


@pytest.mark.anyio
async def test_worked_example_end_to_end_over_the_ports() -> None:
    kpis = await _fetch()

    assert kpis.client_count == 3
    assert kpis.total_outstanding == pytest.approx(26_000.0)
    assert kpis.total_expected_recoverable == pytest.approx(12_800.0)
    assert kpis.collected_to_date == pytest.approx(5_000.0)
    assert kpis.cases_by_category == {
        ScoreCategory.HIGH: 2,
        ScoreCategory.MEDIUM: 0,
        ScoreCategory.LOW: 1,
    }


@pytest.mark.anyio
async def test_scenario_metadata_is_carried_through() -> None:
    kpis = await _fetch()

    assert kpis.scenario_id == _SCENARIO_ID
    assert kpis.scenario_name == "Retail Q3"
    assert kpis.sector == Sector.RETAIL


@pytest.mark.anyio
async def test_scored_at_is_the_latest_of_the_persisted_run() -> None:
    """s6.2 renders this so a stale dashboard is legible rather than silent."""
    kpis = await _fetch()

    assert kpis.scored_at == datetime(2026, 8, 4, 18, 22, 41, tzinfo=UTC)


@pytest.mark.anyio
async def test_a_client_without_a_score_is_counted_as_unscored() -> None:
    kpis = await _fetch(scores=[_score(_A, 80.0, ScoreCategory.HIGH)])

    assert kpis.client_count == 1
    assert kpis.unscored_client_count == 2
    # money covers scored clients only, so B's 20,000 is excluded
    assert kpis.total_outstanding == pytest.approx(6_000.0)


@pytest.mark.anyio
async def test_days_overdue_is_the_max_over_open_invoices() -> None:
    """Same rule as the operator queue — a mean flatters an aged account."""
    dataset = _dataset()
    dataset.invoices.loc[len(dataset.invoices)] = {
        "id": "i4",
        "client_id": str(_A),
        "amount": 1_000.0,
        "status": "overdue",
        "days_overdue": 5,
        "due_date": datetime(2026, 7, 30, tzinfo=UTC),
    }
    kpis = await _fetch(dataset=dataset)

    buckets = {b.label: b.client_count for b in kpis.segmentation["days_overdue_bucket"]}
    assert buckets["90+"] == 1  # A stays at 95, not averaged down to 50


@pytest.mark.anyio
async def test_no_payments_yields_zero_collected_not_a_key_error() -> None:
    """payments is a DataFrame with no columns at all when there are none."""
    kpis = await _fetch(dataset=_dataset(with_payments=False))

    assert kpis.collected_to_date == 0.0
    # nothing is paid down, so A's full 10,000 is outstanding
    assert kpis.total_outstanding == pytest.approx(30_000.0)


# -- structural (design AC 9) ------------------------------------------------


def test_service_does_not_fit_a_model() -> None:
    """ADR-009: KPIs read persisted scores; the request path never trains.

    An AST check, not a substring grep. s4.4 wrote this same shape of acceptance
    criterion as a grep and it flagged a docstring that described the rule.
    """
    tree = ast.parse(inspect.getsource(kpi_aggregate_service))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            imported.update(alias.name for alias in node.names)
            imported.add(node.module or "")
        elif isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)

    forbidden = {"ScoreScenario", "SklearnScorer", "FeatureExtractor", "ScoreAndPersistScenario"}
    assert not (forbidden & imported), f"KPI service must not fit a model: {forbidden & imported}"
