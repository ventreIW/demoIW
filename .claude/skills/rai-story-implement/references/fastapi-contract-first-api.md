# FastAPI Contract-First API Development Patterns

Based on s4.5-API (Prioritized List Endpoint) implementation.

## Core Principle

**Domain contract first, HTTP adapter second.**

The domain value objects and use cases define the contract. The router is a thin adapter that:
1. Validates query parameters (422 on invalid)
2. Calls the use case
3. Serializes the domain response to JSON

No business logic lives in the router.

## Pattern: Domain Contract → HTTP Adapter

### 1. Domain Contract (committed in prior story)

```python
# app/domain/value_objects/prioritized_case.py
@dataclass(frozen=True)
class PrioritizedCase:
    client_id: str
    score: float
    outstanding: float
    rank: int
    category: ScoreCategory  # Added in this story

    @property
    def expected_recoverable(self) -> float:
        return self.outstanding * self.score / 100.0

@dataclass(frozen=True)
class PrioritizedPortfolio:
    cases: list[PrioritizedCase]
    pareto_subset: list[PrioritizedCase]
    threshold: float = DEFAULT_PARETO_THRESHOLD

    @property
    def value_share(self) -> float:
        # ...
```

### 2. Pydantic Response Models (exact mirror of domain)

```python
# app/routers/scenarios.py
class PrioritizedCaseResponse(BaseModel):
    client_id: str
    score: float
    outstanding: float
    rank: int
    expected_recoverable: float
    category: str  # Enum value as string

class PrioritizedPortfolioResponse(BaseModel):
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

### 3. Router Endpoint (thin adapter)

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
    # 1. Validate query params at the edge
    if sort not in {"rank", "score", "outstanding", "expected_recoverable", "days_overdue"}:
        raise HTTPException(422, detail=f"Invalid sort: '{sort}'...")
    if order.lower() not in ("asc", "desc"):
        raise HTTPException(422, detail=f"Invalid order: '{order}'...")
    if category and category not in {"High", "Medium", "Low"}:
        raise HTTPException(422, detail=f"Invalid category: '{category}'...")
    if not 0.0 <= threshold <= 1.0:
        raise HTTPException(422, detail=f"Invalid threshold: {threshold}...")

    # 2. Fetch & score (re-score each call since s4.9 not done)
    scenario = await repo.get_by_id(scenario_id)
    scorer = ScoreScenario()
    dataset = await repo.get_raw_dataset(scenario_id)
    scoring_run = scorer.execute(dataset, scenario_id, seed=scenario.seed or 42)

    # 3. Prioritize
    prioritizer = PrioritizeScenario()
    portfolio = prioritizer.execute(scoring_run, threshold=threshold)

    # 4. Filter/sort on domain objects, then serialize
    cases = _apply_filters_and_sort(portfolio.cases, sort, order, category, days_overdue_min)
    pareto = _pareto_prefix(cases, portfolio.threshold)

    return PrioritizedPortfolioResponse(
        cases=[_to_response(c) for c in cases],
        pareto_subset=[_to_response(c) for c in pareto],
        threshold=portfolio.threshold,
        # ... all fields
    )
```

## Key Patterns

| Pattern | Why |
|---------|-----|
| Validation before DB/scoring | Fail fast, cheap 422 vs expensive 500 |
| Domain objects for filtering/sorting | Single source of truth for logic |
| Serialization at the end | Router stays thin, domain stays pure |
| Response models mirror domain exactly | Contract drift = test failure |

## Query Parameter Validation

Always validate at router level, not in use case:

```python
VALID_SORT_FIELDS = {"rank", "score", "outstanding", "expected_recoverable", "days_overdue"}
VALID_CATEGORIES = {"High", "Medium", "Low"}

if sort not in VALID_SORT_FIELDS:
    raise HTTPException(422, detail=f"Invalid sort: '{sort}'. Must be one of: {', '.join(sorted(VALID_SORT_FIELDS))}")
if order.lower() not in ("asc", "desc"):
    raise HTTPException(422, detail=f"Invalid order: '{order}'. Must be 'asc' or 'desc'")
if category and category not in VALID_CATEGORIES:
    raise HTTPException(422, detail=f"Invalid category: '{category}'. Must be one of: {', '.join(sorted(VALID_CATEGORIES))}")
if not 0.0 <= threshold <= 1.0:
    raise HTTPException(422, detail=f"Invalid threshold: {threshold}. Must be between 0.0 and 1.0")
```

## Testing Strategy

### Integration Tests (with mocked LLM)

```python
@pytest.mark.anyio
@respx.mock
async def test_happy_path(client: AsyncClient) -> None:
    _mock_openrouter()  # Reusable helper

    gen_resp = await client.post("/api/v1/scenarios/generate", json={...})
    sid = gen_resp.json()["id"]

    resp = await client.get(f"/api/v1/scenarios/{sid}/prioritized")
    assert resp.status_code == 200
    body = resp.json()

    # Contract shape
    assert "cases" in body
    assert "pareto_subset" in body
    assert body["value_share"] >= body["threshold"]

    # Domain fields present
    for case in body["cases"]:
        assert "client_id" in case
        assert "score" in case
        assert "outstanding" in case
        assert "rank" in case
        assert "expected_recoverable" in case
        assert "category" in case
```

### Validation Tests

```python
@pytest.mark.anyio
@respx.mock
async def test_invalid_sort_field_returns_422(client: AsyncClient) -> None:
    _mock_openrouter()
    # ... generate scenario ...
    resp = await client.get(f"/api/v1/scenarios/{sid}/prioritized?sort=invalid_field")
    assert resp.status_code == 422
    assert "invalid sort" in resp.json()["detail"].lower()

@pytest.mark.anyio
@respx.mock
async def test_invalid_category_value_returns_422(client: AsyncClient) -> None:
    # ...
    resp = await client.get(f"/api/v1/scenarios/{sid}/prioritized?category=InvalidCategory")
    assert resp.status_code == 422
```

## Contract Drift Prevention

Any change to domain value objects = contract change. Tests will fail on:
- Missing fields in response model
- Type mismatches
- Enum value changes

This is intentional — API consumers (frontend, E5) depend on exact shape.