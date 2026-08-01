from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.application.services.case_aggregate_service import (
    fetch_case_aggregate,
)
from app.application.use_cases.generate_communication_draft import (
    GenerateCommunicationDraft,
    GenerateCommunicationDraftRequest,
)
from app.application.use_cases.record_contact_result import (
    RecordContactResult,
    RecordContactResultRequest,
    RecordContactResultResponse,
)
from app.container import (
    get_client_repo,
    get_communication_repo,
    get_generate_communication_draft_use_case,
    get_invoice_repo,
    get_payment_repo,
    get_record_contact_result_use_case,
    get_scenario_repo,
    get_score_repo,
)
from app.domain.entities.communication import Communication
from app.domain.entities.invoice import Invoice
from app.domain.entities.payment import Payment
from app.domain.entities.score import Score
from app.domain.enums import Channel, Tone
from app.domain.exceptions import EntityNotFoundError, ExternalServiceError
from app.ports.repositories import (
    IClientRepository,
    ICommunicationRepository,
    IInvoiceRepository,
    IPaymentRepository,
    IScenarioRepository,
    IScoreRepository,
)

router = APIRouter(prefix="/api/v1/scenarios", tags=["cases"])


class ClientProfileResponse(BaseModel):
    """Client profile section of the case detail."""

    id: str
    name: str
    sector_description: str | None
    payment_history_pattern: str


class InvoiceSummaryResponse(BaseModel):
    """Invoice summary in case detail."""

    folio: str
    amount: float
    issue_date: str
    due_date: str
    days_overdue: int
    status: str


class PaymentSummaryResponse(BaseModel):
    """Payment summary in case detail."""

    amount: float
    payment_date: str
    method: str


class CommunicationSummaryResponse(BaseModel):
    """Communication summary in case detail."""

    channel: str
    tone: str
    draft_text: str
    status: str
    created_at: str


class ScoreSummaryResponse(BaseModel):
    """Score summary in case detail."""

    score_value: float
    category: str
    explanation: str


class GenerateCommunicationRequest(BaseModel):
    """Request model for generating a communication draft."""

    channel: Channel
    tone: Tone


class CaseDetailResponse(BaseModel):
    """Full case detail response — the case aggregate."""

    client: ClientProfileResponse
    score: ScoreSummaryResponse | None
    invoices: list[InvoiceSummaryResponse]
    payments: list[PaymentSummaryResponse]
    communications: list[CommunicationSummaryResponse]


def _invoice_to_summary(inv: Invoice) -> InvoiceSummaryResponse:
    return InvoiceSummaryResponse(
        folio=inv.folio,
        amount=inv.amount,
        issue_date=inv.issue_date.isoformat(),
        due_date=inv.due_date.isoformat(),
        days_overdue=inv.days_overdue,
        status=inv.status,
    )


def _payment_to_summary(pmt: Payment) -> PaymentSummaryResponse:
    return PaymentSummaryResponse(
        amount=pmt.amount,
        payment_date=pmt.payment_date.isoformat(),
        method=pmt.method,
    )


def _communication_to_summary(comm: Communication) -> CommunicationSummaryResponse:
    return CommunicationSummaryResponse(
        channel=comm.channel.value if hasattr(comm.channel, "value") else str(comm.channel),
        tone=comm.tone.value if hasattr(comm.tone, "value") else str(comm.tone),
        draft_text=comm.draft_text,
        status=comm.status.value if hasattr(comm.status, "value") else str(comm.status),
        created_at=comm.created_at.isoformat(),
    )


def _score_to_summary(sc: Score) -> ScoreSummaryResponse:
    return ScoreSummaryResponse(
        score_value=sc.score_value,
        category=sc.category.value if hasattr(sc.category, "value") else str(sc.category),
        explanation=sc.explanation,
    )


@router.get("/{scenario_id}/clients/{client_id}", response_model=CaseDetailResponse)
async def get_case_detail(
    scenario_id: UUID,
    client_id: UUID,
    scenario_repo: IScenarioRepository = Depends(get_scenario_repo),
    client_repo: IClientRepository = Depends(get_client_repo),
    invoice_repo: IInvoiceRepository = Depends(get_invoice_repo),
    payment_repo: IPaymentRepository = Depends(get_payment_repo),
    score_repo: IScoreRepository = Depends(get_score_repo),
    communication_repo: ICommunicationRepository = Depends(get_communication_repo),
) -> CaseDetailResponse:
    """Return full case detail for a client within a scenario.

    Composes client profile, invoices (sorted by due_date desc),
    payments (sorted by payment_date desc), communications (sorted by
    created_at desc), and the client's score (if one exists).
    """
    try:
        aggregate = await fetch_case_aggregate(
            scenario_id=scenario_id,
            client_id=client_id,
            scenario_repo=scenario_repo,
            client_repo=client_repo,
            invoice_repo=invoice_repo,
            payment_repo=payment_repo,
            score_repo=score_repo,
            communication_repo=communication_repo,
        )
    except EntityNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    # Client profile
    client_profile = ClientProfileResponse(
        id=str(aggregate.client.id),
        name=aggregate.client.name,
        sector_description=aggregate.client.sector_description,
        payment_history_pattern=aggregate.client.payment_history_pattern.value
        if hasattr(aggregate.client.payment_history_pattern, "value")
        else str(aggregate.client.payment_history_pattern),
    )

    # Convert to summary responses
    invoice_summaries = [_invoice_to_summary(inv) for inv in aggregate.invoices]
    payment_summaries = [_payment_to_summary(pmt) for pmt in aggregate.payments]
    comm_summaries = [_communication_to_summary(comm) for comm in aggregate.communications]
    score_summary = _score_to_summary(aggregate.score) if aggregate.score else None

    return CaseDetailResponse(
        client=client_profile,
        score=score_summary,
        invoices=invoice_summaries,
        payments=payment_summaries,
        communications=comm_summaries,
    )


@router.post(
    "/{scenario_id}/clients/{client_id}/contact-result",
    response_model=RecordContactResultResponse,
    status_code=201,
)
async def record_contact_result(
    scenario_id: UUID,
    client_id: UUID,
    body: RecordContactResultRequest,
    use_case: RecordContactResult = Depends(get_record_contact_result_use_case),
) -> RecordContactResultResponse:
    """Record a contact result and trigger rescore (s5.3).

    Persists the ContactResult, updates client status, and calls the
    E4 rescore endpoint to return an updated prioritized portfolio.
    """
    return await use_case.execute(
        RecordContactResultRequest(
            scenario_id=scenario_id,
            client_id=client_id,
            contact_result=body.contact_result,
            notes=body.notes,
        )
    )


@router.post(
    "/{scenario_id}/clients/{client_id}/communications",
    response_model=CommunicationSummaryResponse,
    status_code=201,
)
async def generate_communication(
    scenario_id: UUID,
    client_id: UUID,
    body: GenerateCommunicationRequest,
    use_case: GenerateCommunicationDraft = Depends(get_generate_communication_draft_use_case),
) -> CommunicationSummaryResponse:
    """Generate a communication draft for a client (s5.4).

    Returns the generated draft text with channel, tone, and DRAFT status.
    """
    try:
        response = await use_case.execute(
            GenerateCommunicationDraftRequest(
                scenario_id=scenario_id,
                client_id=client_id,
                channel=body.channel,
                tone=body.tone,
            )
        )
    except EntityNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ExternalServiceError as e:
        raise HTTPException(status_code=502, detail=str(e))
    return _communication_to_summary(response.communication)
