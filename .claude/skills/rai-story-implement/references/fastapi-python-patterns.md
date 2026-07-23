# FastAPI Python Patterns (demoIW)

## Pydantic v2 with FastAPI

```python
from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID
from datetime import datetime

class CreateScenarioRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    sector: Sector

class ScenarioSummary(BaseModel):
    id: UUID
    name: str
    sector: Sector
    status: str
    client_count: int
    created_at: datetime
```

## Dependency Injection with Container

```python
from fastapi import Depends
from app.container import get_scenario_repo
from app.ports.repositories import IScenarioRepository

async def get_scenario_repo(
    session: AsyncSession = Depends(get_session),
) -> IScenarioRepository:
    return SQLAlchemyScenarioRepository(session)

# In router:
@router.get("/{scenario_id}", response_model=ScenarioDetail)
async def get_scenario(
    scenario_id: UUID,
    repo: IScenarioRepository = Depends(get_scenario_repo),
) -> ScenarioDetail:
    ...
```

## Async SQLAlchemy with SQLite for Tests

```python
# conftest.py
TEST_DATABASE_URL = "sqlite+aiosqlite://"

async def override_get_session():
    async with test_session_maker() as session:
        yield session

app.dependency_overrides[get_session] = override_get_session
```

## Mocking External HTTP (OpenRouter) with respx

```python
import respx
import httpx
from app.container import get_llm_port

@respx.mock
async def test_generate_scenario(client: AsyncClient):
    respx.post("https://openrouter.ai/api/v1/chat/completions").mock(
        return_value=httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": "[{'name': 'Client 1', ...}]"}}],
                "usage": {"prompt_tokens": 100, "completion_tokens": 50},
            },
        )
    )
    # Test calls endpoint that uses LLM
```

## Error Handling Pattern

```python
from fastapi import HTTPException

@router.get("/{scenario_id}")
async def get_scenario(scenario_id: UUID, repo: IScenarioRepository = Depends(get_scenario_repo)):
    scenario = await repo.get_by_id(scenario_id)
    if scenario is None:
        raise HTTPException(status_code=404, detail=f"Scenario with id={scenario_id} not found")
    return ScenarioDetail(...)
```

## Filtering & Sorting Query Params

```python
@router.get("/prioritized")
async def get_prioritized(
    threshold: float = 0.80,
    sort: str = "rank",
    order: str = "asc",
    category: Optional[str] = None,
    days_overdue_min: Optional[int] = None,
    # Validate
    valid_sort = {"rank", "score", "outstanding", "expected_recoverable", "days_overdue"}
    if sort not in valid_sort:
        raise HTTPException(422, detail=f"Invalid sort: '{sort}'. Must be one of: {sorted(valid_sort)}")
    if order.lower() not in ("asc", "desc"):
        raise HTTPException(422, detail="order must be 'asc' or 'desc'")
    # Category validation
    if category is not None:
        valid_categories = {"High", "Medium", "Low"}
        if category not in valid_categories:
            raise HTTPException(422, detail=f"Invalid category: '{category}'. Must be one of: {sorted(valid_categories)}")
    # Threshold validation
    if threshold < 0.0 or threshold > 1.0:
        raise HTTPException(422, detail=f"Invalid threshold: {threshold}. Must be between 0.0 and 1.0")
    ...
```

## Category Filter & Pareto Re-computation

When filtering by category, recompute Pareto on the filtered set:

```python
if category:
    cases = [c for c in cases if c.category.value == category]
pareto_subset = _pareto_prefix(cases, portfolio.threshold)
```

## Category Value Serialization

Domain `ScoreCategory` is a StrEnum - serialize correctly:

```python
category = c.category.value if hasattr(c.category, "value") else str(c.category)
```

## Rescore Endpoint Pattern

For rescore endpoints that adjust a single client's score and re-rank:

```python
@router.post("/{scenario_id}/clients/{client_id}/rescore")
async def rescore_client(
    scenario_id: UUID,
    client_id: UUID,
    contact_result: ContactResultType,
    repo: IScenarioRepository = Depends(get_scenario_repo),
):
    # Fetch scenario and current scores
    scenario = await repo.get_by_id(scenario_id)
    scoring_run = ScoreScenario().execute(dataset, scenario_id, seed=scenario.seed or 42)
    
    # Adjust score for contacted client
    scores = {str(s.client_id): s.score_value for s in scoring_run.scores}
    scores[str(client_id)] = clamp(scores[str(client_id)] + DELTA[contact_result], 0, 100)
    
    # Re-rank via PrioritizeScenario
    portfolio = PrioritizeScenario().execute(scoring_run, threshold=0.80)
    # Return updated portfolio
```

## RawDataset Column Mapping (Critical)

| ORM Attribute | RawDataset Column |
|---------------|-------------------|
| `ClientORM.id` | `id` |
| `InvoiceORM.id` | `id` |
| `InvoiceORM.client_id` | `client_id` |
| `PaymentORM.id` | `id` |
| `PaymentORM.invoice_id` | `invoice_id` |
| `PaymentORM.payment_date` | `paid_date` |

**Wrong**: `invoice_id` in clients DataFrame, `payment_id` in payments DataFrame
**Right**: All ID columns use `id` as column name