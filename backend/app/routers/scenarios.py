import csv
from datetime import UTC, datetime
from io import StringIO
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from pydantic import BaseModel

from app.container import get_scenario_repo
from app.domain.entities.scenario import Scenario
from app.domain.enums import ScenarioStatus, Sector
from app.domain.exceptions import EntityNotFoundError
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
