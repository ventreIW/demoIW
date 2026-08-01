# FastAPI Python Patterns for demoIW

## Overview

This document captures project-specific patterns for FastAPI development in demoIW, including dependency injection, error handling, and LLM integration patterns.

## Container Provider Ordering (PAT-N-4)

**CRITICAL**: When adding new providers to `app/container.py`, order matters — a provider must be defined BEFORE any other provider that depends on it via `Depends()`.

```python
# WRONG — get_record_contact_result_use_case uses get_contact_result_repo but it's defined after
async def get_record_contact_result_use_case(
    contact_result_repo: IContactResultRepository = Depends(get_contact_result_repo),
): ...

async def get_contact_result_repo(...): ...

# CORRECT — dependency defined first
async def get_contact_result_repo(...): ...

async def get_record_contact_result_use_case(
    contact_result_repo: IContactResultRepository = Depends(get_contact_result_repo),
): ...
```

**Why**: Python executes top-to-bottom; `Depends(get_contact_result_repo)` resolves at function definition time, so the target must already exist in the module namespace.

## Shared Case Aggregate Service (PAT-N-8)

Extract data-fetching logic to a shared service used by both routers and use cases. Single source of truth for composed data.

**Pattern**:
1. Create `app/application/services/case_aggregate_service.py` with:
   - `CaseAggregate` dataclass — raw domain entities
   - `fetch_case_aggregate()` — fetches & composes all data, raises `EntityNotFoundError`

2. Router (`GET /cases/{sid}/clients/{cid}`):
   ```python
   try:
       aggregate = await fetch_case_aggregate(...)
   except EntityNotFoundError as e:
       raise HTTPException(status_code=404, detail=str(e))
   ```

3. Use case (`POST /cases/{sid}/clients/{cid}/communications`):
   ```python
   aggregate = await fetch_case_aggregate(...)
   # Build prompt from aggregate, generate, persist
   ```

**Benefits**: Eliminates ~40 lines of duplicate logic, ensures consistency between router and use case.

## LLM Prompt as Config File (PAT-N-9)

Store prompts in `prompts/{domain}/v{N}_name.txt`, load at service init. Enables iteration without code changes.

**Structure**:
```
prompts/
  communications/
    v1_draft.txt
  data_enrichment/
    v1_company_description.txt
```

**Service pattern**:
```python
class CommunicationDraftService:
    def __init__(self, llm_port: ILLMPort, prompt_dir: Path, model: str | None = None):
        self._llm = llm_port
        self._prompt_dir = Path(prompt_dir)
        self._model = model or settings.MODEL_COMMUNICATIONS
        self._template = self._load_template()

    def _load_template(self) -> str:
        template_path = self._prompt_dir / "communications" / "v1_draft.txt"
        try:
            return template_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            raise RuntimeError(f"Prompt template not found at {template_path}")
```

## 500-After-Retries → 502 Pattern (PAT-N-10)

Catch `ExternalServiceError` in router and return 502. LLM adapter handles retries internally (MAX_RETRIES=3).

**Router**:
```python
from app.domain.exceptions import EntityNotFoundError, ExternalServiceError

@router.post(...)
async def generate_communication(...):
    try:
        response = await use_case.execute(...)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ExternalServiceError as e:
        raise HTTPException(status_code=502, detail=str(e))
    return _communication_to_summary(response.communication)
```

**Adapter** (`OpenRouterAdapter`):
- Retries 3 times on 5xx (500, 502, 503, 504)
- Exponential backoff: `await asyncio.sleep(2**attempt)`
- Catches: `httpx.HTTPStatusError`, `httpx.TimeoutException`
- Does NOT catch: `json.JSONDecodeError` (propagates as 500)

## Database-Unavailable Testing (PAT-N-4)

To test database-unavailable scenarios with FastAPI, inject a bad connection URL into the session factory (fails at query time) — NOT a raising dependency override (FastAPI catches DI exceptions as 500 before the route handler runs).

## Async SQLAlchemy CI Tests (PAT-N-5)

Use `sqlite+aiosqlite://` for async SQLAlchemy CI tests. Requires the `aiosqlite` pip package (not bundled with SQLAlchemy's asyncio extra). Enables real SQLAlchemy execute paths without PostgreSQL dependency in CI.

## Column Names in RawDataset

Column names in `RawDataset` must match ORM models (`id`, not `invoice_id`/`payment_id`).

## Mocking External HTTP with respx

Use `respx` to mock external HTTP (OpenRouter) in integration tests — mock at HTTP layer, not adapter. Follow existing pattern in `tests/unit/test_openrouter_adapter.py`.

Key principles:
- Mock at HTTP layer (`respx.post("https://openrouter.ai/...")`), not adapter method
- Use realistic response shapes matching provider's actual API
- Verify mock was called (`assert mock_route.called`)
- Test both success and failure paths

## Bug Detection Through Integration Tests

Integration tests with real persistence catch bugs that unit tests miss. Ensure test mock data matches the **actual producer's output** (procedural generator, external API), not what the consumer expects. When producer and consumer are owned by different developers/stories, this mismatch is a common source of bugs.

## Strict Adherence to Modification Scope

When a story explicitly restricts modifications to specific files, do not edit any other files. If a required dependency is not yet wired in the container, ask the user how it is currently provided elsewhere rather than assuming or creating new adapters/configuration modules/imports.

## WSL Cross-Filesystem Gate Slowness

When working on WSL with the project on `/mnt/c/`:
- `vitest`: 100-180s per scoped run — use `--no-coverage`
- `eslint`: may timeout entirely (>300s) — skip per-task, run at story close or CI
- `prettier`: may timeout entirely — skip per-task, run at story close or CI
- `tsc --noEmit`: use `node node_modules/typescript/bin/tsc --noEmit` (the `.bin/tsc` symlink breaks on cross-filesystem)

## Verifying Scope Claims

**Never trust scope.md completion markers alone**. Spot-check actual code with `search_files` before claiming a story/epic is done. The scope.md said s2.4 was complete but the backend endpoint didn't exist — Nano caught it. Verify scope claims against filesystem, not documents.

## FastAPI Router Pattern Replication

When adding new endpoints to an existing router, replicate the exact pattern of existing endpoints:
- Same import organization
- Same dependency injection style (`Depends(get_xxx)`)
- Same response model usage (`response_model=XxxSummary`)
- Same error handling (`HTTPException` with consistent detail format)
- Same docstring style (if any)

## Contract-First API Development

For stories that expose domain logic via HTTP:
1. Domain contract first — Value objects and use cases define the contract
2. Router as thin adapter — Router only validates query params, calls use case, serializes response
3. No business logic in router — All arithmetic/decision logic lives in domain/use case layer
4. Validation at the edge — Router validates query params (422 with clear messages) before any DB/scoring calls
5. Response models mirror domain exactly — Pydantic models match domain value objects field-for-field

## Pydantic v2 Patterns

Use Pydantic for all data structures. Validation at boundaries, serialization free.

```python
from pydantic import BaseModel

class CommunicationSummaryResponse(BaseModel):
    channel: str
    tone: str
    draft_text: str
    status: str
    created_at: str
```

## Type Everything

Type annotations on all code. Pyright strict is the standard.

```python
async def fetch_case_aggregate(
    scenario_id: UUID,
    client_id: UUID,
    scenario_repo: IScenarioRepository,
    client_repo: IClientRepository,
    ...
) -> CaseAggregate: ...
```

## TDD Always

RED-GREEN-REFACTOR, no exceptions. Tests are specification, not afterthought.

## Commit After Task

Commit after each completed task, not just story end. Enables recovery, shows progress.

## Full Skill Cycle

Use skills even for small stories. Structure helps; overhead is minimal.