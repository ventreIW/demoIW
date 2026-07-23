# demoIW Project FastAPI/Python Patterns

Session-specific patterns observed in the demoIW backend (RaiSE, Python 3.12, FastAPI, SQLAlchemy 2.0, Pydantic v2, uv, ruff, mypy).

## RaiSE CLI

- Project `rai` is a minimal stub — use `uvx --from raise-cli rai <cmd>` for full CLI
- Commands missing from local `rai`: `db`, `mission`, `gate`, `session journal`
- `rai gate check` may not exist — fall back to direct tooling

## Test Infrastructure

- SQLite in-memory: `sqlite+aiosqlite://` (requires `aiosqlite` package)
- Fixture: `client` in `tests/conftest.py` creates test engine, overrides `get_session`
- Fixture: `client_unavailable` uses bad DB URL for DB-down tests
- Pattern: `@pytest.mark.anyio` for async tests with `httpx.AsyncClient`

## Router Patterns (`backend/app/routers/scenarios.py`)

```python
# Imports grouped: stdlib, third-party, local
from fastapi import APIRouter, Depends, HTTPException, UploadFile
from pydantic import BaseModel

# Local imports with full module path
from app.application.use_cases.generate_dataset import GenerateDataset
from app.container import get_generate_dataset_use_case, get_scenario_repo

router = APIRouter(prefix="/api/v1/scenarios", tags=["scenarios"])

# Request/response models as Pydantic BaseModel classes
class CreateScenarioRequest(BaseModel):
    name: str
    sector: Sector

class ScenarioSummary(BaseModel):
    id: UUID
    name: str
    ...

# Endpoint with dependency injection
@router.get("", response_model=list[ScenarioSummary])
async def list_scenarios(repo: IScenarioRepository = Depends(get_scenario_repo)):
    ...

# POST with status_code
@router.post("", response_model=ScenarioSummary, status_code=201)
async def create_scenario(body: CreateScenarioRequest, repo: IScenarioRepository = Depends(get_scenario_repo)):
    ...

# Error handling
raise HTTPException(status_code=404, detail=f"Scenario with id={scenario_id} not found")
```

## Repository Pattern

- Abstract port in `app/ports/repositories.py` (ABC with `@abstractmethod`)
- SQLAlchemy impl in `app/adapters/persistence/sqlalchemy_*_repo.py`
- Container wires impl in `app/container.py` via `Depends(get_xxx_repo)`

## Domain Value Objects

- Use `@dataclass(frozen=True)` for immutable DTOs
- Computed properties for derived values (`expected_recoverable`)
- Type hints with `Final` for constants

## Database Access

- Async SQLAlchemy 2.0: `AsyncSession`, `select()`, `scalar_one_or_none()`
- Models in `app/adapters/persistence/models.py` (Mapped classes)
- Mappers in `app/adapters/persistence/mappers.py` (domain ⇄ ORM)

## Cache Clearing After Import/Signature Changes

After editing Python files that change imports or function/class signatures, stale `.pyc` files can cause confusing errors (e.g., `TypeError` referencing old signatures):

```bash
find backend -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null
find backend -name "*.pyc" -delete 2>/dev/null
```

## Code Quality Gates

```bash
cd backend
uv run pytest tests/test_prioritized_endpoint.py -v           # tests
uv run ruff check app/routers/scenarios.py                     # lint
uv run ruff format --check app/routers/scenarios.py            # format
uv run mypy app/routers/scenarios.py                           # types
```

## Branch Naming

Format: `story/s{N}.{M}/{slug}` — always with `story/` prefix
Example: `story/s4.5/prioritized-list-endpoint`

---

## New Patterns from s4.5-API Implementation

### 1. Container Wiring for New Use Cases

When adding a new use case to the FastAPI dependency injection system, add a provider function to `app/container.py` following the **exact existing pattern**:

```python
# Import the use case
from app.application.use_cases.prioritize_scenario import PrioritizeScenario

# Provider function — mirrors existing get_xxx_use_case pattern
async def get_prioritize_scenario_use_case() -> PrioritizeScenario:
    """Dependency that provides a PrioritizeScenario use case instance."""
    return PrioritizeScenario()
```

Key rules:
- Match signature style: `async def get_<name>() -> Type:`
- Same docstring format: `"""Dependency that provides a <Name> instance."""`
- No extra dependencies if the use case has no constructor args (like `PrioritizeScenario`)
- If use case needs deps, follow `get_generate_dataset_use_case` pattern with `Depends()` params

### 2. Repository Interface Extension

When an endpoint needs data not exposed by the current repository interface:

**Step 1:** Add abstract method to the port in `app/ports/repositories.py`:
```python
@abstractmethod
async def get_raw_dataset(self, scenario_id: UUID) -> RawDataset | None:
    """Return raw clients, invoices, and payments as DataFrames for scoring."""
    ...
```

**Step 2:** Implement in SQLAlchemy adapter (`app/adapters/persistence/sqlalchemy_scenario_repo.py`):
```python
async def get_raw_dataset(self, scenario_id: UUID) -> RawDataset | None:
    import pandas as pd
    from sqlalchemy import select
    
    # Fetch clients, then invoices via client_ids, then payments via invoice_ids
    # Return RawDataset(clients=clients_df, invoices=invoices_df, payments=payments_df)
```

**Step 3:** Use in endpoint via existing `Depends(get_scenario_repo)` — no container changes needed.

### 3. Value Object Modification for API Contracts

When a domain value object needs a new field for API serialization:

**Step 1:** Add field to frozen dataclass in `app/domain/value_objects/xxx.py`:
```python
@dataclass(frozen=True)
class PrioritizedCase:
    client_id: str
    score: float
    outstanding: float
    rank: int
    category: ScoreCategory  # NEW field
```

**Step 2:** Update all creators of this object (e.g., `prioritizer.py`):
```python
PrioritizedCase(
    client_id=client_id,
    score=scores[client_id],
    outstanding=outstanding_by_client[client_id],
    rank=position,
    category=categorize(score),  # compute from score
)
```

**Step 3:** Response serialization automatically includes new field.

### 4. FastAPI Type Annotations

- **Return type**: Use `dict[str, object]` not bare `dict` (mypy strict)
- **Helper functions**: Use forward references for circular imports:
  ```python
  def _portfolio_to_dict(
      portfolio: "PrioritizedPortfolio",  # forward ref
      ...
  ) -> dict[str, object]:
  ```
- **Query params**: Use `str | None = None` for optional params, FastAPI handles conversion

### 5. TDD Test Pattern for New Endpoints

```python
# tests/test_prioritized_endpoint.py
class TestPrioritizedEndpoint:
    @pytest.mark.anyio
    async def test_404_unscored_scenario(self, client) -> None:
        # RED: test fails before endpoint exists
        create_resp = await client.post("/api/v1/scenarios", json={"name": "X", "sector": "retail"})
        sid = create_resp.json()["id"]
        response = await client.get(f"/api/v1/scenarios/{sid}/prioritized")
        assert response.status_code == 404
        assert "no data" in response.json()["detail"].lower()
```

- Tests in `tests/` (not `tests/integration/` or `tests/unit/` for API tests)
- `@pytest.mark.anyio` for async
- Use `client` fixture from `conftest.py`

### 6. Re-scoring on Each Request (Temporary)

Since score persistence (s4.9) isn't done yet, the endpoint re-scores the scenario on every call:

```python
# In endpoint:
scorer = ScoreScenario()
dataset = await repo.get_raw_dataset(scenario_id)
scoring_run = scorer.execute(dataset, scenario_id, seed=scenario.seed or 42)
portfolio = prioritizer.execute(scoring_run, threshold=threshold)
```

This is acceptable for demo; s4.9 will persist scores and the endpoint will fetch instead of re-compute.

### 7. Sorting/Filtering Pareto Subset Correctly

The Pareto subset must be recomputed **after** sorting/filtering the full portfolio:

```python
# Filter first (category, days_overdue)
cases = [c for c in portfolio.cases if c.category == category]

# Sort full list
cases.sort(key=sort_key_map[sort], reverse=order == "desc")

# Then recompute Pareto on filtered/sorted list
pareto_subset = _pareto_prefix(cases, threshold)
```

This ensures the "smallest prefix reaching threshold" invariant holds on the view the user sees.