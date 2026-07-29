from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.container import (
    get_client_repo,
    get_communication_repo,
    get_invoice_repo,
    get_payment_repo,
    get_scenario_repo,
    get_score_repo,
)
from app.domain.entities.client import Client
from app.domain.entities.communication import Communication
from app.domain.entities.invoice import Invoice
from app.domain.entities.payment import Payment
from app.domain.entities.score import Score
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
    # Verify scenario exists
    scenario = await scenario_repo.get_by_id(scenario_id)
    if scenario is None:
        raise HTTPException(status_code=404, detail="Scenario not found")

    # Fetch client and verify it belongs to this scenario
    client = await client_repo.get_by_id(client_id)
    if client is None:
        raise HTTPException(status_code=404, detail="Client not found")

    # Client profile
    client_profile = ClientProfileResponse(
        id=str(client.id),
        name=client.name,
        sector_description=client.sector_description,
        payment_history_pattern=client.payment_history_pattern.value
        if hasattr(client.payment_history_pattern, "value")
        else str(client.payment_history_pattern),
    )

    # Invoices sorted by due_date desc
    invoices = await invoice_repo.get_by_client_id(client_id)
    invoices.sort(key=lambda inv: inv.due_date, reverse=True)
    invoice_summaries = [_invoice_to_summary(inv) for inv in invoices]

    # Payments sorted by payment_date desc
    payments = await payment_repo.get_by_client_id(client_id)
    payments.sort(key=lambda pmt: pmt.payment_date, reverse=True)
    payment_summaries = [_payment_to_summary(pmt) for pmt in payments]

    # Communications sorted by created_at desc
    communications = await communication_repo.get_by_client_id(client_id)
    comm_summaries = [_communication_to_summary(comm) for comm in communications]

    # Score — filter from scenario scores
    scores = await score_repo.get_by_scenario(scenario_id)
    client_score = next((sc for sc in scores if sc.client_id == client_id), None)
    score_summary = _score_to_summary(client_score) if client_score else None

    return CaseDetailResponse(
        client=client_profile,
        score=score_summary,
        invoices=invoice_summaries,
        payments=payment_summaries,
        communications=comm_summaries,
    )