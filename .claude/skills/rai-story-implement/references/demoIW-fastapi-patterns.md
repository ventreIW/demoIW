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

---

## New Patterns from S5.4 Communications Generator

### 8. LLM Service with Prompt Templates (Config-Driven)

For services that call LLMs via `ILLMPort`, use a **prompt template file** in `prompts/<service>/` (mirrors `prompts/data_enrichment/` pattern):

```python
# app/application/services/communication_draft_service.py
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from app.config import settings
from app.domain.enums import Channel, Tone
from app.ports.llm_port import ILLMPort

if TYPE_CHECKING:
    from app.routers.cases import CaseDetailResponse

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class CaseDetail:
    """Minimal case detail for prompt building — decoupled from router response model."""
    client_name: str
    sector_description: str | None
    payment_history_pattern: str
    invoices: list[dict[str, str | int | float]]
    payments: list[dict[str, str | int | float]]
    score_value: float | None
    score_category: str | None
    communications: list[dict[str, str]]


class CommunicationDraftService:
    """Service for generating communication drafts via LLM."""

    def __init__(
        self,
        llm_port: ILLMPort,
        prompt_dir: Path | str,
        model: str | None = None,
    ) -> None:
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

    def _build_prompt(self, case_detail: CaseDetail, channel: Channel, tone: Tone) -> str:
        """Build prompt by filling all placeholders from case detail."""
        # Format invoices, payments, communications into strings
        invoice_lines = [
            f"- {inv['folio']}: {inv['amount']} "
            f"(due {inv['due_date']}, {inv['days_overdue']} days overdue, status: {inv['status']})"
            for inv in case_detail.invoices
        ]
        invoice_list = "\n".join(invoice_lines) if invoice_lines else "No outstanding invoices."
        # ... similarly for payments and communications

        return self._template.format(
            client_name=case_detail.client_name,
            sector_description=case_detail.sector_description or "N/A",
            payment_history_pattern=case_detail.payment_history_pattern,
            invoice_list=invoice_list,
            payment_history=payment_history,
            score_value=case_detail.score_value if case_detail.score_value is not None else "N/A",
            score_category=case_detail.score_category or "N/A",
            comms_log=comms_log,
            channel=channel.value,  # Enum .value is LOWERCASE ("email", "phone", "whatsapp")
            tone=tone.value,        # Enum .value is LOWERCASE ("formal", "firm", "urgent")
        )

    async def generate(self, case_detail: CaseDetail, channel: Channel, tone: Tone) -> str:
        prompt = self._build_prompt(case_detail, channel, tone)
        log.info("Generating communication draft", extra={"channel": channel.value, "tone": tone.value})
        return await self._llm.generate(prompt, model=self._model, max_tokens=512)


def case_detail_response_to_domain(response: "CaseDetailResponse") -> CaseDetail:
    """Convert router CaseDetailResponse to internal CaseDetail for prompt building."""
    return CaseDetail(
        client_name=response.client.name,
        sector_description=response.client.sector_description,
        payment_history_pattern=response.client.payment_history_pattern,
        invoices=[...],
        payments=[...],
        score_value=response.score.score_value if response.score else None,
        score_category=response.score.category if response.score else None,
        communications=[...],
    )
```

**Key rules:**
- **Prompt template in config, not code** — `prompts/communications/v1_draft.txt`
- **Model from settings** — `settings.MODEL_COMMUNICATIONS` (default), overrideable for tests
- **Channel/Tone enum values are lowercase** — `channel.value` → `"email"`, not `"EMAIL"`
- **Missing template → RuntimeError** during construction (fail fast)
- **Internal `CaseDetail` dataclass** — decouples service from router Pydantic models
- **Converter function** — `case_detail_response_to_domain` maps router → service types

### 9. Mocking ILLMPort for Unit Tests

Create a mock class implementing the `ILLMPort` protocol:

```python
# tests/unit/test_communication_draft_service.py
from app.ports.llm_port import ILLMPort

class MockLLMPort(ILLMPort):
    """Mock ILLMPort for testing."""
    def __init__(self) -> None:
        self.generate_calls: list[tuple[str, str, int]] = []

    async def generate(self, prompt: str, model: str, max_tokens: int = 512) -> str:
        self.generate_calls.append((prompt, model, max_tokens))
        return "Estimado cliente, le recordamos su saldo pendiente de $50,000."

    async def query(self, system_prompt: str, user_message: str, model: str) -> str:
        return "mock response"
```

**Usage in tests:**
```python
def test_generate_calls_llm_with_correct_params(mock_llm_port, prompt_dir, sample_case_detail):
    service = CommunicationDraftService(llm_port=mock_llm_port, prompt_dir=prompt_dir, model="test-model")
    result = await service.generate(sample_case_detail, Channel.PHONE, Tone.FIRM)
    
    prompt, model, max_tokens = mock_llm_port.generate_calls[0]
    assert model == "test-model"
    assert max_tokens == 512
    assert "phone" in prompt   # lowercase channel value
    assert "firm" in prompt    # lowercase tone value
```

**Key rules:**
- **Implement `ILLMPort`** — satisfies type checker (`mypy --strict`)
- **Track calls** — `generate_calls` list for assertion
- **Return realistic text** — Spanish draft for communications
- **Type annotate tuple** — `tuple[str, str, int]` for mypy strict

---

## New Patterns from S5.4 Refactoring (Shared Case Aggregate Service)

### 10. Shared Case Aggregate Service (Single Source of Truth)

When multiple consumers (router + use cases) need the same composed data, extract to a **shared service** in `app/application/services/`:

```python
# app/application/services/case_aggregate_service.py
from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.domain.entities.client import Client
from app.domain.entities.communication import Communication
from app.domain.entities.invoice import Invoice
from app.domain.entities.payment import Payment
from app.domain.entities.score import Score
from app.domain.exceptions import EntityNotFoundError
from app.ports.repositories import (
    IClientRepository,
    ICommunicationRepository,
    IInvoiceRepository,
    IPaymentRepository,
    IScenarioRepository,
    IScoreRepository,
)


@dataclass(frozen=True)
class CaseAggregate:
    """Raw case aggregate data for use by both router and use cases."""
    client: Client
    invoices: list[Invoice]          # sorted by due_date desc
    payments: list[Payment]          # sorted by payment_date desc
    communications: list[Communication]  # sorted by created_at desc
    score: Score | None


async def fetch_case_aggregate(
    scenario_id: UUID,
    client_id: UUID,
    scenario_repo: IScenarioRepository,
    client_repo: IClientRepository,
    invoice_repo: IInvoiceRepository,
    payment_repo: IPaymentRepository,
    score_repo: IScoreRepository,
    communication_repo: ICommunicationRepository,
) -> CaseAggregate:
    """Fetch and compose the full case aggregate for a client within a scenario.
    Raises EntityNotFoundError if scenario or client not found.
    """
    # Verify scenario exists
    scenario = await scenario_repo.get_by_id(scenario_id)
    if scenario is None:
        raise EntityNotFoundError("Scenario", str(scenario_id))

    # Fetch client
    client = await client_repo.get_by_id(client_id)
    if client is None:
        raise EntityNotFoundError("Client", str(client_id))

    # Invoices sorted by due_date desc
    invoices = await invoice_repo.get_by_client_id(client_id)
    invoices.sort(key=lambda inv: inv.due_date, reverse=True)

    # Payments sorted by payment_date desc
    payments = await payment_repo.get_by_client_id(client_id)
    payments.sort(key=lambda pmt: pmt.payment_date, reverse=True)

    # Communications sorted by created_at desc (explicit sort!)
    communications = await communication_repo.get_by_client_id(client_id)
    communications.sort(key=lambda c: c.created_at, reverse=True)

    # Score — filter from scenario scores
    scores = await score_repo.get_by_scenario(scenario_id)
    client_score = next((sc for sc in scores if sc.client_id == client_id), None)

    return CaseAggregate(
        client=client,
        invoices=invoices,
        payments=payments,
        communications=communications,
        score=client_score,
    )
```

**Router consumption** (catches domain exception → HTTPException):

```python
from app.application.services.case_aggregate_service import fetch_case_aggregate
from app.domain.exceptions import EntityNotFoundError

@router.get("/{scenario_id}/clients/{client_id}", response_model=CaseDetailResponse)
async def get_case_detail(...):
    try:
        aggregate = await fetch_case_aggregate(
            scenario_id=scenario_id, client_id=client_id,
            scenario_repo=scenario_repo, client_repo=client_repo,
            invoice_repo=invoice_repo, payment_repo=payment_repo,
            score_repo=score_repo, communication_repo=communication_repo,
        )
    except EntityNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    # Convert domain entities → response models
    client_profile = ClientProfileResponse(...)
    invoice_summaries = [_invoice_to_summary(inv) for inv in aggregate.invoices]
    # ...
    return CaseDetailResponse(...)
```

**Use case consumption** (lets exception propagate for tests to catch):

```python
from app.application.services.case_aggregate_service import fetch_case_aggregate

class GenerateCommunicationDraft:
    async def execute(self, request):
        aggregate = await fetch_case_aggregate(
            scenario_id=request.scenario_id, client_id=request.client_id,
            scenario_repo=self._scenario_repo, client_repo=self._client_repo,
            invoice_repo=self._invoice_repo, payment_repo=self._payment_repo,
            score_repo=self._score_repo, communication_repo=self._communication_repo,
        )
        # Build internal CaseDetail from aggregate for prompt...
```

**Key rules:**
- **Raw domain entities in aggregate** — no serialization; converter functions handle that per-consumer
- **Explicit sorting** — all lists sorted in service (due_date desc, payment_date desc, created_at desc)
- **Domain exception** — `EntityNotFoundError` raised by service; router converts to `HTTPException(404)`
- **Single source of truth** — eliminates duplicate fetch/sort logic between router and use cases
- **Testable** — unit tests verify repos called in correct order; integration tests verify 404s