import csv
from datetime import UTC, datetime
from io import StringIO
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from pydantic import BaseModel

from app.application.use_cases.generate_dataset import GenerateDataset
from app.application.use_cases.prioritize_scenario import PrioritizeScenario
from app.application.use_cases.rescore_scenario import RescoreScenario
from app.application.use_cases.score_and_persist_scenario import ScoreAndPersistScenario
from app.application.use_cases.score_scenario import ScoreScenario
from app.config import settings
from app.container import (
    get_generate_dataset_use_case,
    get_rescore_scenario_use_case,
    get_scenario_repo,
    get_score_and_persist_use_case,
)
from app.domain.entities.scenario import Scenario
from app.domain.enums import ContactResultType, ScenarioStatus, ScoreCategory, Sector
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


class GeneratedScenarioResponse(ScenarioSummary):
    """Generate response. `enriched` is the ground-truth signal that the LLM
    actually enriched the data — False means the scenario carries raw Faker
    names (degraded run), so a dead AI subsystem is visible at the API (s4.8)."""

    enriched: bool


class ScoreRunResponse(BaseModel):
    """Result of scoring + persisting a scenario (s4.10)."""

    scenario_id: UUID
    scored_count: int
    unscored_count: int
    already_persisted: bool


class PrioritizedCaseResponse(BaseModel):
    """Response model matching PrioritizedCase domain object exactly."""

    client_id: str
    client_name: str
    score: float
    outstanding: float
    days_overdue: int
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


@router.post("/generate", response_model=GeneratedScenarioResponse, status_code=201)
async def generate_scenario(
    body: GenerationParams,
    use_case: GenerateDataset = Depends(get_generate_dataset_use_case),
    repo: IScenarioRepository = Depends(get_scenario_repo),
) -> GeneratedScenarioResponse:
    model = settings.MODEL_DATA_ENRICHMENT
    enriched = await use_case.execute(body, model)
    scenario = await repo.get_active()
    if scenario is None:
        raise HTTPException(status_code=500, detail="Failed to retrieve generated scenario")
    client_count = await repo.get_client_count(scenario.id)
    return GeneratedScenarioResponse(
        id=scenario.id,
        name=scenario.name,
        sector=scenario.sector,
        status=scenario.status.value,
        client_count=client_count,
        created_at=scenario.created_at,
        enriched=enriched,
    )


@router.post("/{scenario_id}/score", response_model=ScoreRunResponse, status_code=201)
async def score_and_persist_scenario(
    scenario_id: UUID,
    use_case: ScoreAndPersistScenario = Depends(get_score_and_persist_use_case),
) -> ScoreRunResponse:
    """Score a scenario and persist a Score for every scored client (s4.10).

    Idempotent: re-calling returns the already-persisted count without duplicating rows.
    """
    try:
        result = await use_case.execute(scenario_id)
    except EntityNotFoundError:
        raise HTTPException(status_code=404, detail=f"Scenario with id={scenario_id} not found")
    return ScoreRunResponse(
        scenario_id=scenario_id,
        scored_count=result.scored_count,
        unscored_count=result.unscored_count,
        already_persisted=result.already_persisted,
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
    - category: filter by high | medium | low (case-insensitive)
    - days_overdue_min: filter by minimum days overdue
    """
    # Validate query parameters
    valid_sort_fields = {"rank", "score", "outstanding", "expected_recoverable", "days_overdue"}
    if sort not in valid_sort_fields:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Invalid sort field: '{sort}'. "
                f"Must be one of: {', '.join(sorted(valid_sort_fields))}"
            ),
        )

    if order.lower() not in ("asc", "desc"):
        raise HTTPException(
            status_code=422,
            detail=f"Invalid order: '{order}'. Must be 'asc' or 'desc'",
        )

    # Derived from ScoreCategory rather than hardcoded. A literal set here duplicated
    # knowledge the enum already owns, and the two never agreed: the whitelist held
    # "High" while the enum (and the wire format, and the frontend type) hold "high",
    # so no input could both pass validation and match a case (BUG-02).
    resolved_category: ScoreCategory | None = None
    if category is not None:
        by_value = {member.value: member for member in ScoreCategory}
        resolved_category = by_value.get(category.lower())
        if resolved_category is None:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"Invalid category: '{category}'. "
                    f"Must be one of: {', '.join(sorted(by_value))}"
                ),
            )

    if threshold < 0.0 or threshold > 1.0:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid threshold: {threshold}. Must be between 0.0 and 1.0",
        )

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
    if resolved_category is not None:
        cases = [c for c in cases if ScoreCategory(c.category) is resolved_category]

    # Filter by days_overdue_min if provided
    if days_overdue_min is not None:
        cases = [c for c in cases if c.days_overdue >= days_overdue_min]

    # Sort
    sort_key_map = {
        "rank": lambda c: c.rank,
        "score": lambda c: c.score,
        "outstanding": lambda c: c.outstanding,
        "expected_recoverable": lambda c: c.expected_recoverable,
        "days_overdue": lambda c: c.days_overdue,
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
            client_name=c.client_name,
            score=c.score,
            outstanding=c.outstanding,
            days_overdue=c.days_overdue,
            rank=c.rank,
            expected_recoverable=c.expected_recoverable,
            category=c.category.value if hasattr(c.category, "value") else str(c.category),
        )
        for c in cases
    ]


class RescoreRequest(BaseModel):
    """Request model for rescore endpoint."""

    contact_result: ContactResultType


@router.post(
    "/{scenario_id}/clients/{client_id}/rescore",
    response_model=PrioritizedPortfolioResponse,
)
async def rescore_client(
    scenario_id: UUID,
    client_id: UUID,
    body: RescoreRequest,
    rescore_use_case: RescoreScenario = Depends(get_rescore_scenario_use_case),
    repo: IScenarioRepository = Depends(get_scenario_repo),
) -> PrioritizedPortfolioResponse:
    """Update a client's score based on contact result and return updated prioritization."""
    # Fetch scenario
    scenario = await repo.get_by_id(scenario_id)
    if scenario is None:
        raise HTTPException(status_code=404, detail=f"Scenario with id={scenario_id} not found")

    # Execute rescore
    try:
        portfolio = await rescore_use_case.execute(
            scenario_id=scenario_id,
            client_id=client_id,
            contact_result=body.contact_result,
            repo=repo,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    # Convert domain model to response model
    from app.routers.scenarios import _cases_to_response

    cases_resp = _cases_to_response(portfolio.cases)
    pareto_resp = _cases_to_response(portfolio.pareto_subset)

    return PrioritizedPortfolioResponse(
        cases=cases_resp,
        pareto_subset=pareto_resp,
        threshold=portfolio.threshold,
        total_expected_recoverable=portfolio.total_expected_recoverable,
        subset_expected_recoverable=portfolio.subset_expected_recoverable,
        portfolio_count=portfolio.portfolio_count,
        subset_count=len(portfolio.pareto_subset),
        value_share=portfolio.value_share,
        summary=portfolio.summary(),
    )
