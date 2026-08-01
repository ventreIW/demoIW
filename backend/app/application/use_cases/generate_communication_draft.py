from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.application.services.case_aggregate_service import (
    fetch_case_aggregate,
)
from app.application.services.communication_draft_service import (
    CaseDetail,
    CommunicationDraftService,
)
from app.domain.entities.communication import Communication
from app.domain.enums import Channel, CommunicationStatus, Tone
from app.ports.repositories import (
    IClientRepository,
    ICommunicationRepository,
    IInvoiceRepository,
    IPaymentRepository,
    IScenarioRepository,
    IScoreRepository,
)


@dataclass(frozen=True)
class GenerateCommunicationDraftRequest:
    """Input for generating a communication draft."""

    scenario_id: UUID
    client_id: UUID
    channel: Channel
    tone: Tone


@dataclass(frozen=True)
class GenerateCommunicationDraftResponse:
    """Output from generating a communication draft."""

    communication: Communication


class GenerateCommunicationDraft:
    """Generate a communication draft and persist it."""

    def __init__(
        self,
        scenario_repo: IScenarioRepository,
        client_repo: IClientRepository,
        invoice_repo: IInvoiceRepository,
        payment_repo: IPaymentRepository,
        score_repo: IScoreRepository,
        communication_repo: ICommunicationRepository,
        draft_service: CommunicationDraftService,
    ) -> None:
        self._scenario_repo = scenario_repo
        self._client_repo = client_repo
        self._invoice_repo = invoice_repo
        self._payment_repo = payment_repo
        self._score_repo = score_repo
        self._communication_repo = communication_repo
        self._draft_service = draft_service

    async def execute(
        self,
        request: GenerateCommunicationDraftRequest,
    ) -> GenerateCommunicationDraftResponse:
        # Fetch case aggregate using shared service
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

        # Build case detail for prompt
        case_detail = CaseDetail(
            client_name=aggregate.client.name,
            sector_description=aggregate.client.sector_description,
            payment_history_pattern=aggregate.client.payment_history_pattern.value
            if hasattr(aggregate.client.payment_history_pattern, "value")
            else str(aggregate.client.payment_history_pattern),
            invoices=[
                {
                    "folio": inv.folio,
                    "amount": inv.amount,
                    "due_date": inv.due_date.isoformat(),
                    "days_overdue": inv.days_overdue,
                    "status": inv.status,
                }
                for inv in aggregate.invoices
            ],
            payments=[
                {
                    "amount": pmt.amount,
                    "payment_date": pmt.payment_date.isoformat(),
                    "method": pmt.method,
                }
                for pmt in aggregate.payments
            ],
            score_value=aggregate.score.score_value if aggregate.score else None,
            score_category=aggregate.score.category.value
            if aggregate.score and hasattr(aggregate.score.category, "value")
            else (aggregate.score.category if aggregate.score else None),
            communications=[
                {
                    "channel": c.channel.value
                    if hasattr(c.channel, "value")
                    else str(c.channel),
                    "tone": c.tone.value if hasattr(c.tone, "value") else str(c.tone),
                    "draft_text": c.draft_text,
                    "status": c.status.value
                    if hasattr(c.status, "value")
                    else str(c.status),
                    "created_at": c.created_at.isoformat(),
                }
                for c in aggregate.communications
            ],
        )

        # Generate draft via service
        draft_text = await self._draft_service.generate(
            case_detail,
            request.channel,
            request.tone,
        )

        # Persist Communication
        communication = Communication(
            id=uuid4(),
            client_id=request.client_id,
            scenario_id=request.scenario_id,
            channel=request.channel,
            tone=request.tone,
            draft_text=draft_text,
            status=CommunicationStatus.DRAFT,
            created_at=datetime.now(UTC),
        )
        await self._communication_repo.add(communication)

        return GenerateCommunicationDraftResponse(communication=communication)
