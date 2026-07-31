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
    invoices: list[Invoice]  # sorted by due_date desc
    payments: list[Payment]  # sorted by payment_date desc
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

    Raises:
        EntityNotFoundError: If scenario or client not found.
    """
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
