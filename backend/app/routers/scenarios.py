import csv
from datetime import UTC, datetime
from io import StringIO
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from pydantic import BaseModel

from app.application.use_cases.generate_dataset import GenerateDataset
from app.application.use_cases.prioritize_scenario import PrioritizeScenario
from app.application.use_cases.score_scenario import ScoreScenario
from app.config import settings
from app.container import get_generate_dataset_use_case, get_scenario_repo
from app.domain.entities.scenario import Scenario
from app.domain.enums import ScenarioStatus, Sector
from app.domain.exceptions import EntityNotFoundError
from app.domain.value_objects.generation_params import GenerationParams
from app.domain.value_objects.prioritized_case import PrioritizedCase
from app.ports.repositories import IScenarioRepository

router = APIRouter(prefix="/api/v1/scenarios", tags=["scenarios"])


class CreateScenarioRequest(BaseModel):
    name: str
    sector: Sector


class ScenarioSummary(BaseModel):
    id: UUID
    name: str
    sector: Sector
    status: str
    client_count: int
    created_at: datetime


class ScenarioDetail(ScenarioSummary):
    seed: int | None
    parameters: dict[str, object]
    source: str


class PrioritizedCaseResponse(BaseModel):
    """Response model matching PrioritizedCase domain object exactly."""

    client_id: str
    score: float
    outstanding: float
    rank: int
    expected_recoverable: float
    category: str


class PrioritizedPortfolioResponse(BaseModel):
    """Response model matching PrioritizedPortfolio domain object exactly."""

    cases: list[PrioritizedCaseResponse]
    pareto_subset: list[PrioritizedCaseResponse]
    threshold: float
    total_expected_recoverable: float
    subset_expected_recoverable: float
    portfolio_count: int
    subset_count: int
    value_share: float
    summary: str


@router.get("", response_model=list[ScenarioSummary])
async def list_scenarios(
    repo: IScenarioRepository = Depends(get_scenario_repo),
) -> list[ScenarioSummary]:
    scenarios = await repo.list_all()
    result: list[ScenarioSummary] = []
    for s in scenarios:
        count = await repo.get_client_count(s.id)
        result.append(
            ScenarioSummary(
                id=s.id,
                name=s.name,
                sector=s.sector,
                status=s.status.value,
                client_count=count,
                created_at=s.created_at,
            )
        )
    return result


@router.post("", response_model=ScenarioSummary, status_code=201)
async def create_scenario(
    body: CreateScenarioRequest,
    repo: IScenarioRepository = Depends(get_scenario_repo),
) -> ScenarioSummary:
    domain = Scenario(
        id=uuid4(),
        name=body.name,
        sector=body.sector,
        seed=None,
        parameters={},
        source="manual",
        status=ScenarioStatus.INACTIVE,
        created_at=datetime.now(UTC),
    )
    saved = await repo.add(domain)
    return ScenarioSummary(
        id=saved.id,
        name=saved.name,
        sector=saved.sector,
        status=saved.status.value,
        client_count=0,
        created_at=saved.created_at,
    )


@router.get("/active", response_model=ScenarioDetail)
async def get_active(
    repo: IScenarioRepository = Depends(get_scenario_repo),
) -> ScenarioDetail:
    scenario = await repo.get_active()
    if scenario is None:
        raise HTTPException(
            status_code=404,
            detail="No active scenario found",
        )
    count = await repo.get_client_count(scenario.id)
    return ScenarioDetail(
        id=scenario.id,
        name=scenario.name,
        sector=scenario.sector,
        status=scenario.status.value,
        client_count=count,
        created_at=scenario.created_at,
        seed=scenario.seed,
        parameters=scenario.parameters,
        source=scenario.source,
    )


@router.get("/{scenario_id}", response_model=ScenarioDetail)
async def get_scenario(
    scenario_id: UUID,
    repo: IScenarioRepository = Depends(get_scenario_repo),
) -> ScenarioDetail:
    scenario = await repo.get_by_id(scenario_id)
    if scenario is None:
        raise HTTPException(
            status_code=404,
            detail=f"Scenario with id={scenario_id} not found",
        )
    count = await repo.get_client_count(scenario_id)
    return ScenarioDetail(
        id=scenario.id,
        name=scenario.name,
        sector=scenario.sector,
        status=scenario.status.value,
        client_count=count,
        created_at=scenario.created_at,
        seed=scenario.seed,
        parameters=scenario.parameters,
        source=scenario.source,
    )


@router.patch("/{scenario_id}/activate", response_model=ScenarioDetail)
async def activate_scenario(
    scenario_id: UUID,
    repo: IScenarioRepository = Depends(get_scenario_repo),
) -> ScenarioDetail:
    try:
        scenario = await repo.set_active(scenario_id)
    except EntityNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Scenario with id={scenario_id} not found",
        )
    count = await repo.get_client_count(scenario_id)
    return ScenarioDetail(
        id=scenario.id,
        name=scenario.name,
        sector=scenario.sector,
        status=scenario.status.value,
        client_count=count,
        created_at=scenario.created_at,
        seed=scenario.seed,
        parameters=scenario.parameters,
        source=scenario.source,
    )


REQUIRED_COLUMNS = {"client_name", "amount", "due_date", "invoice_id"}


@router.post("/upload-csv", response_model=ScenarioSummary, status_code=201)
async def upload_csv(
    file: UploadFile,
    repo: IScenarioRepository = Depends(get_scenario_repo),
) -> ScenarioSummary:
    """Create a scenario from a CSV file.

    Required columns: client_name, amount, due_date, invoice_id.
    """
    content = await file.read()

    if not content:
        raise HTTPException(
            status_code=422,
            detail=[{"msg": "Empty file"}],
        )

    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=422,
            detail=[{"msg": "File must be UTF-8 encoded"}],
        )

    try:
        reader = csv.DictReader(StringIO(text))
    except csv.Error:
        raise HTTPException(
            status_code=422,
            detail=[{"msg": "Could not parse CSV file"}],
        )

    if reader.fieldnames is None:
        raise HTTPException(
            status_code=422,
            detail=[{"msg": "Could not parse CSV headers"}],
        )

    actual_columns = set(reader.fieldnames)
    missing = REQUIRED_COLUMNS - actual_columns
    if missing:
        raise HTTPException(
            status_code=422,
            detail=[{"msg": f"Missing required columns: {', '.join(sorted(missing))}"}],
        )

    rows: list[dict[str, str]] = []
    try:
        rows = list(reader)
    except csv.Error as e:
        raise HTTPException(
            status_code=422,
            detail=[{"msg": f"CSV parse error: {e}"}],
        )

    if not rows:
        raise HTTPException(
            status_code=422,
            detail=[{"msg": "CSV file has no data rows"}],
        )

    # Derive scenario name from filename (without extension)
    name = file.filename.rsplit(".", 1)[0] if file.filename else "csv_import"

    domain = Scenario(
        id=uuid4(),
        name=name,
        sector=Sector.RETAIL,
        seed=None,
        parameters={},
        source="csv_upload",
        status=ScenarioStatus.INACTIVE,
        created_at=datetime.now(UTC),
    )

    saved = await repo.create_from_csv(domain, rows)
    count = await repo.get_client_count(saved.id)
    return ScenarioSummary(
        id=saved.id,
        name=saved.name,
        sector=saved.sector,
        status=saved.status.value,
        client_count=count,
        created_at=saved.created_at,
    )


@router.post("/generate", response_model=ScenarioSummary, status_code=201)
async def generate_scenario(
    body: GenerationParams,
    use_case: GenerateDataset = Depends(get_generate_dataset_use_case),
    repo: IScenarioRepository = Depends(get_scenario_repo),
) -> ScenarioSummary:
    model = settings.MODEL_DATA_ENRICHMENT
    await use_case.execute(body, model)
    scenario = await repo.get_active()
    if scenario is None:
        raise HTTPException(status_code=500, detail="Failed to retrieve generated scenario")
    client_count = await repo.get_client_count(scenario.id)
    return ScenarioSummary(
        id=scenario.id,
        name=scenario.name,
        sector=scenario.sector,
        status=scenario.status.value,
        client_count=client_count,
        created_at=scenario.created_at,
    )


@router.get("/{scenario_id}/prioritized", response_model=PrioritizedPortfolioResponse)
async def get_prioritized(
    scenario_id: UUID,
    threshold: float = 0.80,
    sort: str = "rank",
    order: str = "asc",
    category: str | None = None,
    days_overdue_min: int | None = None,
    repo: IScenarioRepository = Depends(get_scenario_repo),
) -> PrioritizedPortfolioResponse:
    """Return prioritized portfolio for a scenario with Pareto subset.

    Query params:
    - threshold: Pareto threshold (default 0.80)
    - sort: one of rank, score, outstanding, expected_recoverable, days_overdue
    - order: asc | desc
    - category: filter by High | Medium | Low
    - days_overdue_min: filter by minimum days overdue
    """
    # Fetch scenario
    scenario = await repo.get_by_id(scenario_id)
    if scenario is None:
        raise HTTPException(status_code=404, detail=f"Scenario with id={scenario_id} not found")

    # Score the scenario (re-score on each call since s4.9 not done yet)
    scorer = ScoreScenario()
    dataset = await repo.get_raw_dataset(scenario_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail="Scenario has no data to score")

    scoring_run = scorer.execute(dataset, scenario_id, seed=scenario.seed or 42)

    if not scoring_run.scores:
        raise HTTPException(status_code=404, detail="Scenario has no scored clients")

    # Prioritize
    prioritizer = PrioritizeScenario()
    portfolio = prioritizer.execute(scoring_run, threshold=threshold)

    cases = portfolio.cases

    # Filter by category if provided
    if category:

        def _cat_matches(c: "PrioritizedCase") -> bool:
            cat = c.category
            return (cat.value if hasattr(cat, "value") else str(cat)) == category

        cases = [c for c in cases if _cat_matches(c)]

    # Filter by days_overdue_min if provided (requires days_overdue on case)
    if days_overdue_min is not None:
        cases = [c for c in cases if getattr(c, "days_overdue", 0) >= days_overdue_min]

    # Sort
    sort_key_map = {
        "rank": lambda c: c.rank,
        "score": lambda c: c.score,
        "outstanding": lambda c: c.outstanding,
        "expected_recoverable": lambda c: c.expected_recoverable,
        "days_overdue": lambda c: getattr(c, "days_overdue", 0),
    }
    if sort in sort_key_map:
        reverse = order.lower() == "desc"
        cases.sort(key=sort_key_map[sort], reverse=reverse)

    # Recompute Pareto on filtered/sorted set
    from app.application.services.prioritizer import _pareto_prefix

    pareto_subset = _pareto_prefix(cases, portfolio.threshold)

    # Convert to response models
    cases_resp = _cases_to_response(cases)
    pareto_resp = _cases_to_response(pareto_subset)

    return PrioritizedPortfolioResponse(
        cases=cases_resp,
        pareto_subset=pareto_resp,
        threshold=portfolio.threshold,
        total_expected_recoverable=portfolio.total_expected_recoverable,
        subset_expected_recoverable=portfolio.subset_expected_recoverable,
        portfolio_count=portfolio.portfolio_count,
        subset_count=len(pareto_subset),
        value_share=portfolio.value_share,
        summary=portfolio.summary(),
    )


def _cases_to_response(cases: list["PrioritizedCase"]) -> list[PrioritizedCaseResponse]:
    """Convert domain PrioritizedCase list to response models."""
    return [
        PrioritizedCaseResponse(
            client_id=str(c.client_id),
            score=c.score,
            outstanding=c.outstanding,
            rank=c.rank,
            expected_recoverable=c.expected_recoverable,
            category=c.category.value if hasattr(c.category, "value") else str(c.category),
        )
        for c in cases
    ]
