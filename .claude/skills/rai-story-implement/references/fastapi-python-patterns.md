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

## Container Provider Ordering (Critical)

When adding new providers to `app/container.py`, **order matters**: a provider must be defined BEFORE any other provider that depends on it via `Depends()`.

```python
# WRONG - get_record_contact_result_use_case uses get_contact_result_repo but it's defined after
async def get_record_contact_result_use_case(
    contact_result_repo: IContactResultRepository = Depends(get_contact_result_repo),
): ...

async def get_contact_result_repo(...): ...

# CORRECT - dependency defined first
async def get_contact_result_repo(...): ...

async def get_record_contact_result_use_case(
    contact_result_repo: IContactResultRepository = Depends(get_contact_result_repo),
): ...
```

**Pitfall**: Python executes top-to-bottom; `Depends(get_contact_result_repo)` resolves at function definition time, so the target must already exist in the module namespace.

## Nullable Foreign Key Pattern

When a relationship is optional (e.g., `ContactResult` may not have a `Communication` yet — s5.3 records contact, s5.4 links communication), apply at three layers:

### 1. ORM Model
```python
class ContactResultORM(Base):
    communication_id: Mapped[str | None] = mapped_column(
        ForeignKey("communications.id", ondelete="CASCADE"), nullable=True
    )
```

### 2. Mapper (both directions)
```python
def contact_result_orm_to_domain(orm: ContactResultORM) -> ContactResult:
    return ContactResult(
        ...
        communication_id=UUID(orm.communication_id) if orm.communication_id else None,
    )

def contact_result_domain_to_orm(domain: ContactResult) -> ContactResultORM:
    return ContactResultORM(
        ...
        communication_id=str(domain.communication_id) if domain.communication_id else None,
    )
```

### 3. Domain Entity
```python
class ContactResult(BaseModel):
    communication_id: UUID | None  # Optional for audit-only rows
```

## Test Fixture Pattern for FK Relationships

When testing repositories with FK constraints, create parent entities via raw SQL before exercising the child repository:

```python
@pytest.fixture
async def async_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)()
    yield session
    await session.close()
    await engine.dispose()

async def _create_scenario_and_client(async_session, scenario_id, client_id):
    await async_session.execute(
        insert(ScenarioORM).values({...})
    )
    await async_session.execute(
        insert(ClientORM).values({...})
    )
    await async_session.commit()

# In test:
scenario_id = uuid4()
client_id = uuid4()
await _create_scenario_and_client(async_session, scenario_id, client_id)

repo = SQLAlchemyContactResultRepository(async_session)
await repo.add(contact_result)  # FK satisfied
```

## FastAPI Enum Auto-Validation

Use the domain enum directly in Pydantic request models — FastAPI automatically validates and returns 422 for invalid values:

```python
from app.domain.enums import ContactResultType

class ContactResultRequest(BaseModel):
    contact_result: ContactResultType  # Auto-validates against enum values
    notes: str | None = None

@router.post("/contact-result")
async def record_contact(body: ContactResultRequest):
    # body.contact_result is already a ContactResultType member
    # Invalid values → 422 before handler runs
```

**No custom validator needed** — `StrEnum` + Pydantic v2 handles it.

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


## LLM Service Implementation Patterns (s3.2, s5.4)

### 1. Config-Driven Prompt Templates

Store prompts as `.txt` files in `prompts/<feature>/v1_<name>.txt` — not in code:

```
prompts/
├── data_enrichment/
│   └── v1_company_description.txt
└── communications/
    └── v1_draft.txt
```

Template uses Python `str.format()` placeholders: `{client_name}`, `{invoice_list}`, etc.

### 2. LLM Service Structure

```python
# app/application/services/communication_draft_service.py
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from app.config import settings
from app.domain.enums import Channel, Tone
from app.ports.llm_port import ILLMPort

if TYPE_CHECKING:
    from app.routers.cases import CaseDetailResponse

@dataclass(frozen=True)
class CaseDetail:
    """Internal domain model for prompt building — decoupled from router response."""
    client_name: str
    sector_description: str | None
    payment_history_pattern: str
    invoices: list[dict[str, str | int | float]]
    payments: list[dict[str, str | int | float]]
    score_value: float | None
    score_category: str | None
    communications: list[dict[str, str]]

class CommunicationDraftService:
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
        # Format all placeholders from case_detail
        invoice_list = "\n".join(
            f"- {inv['folio']}: {inv['amount']} "
            f"(due {inv['due_date']}, {inv['days_overdue']} days overdue, status: {inv['status']})"
            for inv in case_detail.invoices
        ) or "No outstanding invoices."
        # ... similar for payments, communications
        
        return self._template.format(
            client_name=case_detail.client_name,
            sector_description=case_detail.sector_description or "N/A",
            payment_history_pattern=case_detail.payment_history_pattern,
            invoice_list=invoice_list,
            # ... all placeholders
            channel=channel.value,
            tone=tone.value,
        )

    async def generate(self, case_detail: CaseDetail, channel: Channel, tone: Tone) -> str:
        prompt = self._build_prompt(case_detail, channel, tone)
        return await self._llm.generate(prompt, model=self._model, max_tokens=512)

def case_detail_response_to_domain(response: CaseDetailResponse) -> CaseDetail:
    """Convert router response to internal domain model."""
    return CaseDetail(
        client_name=response.client.name,
        sector_description=response.client.sector_description,
        payment_history_pattern=response.client.payment_history_pattern,
        invoices=[{"folio": inv.folio, "amount": inv.amount, ...} for inv in response.invoices],
        payments=[{"amount": pmt.amount, "payment_date": pmt.payment_date, ...} for pmt in response.payments],
        score_value=response.score.score_value if response.score else None,
        score_category=response.score.category if response.score else None,
        communications=[{"channel": c.channel, "tone": c.tone, ...} for c in response.communications],
    )
```

Key principles:
- **Internal `CaseDetail`** is a frozen dataclass with simple types (no Pydantic, no enums) — pure data for prompt formatting
- **Router response → internal domain** via converter function (keeps service independent of API layer)
- **Template loading** at init time with clear error if missing
- **Model from config** (`settings.MODEL_COMMUNICATIONS`) with optional override
- **Max tokens** tuned per use case (512 for drafts, 1024 for queries)

### 3. Container Wiring for LLM Services

```python
# app/container.py
from app.application.services.communication_draft_service import CommunicationDraftService
from app.ports.llm_port import ILLMPort
from app.config import settings
from pathlib import Path

async def get_draft_service(
    llm_port: ILLMPort = Depends(get_llm_port),
) -> CommunicationDraftService:
    prompt_dir = Path(__file__).resolve().parents[2] / "prompts"
    return CommunicationDraftService(
        llm_port=llm_port,
        prompt_dir=prompt_dir,
        model=settings.MODEL_COMMUNICATIONS,
    )
```

### 4. Type Annotations for Mixed-Value Dicts

When dicts contain mixed value types (str, int, float), use explicit union:

```python
# Correct
invoices: list[dict[str, str | int | float]]
payments: list[dict[str, str | int | float]]
communications: list[dict[str, str]]  # all string values

# WRONG - bare dict loses type info
invoices: list[dict]
```

### 5. Long f-string Formatting (ruff E501)

Split long f-strings across implicit concatenation:

```python
# Instead of one long line:
f"- {inv['folio']}: {inv['amount']} (due {inv['due_date']}, {inv['days_overdue']} days overdue, status: {inv['status']})"

# Split:
f"- {inv['folio']}: {inv['amount']} "
f"(due {inv['due_date']}, {inv['days_overdue']} days overdue, status: {inv['status']})"
```

### 6. Integration Test with respx Mock

```python
# tests/integration/test_communications_integration.py
import respx
import httpx

@respx.mock
async def test_generate_communication_integration(client: AsyncClient):
    # Mock OpenRouter
    mock_route = respx.post("https://openrouter.ai/api/v1/chat/completions").mock(
        return_value=httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": "Estimado cliente, le recordamos su saldo..."}}],
                "usage": {"prompt_tokens": 200, "completion_tokens": 100},
            },
        )
    )
    
    response = await client.post(
        f"/api/v1/scenarios/{sid}/clients/{cid}/communications",
        json={"channel": "email", "tone": "formal"},
    )
    
    assert response.status_code == 201
    assert "Estimado cliente" in response.json()["draft_text"]
    assert mock_route.called
```

### 7. Integration Test with Sequential Mock Responses (side_effect)

When the endpoint makes multiple OpenRouter calls (e.g., enrichment + communication), use `side_effect` to sequence responses:

```python
# tests/integration/test_communications_integration.py
@respx.mock
async def test_generate_communication_integration_persists_draft(client: AsyncClient):
    # Mock ALL OpenRouter calls: 3 enrichment batches + 1 communication call
    mock_route = respx.post("https://openrouter.ai/api/v1/chat/completions").mock(
        side_effect=[
            _enrichment_mock_response(20),
            _enrichment_mock_response(20),
            _enrichment_mock_response(20),
            _llm_mock_response("Estimado cliente, le recordamos su pago..."),
        ]
    )

    response = await client.post(
        f"/api/v1/scenarios/{sid}/clients/{cid}/communications",
        json={"channel": "email", "tone": "formal"},
    )

    assert response.status_code == 201
    assert mock_route.call_count == 4  # 3 enrichment + 1 communication

def _llm_mock_response(content: str) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "choices": [{"message": {"content": content}}],
            "usage": {"prompt_tokens": 50, "completion_tokens": 20},
        },
    )

def _enrichment_mock_response(count: int) -> httpx.Response:
    import json
    enriched = [
        {"name": f"Cliente {i}", "sector_description": "Empresa retail."}
        for i in range(count)
    ]
    return httpx.Response(
        200,
        json={"choices": [{"message": {"content": json.dumps(enriched)}}]},
    )
```

**Note**: OpenRouterAdapter retries 3 times on 5xx/timeout (MAX_RETRIES=3). For failure tests, provide 4 responses (1 initial + 3 retries):

```python
# 500 error test - 4 failures (1 initial + 3 retries)
respx.post("https://openrouter.ai/api/v1/chat/completions").mock(
    side_effect=[
        _enrichment_mock_response(20),  # enrichment
        _enrichment_mock_response(20),
        _enrichment_mock_response(20),
        httpx.Response(500),  # attempt 1
        httpx.Response(500),  # retry 1
        httpx.Response(500),  # retry 2
        httpx.Response(500),  # retry 3
    ]
)
```

### 8. Shared Service Extraction Pattern (Router + Use Case)

When both a router endpoint and a use case need the same data-fetching logic, extract to a shared service:

```python
# app/application/services/case_aggregate_service.py
from dataclasses import dataclass
from uuid import UUID

from app.domain.entities.client import Client
from app.domain.entities.communication import Communication
from app.domain.entities.invoice import Invoice
from app.domain.entities.payment import Payment
from app.domain.entities.score import Score
from app.domain.exceptions import EntityNotFoundError
from app.ports.repositories import (
    IClientRepository, ICommunicationRepository, IInvoiceRepository,
    IPaymentRepository, IScenarioRepository, IScoreRepository,
)

@dataclass(frozen=True)
class CaseAggregate:
    client: Client
    invoices: list[Invoice]        # sorted by due_date desc
    payments: list[Payment]        # sorted by payment_date desc
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
    # Verify scenario exists
    scenario = await scenario_repo.get_by_id(scenario_id)
    if scenario is None:
        raise EntityNotFoundError("Scenario", str(scenario_id))

    client = await client_repo.get_by_id(client_id)
    if client is None:
        raise EntityNotFoundError("Client", str(client_id))

    invoices = await invoice_repo.get_by_client_id(client_id)
    invoices.sort(key=lambda inv: inv.due_date, reverse=True)

    payments = await payment_repo.get_by_client_id(client_id)
    payments.sort(key=lambda pmt: pmt.payment_date, reverse=True)

    communications = await communication_repo.get_by_client_id(client_id)
    communications.sort(key=lambda c: c.created_at, reverse=True)

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

**Router usage** (converts to HTTPException):
```python
# app/routers/cases.py
from app.application.services.case_aggregate_service import fetch_case_aggregate
from app.domain.exceptions import EntityNotFoundError

@router.get("/{scenario_id}/clients/{client_id}")
async def get_case_detail(...):
    try:
        aggregate = await fetch_case_aggregate(...)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    # Convert to response model...
```

**Use case usage** (lets EntityNotFoundError propagate):
```python
# app/application/use_cases/generate_communication_draft.py
from app.application.services.case_aggregate_service import fetch_case_aggregate

class GenerateCommunicationDraft:
    async def execute(self, request):
        aggregate = await fetch_case_aggregate(
            scenario_id=request.scenario_id,
            client_id=request.client_id,
            scenario_repo=self._scenario_repo,
            client_repo=self._client_repo,
            # ... pass all repos
        )
        # Build CaseDetail for prompt from aggregate
```

### 9. ExternalServiceError Handling in Router

Convert LLM adapter errors to 502 Bad Gateway:

```python
# app/routers/cases.py
from app.domain.exceptions import EntityNotFoundError, ExternalServiceError

@router.post("/{scenario_id}/clients/{client_id}/communications")
async def generate_communication(...):
    try:
        response = await use_case.execute(...)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ExternalServiceError as e:
        raise HTTPException(status_code=502, detail=str(e))
    return _communication_to_summary(response.communication)
```

**Why 502?**: Upstream service (OpenRouter) failed — this is a bad gateway, not a client error.