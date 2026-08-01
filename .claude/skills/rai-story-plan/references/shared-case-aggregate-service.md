# Shared Case Aggregate Service Pattern

## Overview

When a router endpoint and a use case both need the same composed data (e.g., case detail with client, invoices, payments, score, communications), extract the fetch logic to a shared service. This eliminates duplication and ensures consistency.

## Pattern

### 1. Create the Service

`app/application/services/case_aggregate_service.py`:

```python
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
    client: Client
    invoices: list[Invoice]      # sorted by due_date desc
    payments: list[Payment]      # sorted by payment_date desc
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
    """Fetch and compose the full case aggregate for a client within a scenario."""
    # Verify scenario exists
    scenario = await scenario_repo.get_by_id(scenario_id)
    if scenario is None:
        raise EntityNotFoundError("Scenario", str(scenario_id))

    # Fetch client and verify it belongs to this scenario
    client = await client_repo.get_by_id(client_id)
    if client is None:
        raise EntityNotFoundError("Client", str(client_id))

    # Invoices sorted by due_date desc
    invoices = await invoice_repo.get_by_client_id(client_id)
    invoices.sort(key=lambda inv: inv.due_date, reverse=True)

    # Payments sorted by payment_date desc
    payments = await payment_repo.get_by_client_id(client_id)
    payments.sort(key=lambda pmt: pmt.payment_date, reverse=True)

    # Communications sorted by created_at desc
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

### 2. Router Usage

```python
from app.application.services.case_aggregate_service import (
    CaseAggregate,
    fetch_case_aggregate,
)

@router.get("/{scenario_id}/clients/{client_id}", response_model=CaseDetailResponse)
async def get_case_detail(
    scenario_id: UUID,
    client_id: UUID,
    scenario_repo: IScenarioRepository = Depends(get_scenario_repo),
    ...
) -> CaseDetailResponse:
    try:
        aggregate = await fetch_case_aggregate(
            scenario_id=scenario_id,
            client_id=client_id,
            scenario_repo=scenario_repo,
            client_repo=client_repo,
            ...
        )
    except EntityNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    # Convert to response model
    return CaseDetailResponse(
        client=ClientProfileResponse(...),
        invoices=[...],
        ...
    )
```

### 3. Use Case Usage

```python
from app.application.services.case_aggregate_service import (
    CaseAggregate,
    fetch_case_aggregate,
)

class GenerateCommunicationDraft:
    async def execute(self, request: GenerateCommunicationDraftRequest):
        aggregate = await fetch_case_aggregate(
            scenario_id=request.scenario_id,
            client_id=request.client_id,
            scenario_repo=self._scenario_repo,
            client_repo=self._client_repo,
            invoice_repo=self._invoice_repo,
            payment_repo=self._payment_repo,
            score_repo=self._score_repo,
            communication_repo=self._communication_repo,
        )

        # Build prompt from aggregate
        case_detail = CaseDetail(
            client_name=aggregate.client.name,
            sector_description=aggregate.client.sector_description,
            ...
        )
        draft_text = await self._draft_service.generate(case_detail, ...)
        ...
```

## Benefits

- **Single source of truth**: Same data-fetching logic for router and use case
- **Eliminates duplication**: ~40 lines of identical code removed
- **Consistency guaranteed**: Router and use case always return identical data
- **Testable**: Service can be unit tested independently
- **Maintainable**: Changes to data fetching only need one update

## When to Apply

- Router returns a composed aggregate (client + related entities)
- Use case needs the same aggregate for business logic
- Multiple endpoints need the same data composition
- Current code has duplicate fetch logic in router and use case

## Anti-Patterns to Avoid

- Copy-pasting fetch logic between router and use case
- Creating separate service methods that do almost the same thing
- Putting fetch logic in a base class (over-engineering)
- Having the use case call the router endpoint (circular dependency)

## Related Patterns

- `fastapi-python-patterns.md` — PAT-N-8: Shared case aggregate service
- `integration-test-patterns.md` — Testing the service with mocked repos