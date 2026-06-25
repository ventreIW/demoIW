from datetime import UTC, datetime
from uuid import UUID

from app.adapters.persistence.models import (
    ClientORM,
    CommunicationORM,
    ContactResultORM,
    InvoiceORM,
    PaymentORM,
    ScenarioORM,
    ScoreORM,
)
from app.domain.entities.client import Client
from app.domain.entities.communication import Communication
from app.domain.entities.contact_result import ContactResult
from app.domain.entities.invoice import Invoice
from app.domain.entities.payment import Payment
from app.domain.entities.scenario import Scenario
from app.domain.entities.score import Score
from app.domain.enums import (
    Channel,
    CommunicationStatus,
    ContactResultType,
    PaymentPattern,
    ScenarioStatus,
    ScoreCategory,
    Sector,
    Tone,
)


def _utc(dt: datetime) -> datetime:
    """Attach UTC timezone to a naive datetime (SQLite strips tzinfo on storage)."""
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)


def scenario_orm_to_domain(orm: ScenarioORM) -> Scenario:
    return Scenario(
        id=UUID(orm.id),
        name=orm.name,
        sector=Sector(orm.sector),
        seed=orm.seed,
        parameters=orm.parameters,
        source=orm.source,
        status=ScenarioStatus(orm.status),
        created_at=_utc(orm.created_at),
    )


def scenario_domain_to_orm(domain: Scenario) -> ScenarioORM:
    return ScenarioORM(
        id=str(domain.id),
        name=domain.name,
        sector=domain.sector.value,
        seed=domain.seed,
        parameters=domain.parameters,
        source=domain.source,
        status=domain.status.value,
        created_at=domain.created_at,
    )


def client_orm_to_domain(orm: ClientORM) -> Client:
    return Client(
        id=UUID(orm.id),
        scenario_id=UUID(orm.scenario_id),
        name=orm.name,
        sector_description=orm.sector_description,
        payment_history_pattern=PaymentPattern(orm.payment_history_pattern),
    )


def client_domain_to_orm(domain: Client) -> ClientORM:
    return ClientORM(
        id=str(domain.id),
        scenario_id=str(domain.scenario_id),
        name=domain.name,
        sector_description=domain.sector_description,
        payment_history_pattern=domain.payment_history_pattern.value,
    )


def invoice_orm_to_domain(orm: InvoiceORM) -> Invoice:
    return Invoice(
        id=UUID(orm.id),
        client_id=UUID(orm.client_id),
        folio=orm.folio,
        amount=orm.amount,
        issue_date=_utc(orm.issue_date),
        due_date=_utc(orm.due_date),
        days_overdue=orm.days_overdue,
        status=orm.status,
    )


def invoice_domain_to_orm(domain: Invoice) -> InvoiceORM:
    return InvoiceORM(
        id=str(domain.id),
        client_id=str(domain.client_id),
        folio=domain.folio,
        amount=domain.amount,
        issue_date=domain.issue_date,
        due_date=domain.due_date,
        days_overdue=domain.days_overdue,
        status=domain.status,
    )


def payment_orm_to_domain(orm: PaymentORM) -> Payment:
    return Payment(
        id=UUID(orm.id),
        invoice_id=UUID(orm.invoice_id),
        amount=orm.amount,
        payment_date=_utc(orm.payment_date),
        method=orm.method,
    )


def payment_domain_to_orm(domain: Payment) -> PaymentORM:
    return PaymentORM(
        id=str(domain.id),
        invoice_id=str(domain.invoice_id),
        amount=domain.amount,
        payment_date=domain.payment_date,
        method=domain.method,
    )


def score_orm_to_domain(orm: ScoreORM) -> Score:
    return Score(
        id=UUID(orm.id),
        client_id=UUID(orm.client_id),
        scenario_id=UUID(orm.scenario_id),
        score_value=orm.score_value,
        category=ScoreCategory(orm.category),
        explanation=orm.explanation,
        scored_at=_utc(orm.scored_at),
    )


def score_domain_to_orm(domain: Score) -> ScoreORM:
    return ScoreORM(
        id=str(domain.id),
        client_id=str(domain.client_id),
        scenario_id=str(domain.scenario_id),
        score_value=domain.score_value,
        category=domain.category.value,
        explanation=domain.explanation,
        scored_at=domain.scored_at,
    )


def communication_orm_to_domain(orm: CommunicationORM) -> Communication:
    return Communication(
        id=UUID(orm.id),
        client_id=UUID(orm.client_id),
        scenario_id=UUID(orm.scenario_id),
        channel=Channel(orm.channel),
        tone=Tone(orm.tone),
        draft_text=orm.draft_text,
        status=CommunicationStatus(orm.status),
        created_at=_utc(orm.created_at),
    )


def communication_domain_to_orm(domain: Communication) -> CommunicationORM:
    return CommunicationORM(
        id=str(domain.id),
        client_id=str(domain.client_id),
        scenario_id=str(domain.scenario_id),
        channel=domain.channel.value,
        tone=domain.tone.value,
        draft_text=domain.draft_text,
        status=domain.status.value,
        created_at=domain.created_at,
    )


def contact_result_orm_to_domain(orm: ContactResultORM) -> ContactResult:
    return ContactResult(
        id=UUID(orm.id),
        client_id=UUID(orm.client_id),
        communication_id=UUID(orm.communication_id),
        result_type=ContactResultType(orm.result_type),
        notes=orm.notes,
        recorded_at=_utc(orm.recorded_at),
    )


def contact_result_domain_to_orm(domain: ContactResult) -> ContactResultORM:
    return ContactResultORM(
        id=str(domain.id),
        client_id=str(domain.client_id),
        communication_id=str(domain.communication_id),
        result_type=domain.result_type.value,
        notes=domain.notes,
        recorded_at=domain.recorded_at,
    )
