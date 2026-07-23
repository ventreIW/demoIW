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
    # Validate
    valid_sort = {"rank", "score", "outstanding", "expected_recoverable", "days_overdue"}
    if sort not in valid_sort:
        raise HTTPException(422, detail=f"Invalid sort: '{sort}'. Must be one of: {sorted(valid_sort)}")
    if order.lower() not in ("asc", "desc"):
        raise HTTPException(422, detail="order must be 'asc' or 'desc'")
    ...
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