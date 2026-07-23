# FastAPI Endpoint Patterns (demoIW)

## Adding a New Endpoint to an Existing Router

When adding `GET /api/v1/scenarios/{scenario_id}/prioritized` to `scenarios.py`:

1. **Import organization** — Group imports: stdlib, third-party, app modules
2. **Dependency injection** — Use `Depends(get_xxx)` for repo/use case providers from container
3. **Response model** — Define Pydantic models matching domain contract exactly
4. **Query parameter validation** — Validate early, return 422 with clear messages
5. **Error handling** — `HTTPException` with consistent detail format
6. **Docstring** — Document query params and response shape

```python
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
    # Validate query parameters first
    valid_sort_fields = {"rank", "score", "outstanding", "expected_recoverable", "days_overdue"}
    if sort not in valid_sort_fields:
        raise HTTPException(422, detail=f"Invalid sort: '{sort}'. Must be one of: {sorted(valid_sort_fields)}")
    # ... rest of validation
    # Fetch, process, return response model
```

## Pydantic Response Models Matching Domain Contract

```python
class PrioritizedCaseResponse(BaseModel):
    """Response model matching PrioritizedCase domain object exactly."""
    client_id: str
    score: float
    outstanding: float
    rank: int
    expected_recoverable: float
    category: str  # "High" | "Medium" | "Low"

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
```

## Column Name Mapping: ORM → RawDataset

The `RawDataset` expects specific column names. Map ORM attributes correctly:

| ORM Model | RawDataset Column |
|-----------|-------------------|
| `ClientORM.id` | `id` (not `client_id`) |
| `InvoiceORM.id` | `id` (not `invoice_id`) |
| `InvoiceORM.client_id` | `client_id` |
| `PaymentORM.id` | `id` (not `payment_id`) |
| `PaymentORM.invoice_id` | `invoice_id` |
| `PaymentORM.payment_date` | `paid_date` |

**Common error**: Using `invoice_id` in clients DataFrame or `payment_id` in payments DataFrame — these don't exist in RawDataset schema.

## WSL Python Cache Clearing

After adding new imports or changing function signatures in `app/` directories:

```bash
find . -path "*/app/*/__pycache__" -exec rm -rf {} + 2>/dev/null
# or targeted:
rm -rf app/routers/__pycache__ app/__pycache__
```

**Symptoms of stale cache**: `TypeError` referencing code that doesn't exist in current source (e.g., `Router.__init__() got unexpected keyword argument 'on_startup'`).

## Integration Tests with respx for OpenRouter

Mock at HTTP layer, not adapter:

```python
import respx
import httpx

@respx.mock
async def test_happy_path(client):
    mock_llm = [
        {"name": "Enriched Client 1", "sector_description": "A retail company in Mexico."},
        {"name": "Enriched Client 2", "sector_description": "A retail business operating in Mexico."},
    ]
    respx.post("https://openrouter.ai/api/v1/chat/completions").mock(
        return_value=httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": str(mock_llm).replace("'", '"')}}],
                "usage": {"prompt_tokens": 100, "completion_tokens": 50},
            },
        )
    )
    # Generate scenario then call endpoint
```

## Query Parameter Validation Pattern

Validate all query params upfront, return 422 with actionable messages:

```python
# Sort field validation
valid_sort = {"rank", "score", "outstanding", "expected_recoverable", "days_overdue"}
if sort not in valid_sort:
    raise HTTPException(422, detail=f"Invalid sort: '{sort}'. Must be one of: {sorted(valid_sort)}")

# Order validation
if order.lower() not in ("asc", "desc"):
    raise HTTPException(422, detail=f"Invalid order: '{order}'. Must be 'asc' or 'desc'")

# Category validation
valid_cats = {"High", "Medium", "Low"}
if category and category not in valid_cats:
    raise HTTPException(422, detail=f"Invalid category: '{category}'. Must be one of: {sorted(valid_cats)}")

# Range validation
if threshold < 0.0 or threshold > 1.0:
    raise HTTPException(422, detail=f"Invalid threshold: {threshold}. Must be between 0.0 and 1.0")
```

## Container Wiring for New Use Case

In `container.py`:

```python
from app.application.use_cases.prioritize_scenario import PrioritizeScenario

async def get_prioritize_scenario_use_case() -> PrioritizeScenario:
    """Dependency that provides a PrioritizeScenario use case instance."""
    return PrioritizeScenario()
```

Then inject in endpoint: `use_case: PrioritizeScenario = Depends(get_prioritize_scenario_use_case)`

## Orphaned Test Check (Jidoka)

After story complete, verify no tests importing changed modules were left untouched:

```bash
# From project root
git diff --name-only HEAD...$(git merge-base HEAD main) -- 'packages/*/src/' | \
  sed 's|.*/src/||; s|/[^/]*$||' | sort -u | while read mod; do
  mod_dotted=$(echo "$mod" | tr '/' '.')
  grep -rl "from $mod_dotted" packages/*/tests/ 2>/dev/null | while read tf; do
    if ! git diff --name-only HEAD...$(git merge-base HEAD main) -- "$tf" | grep -q .; then
      echo "BLOCKED: $tf imports $mod_dotted but was not touched"
    fi
  done
done
```

If orphans found: STOP. Read each, run it, fix or document why no change needed.