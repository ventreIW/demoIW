from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.adapters.persistence.mappers import (
    client_domain_to_orm,
    client_orm_to_domain,
    communication_orm_to_domain,
    contact_result_domain_to_orm,
    contact_result_orm_to_domain,
    invoice_domain_to_orm,
    invoice_orm_to_domain,
    payment_orm_to_domain,
    scenario_domain_to_orm,
    scenario_orm_to_domain,
    score_orm_to_domain,
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


@pytest.mark.asyncio
async def test_scenario_round_trip(db_session):  # type: ignore[no-untyped-def]
    domain = Scenario(
        id=uuid4(),
        name="Manufactura — Demo",
        sector=Sector.MANUFACTURING,
        seed=None,
        parameters={},
        source="generated",
        status=ScenarioStatus.INACTIVE,
        created_at=datetime.now(UTC),
    )
    orm = scenario_domain_to_orm(domain)
    db_session.add(orm)
    await db_session.commit()
    await db_session.refresh(orm)
    recovered = scenario_orm_to_domain(orm)
    assert recovered == domain


@pytest.mark.asyncio
async def test_client_round_trip(db_session):  # type: ignore[no-untyped-def]
    scenario_id = uuid4()
    domain = Client(
        id=uuid4(),
        scenario_id=scenario_id,
        name="ACME S.A. de C.V.",
        sector_description="Manufactura de autopartes",
        payment_history_pattern=PaymentPattern.DELAYED_30,
    )
    # Client requires FK scenario — insert scenario ORM first
    from app.adapters.persistence.models import ScenarioORM

    scenario_orm = ScenarioORM(
        id=str(scenario_id),
        name="Parent",
        sector="manufacturing",
        seed=None,
        parameters={},
        source="generated",
        status="inactive",
        created_at=datetime.now(UTC),
    )
    db_session.add(scenario_orm)
    await db_session.commit()

    orm = client_domain_to_orm(domain)
    db_session.add(orm)
    await db_session.commit()
    await db_session.refresh(orm)
    recovered = client_orm_to_domain(orm)
    assert recovered == domain


@pytest.mark.asyncio
async def test_invoice_round_trip(db_session):  # type: ignore[no-untyped-def]
    client_id = uuid4()
    scenario_id = uuid4()
    domain = Invoice(
        id=uuid4(),
        client_id=client_id,
        folio="F-2026-001",
        amount=50000.0,
        issue_date=datetime.now(UTC),
        due_date=datetime.now(UTC),
        days_overdue=15,
        status="overdue",
    )
    from app.adapters.persistence.models import ClientORM, ScenarioORM

    db_session.add(
        ScenarioORM(
            id=str(scenario_id),
            name="P",
            sector="retail",
            seed=None,
            parameters={},
            source="generated",
            status="inactive",
            created_at=datetime.now(UTC),
        )
    )
    db_session.add(
        ClientORM(
            id=str(client_id),
            scenario_id=str(scenario_id),
            name="Client",
            sector_description=None,
            payment_history_pattern="on_time",
        )
    )
    await db_session.commit()

    orm = invoice_domain_to_orm(domain)
    db_session.add(orm)
    await db_session.commit()
    await db_session.refresh(orm)
    recovered = invoice_orm_to_domain(orm)
    assert recovered == domain


@pytest.mark.asyncio
async def test_payment_round_trip(db_session):  # type: ignore[no-untyped-def]
    domain = Payment(
        id=uuid4(),
        invoice_id=uuid4(),
        amount=25000.0,
        payment_date=datetime.now(UTC),
        method="transfer",
    )
    # Payment has FK to invoice — use non-FK ORM insert for unit test
    from app.adapters.persistence.models import PaymentORM

    orm_direct = PaymentORM(
        id=str(domain.id),
        invoice_id=str(domain.invoice_id),
        amount=domain.amount,
        payment_date=domain.payment_date,
        method=domain.method,
    )
    recovered = payment_orm_to_domain(orm_direct)
    assert recovered == domain


@pytest.mark.asyncio
async def test_score_round_trip(db_session):  # type: ignore[no-untyped-def]
    domain = Score(
        id=uuid4(),
        client_id=uuid4(),
        scenario_id=uuid4(),
        score_value=0.82,
        category=ScoreCategory.HIGH,
        explanation="Strong payment record",
        scored_at=datetime.now(UTC),
    )
    from app.adapters.persistence.models import ScoreORM

    orm_direct = ScoreORM(
        id=str(domain.id),
        client_id=str(domain.client_id),
        scenario_id=str(domain.scenario_id),
        score_value=domain.score_value,
        category=domain.category.value,
        explanation=domain.explanation,
        scored_at=domain.scored_at,
    )
    recovered = score_orm_to_domain(orm_direct)
    assert recovered == domain


@pytest.mark.asyncio
async def test_communication_round_trip(db_session):  # type: ignore[no-untyped-def]
    domain = Communication(
        id=uuid4(),
        client_id=uuid4(),
        scenario_id=uuid4(),
        channel=Channel.EMAIL,
        tone=Tone.FORMAL,
        draft_text="Estimado cliente, le recordamos...",
        status=CommunicationStatus.DRAFT,
        created_at=datetime.now(UTC),
    )
    from app.adapters.persistence.models import CommunicationORM

    orm_direct = CommunicationORM(
        id=str(domain.id),
        client_id=str(domain.client_id),
        scenario_id=str(domain.scenario_id),
        channel=domain.channel.value,
        tone=domain.tone.value,
        draft_text=domain.draft_text,
        status=domain.status.value,
        created_at=domain.created_at,
    )
    recovered = communication_orm_to_domain(orm_direct)
    assert recovered == domain


@pytest.mark.asyncio
async def test_contact_result_round_trip(db_session):  # type: ignore[no-untyped-def]
    domain = ContactResult(
        id=uuid4(),
        client_id=uuid4(),
        communication_id=uuid4(),
        result_type=ContactResultType.PROMISE_TO_PAY,
        notes="Pagará el viernes.",
        recorded_at=datetime.now(UTC),
    )
    orm = contact_result_domain_to_orm(domain)
    recovered = contact_result_orm_to_domain(orm)
    assert recovered == domain
