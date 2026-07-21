from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.adapters.persistence.models import Base, ClientORM, InvoiceORM, PaymentORM, ScenarioORM
from app.adapters.persistence.sqlalchemy_payment_repo import SQLAlchemyPaymentRepository
from app.domain.entities.payment import Payment
from app.ports.repositories import IPaymentRepository


@pytest.fixture
async def async_session():
    # Create an in-memory SQLite database for testing
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # Create a session
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)()
    yield async_session
    await async_session.close()
    await engine.dispose()


def test_sqlalchemy_payment_repository_exists():
    assert SQLAlchemyPaymentRepository is not None


def test_sqlalchemy_payment_repository_is_subclass_of_ipayment_repository():
    assert issubclass(SQLAlchemyPaymentRepository, IPaymentRepository)


def test_sqlalchemy_payment_repository_has_required_methods():
    assert hasattr(SQLAlchemyPaymentRepository, "add")
    assert hasattr(SQLAlchemyPaymentRepository, "add_many")
    assert hasattr(SQLAlchemyPaymentRepository, "get_by_scenario_id")
    assert hasattr(SQLAlchemyPaymentRepository, "get_by_id")


@pytest.mark.asyncio
async def test_sqlalchemy_payment_repository_can_be_instantiated(async_session):
    repo = SQLAlchemyPaymentRepository(async_session)
    assert isinstance(repo, SQLAlchemyPaymentRepository)


@pytest.mark.asyncio
async def test_add_returns_payment(async_session):
    repo = SQLAlchemyPaymentRepository(async_session)
    # Need an invoice to link payment to
    # Create scenario, client, invoice first
    scenario_id = uuid4()
    client_id = uuid4()
    invoice_id = uuid4()
    from sqlalchemy import insert

    # Insert scenario
    await async_session.execute(
        insert(ScenarioORM).values(
            {
                "id": str(scenario_id),
                "name": "Test Scenario",
                "sector": "TEST",
                "seed": None,
                "parameters": {},
                "source": "manual",
                "status": "active",
                "created_at": datetime.now(UTC),
            }
        )
    )
    # Insert client
    await async_session.execute(
        insert(ClientORM).values(
            {
                "id": str(client_id),
                "scenario_id": str(scenario_id),
                "name": "Test Client",
                "sector_description": None,
                "payment_history_pattern": "ON_TIME",
            }
        )
    )
    # Insert invoice
    await async_session.execute(
        insert(InvoiceORM).values(
            {
                "id": str(invoice_id),
                "client_id": str(client_id),
                "folio": "INV-001",
                "amount": 100.0,
                "issue_date": datetime(2024, 1, 1, tzinfo=UTC),
                "due_date": datetime(2024, 2, 1, tzinfo=UTC),
                "days_overdue": 0,
                "status": "PENDING",
            }
        )
    )
    await async_session.commit()

    payment_id = uuid4()
    payment = Payment(
        id=payment_id,
        invoice_id=invoice_id,
        amount=50.0,
        payment_date=datetime(2024, 1, 15, tzinfo=UTC),
        method="BANK_TRANSFER",
    )
    returned_payment = await repo.add(payment)
    assert isinstance(returned_payment, Payment)
    # The ID should have been generated (different from input)
    assert returned_payment.id != payment_id
    assert isinstance(returned_payment.id, UUID)
    # Verify it's in the database
    from sqlalchemy import select

    result = await async_session.execute(
        select(PaymentORM).where(PaymentORM.id == str(returned_payment.id))
    )
    orm = result.scalar_one_or_none()
    assert orm is not None
    assert orm.amount == 50.0
    assert orm.method == "BANK_TRANSFER"


@pytest.mark.asyncio
async def test_add_many_returns_list_of_payments(async_session):
    repo = SQLAlchemyPaymentRepository(async_session)
    # Setup: scenario, client, two invoices
    scenario_id = uuid4()
    client_id = uuid4()
    invoice_id_1 = uuid4()
    invoice_id_2 = uuid4()
    from sqlalchemy import insert

    await async_session.execute(
        insert(ScenarioORM).values(
            {
                "id": str(scenario_id),
                "name": "Scenario 2",
                "sector": "TEST",
                "seed": None,
                "parameters": {},
                "source": "manual",
                "status": "active",
                "created_at": datetime.now(UTC),
            }
        )
    )
    await async_session.execute(
        insert(ClientORM).values(
            {
                "id": str(client_id),
                "scenario_id": str(scenario_id),
                "name": "Client Two",
                "sector_description": None,
                "payment_history_pattern": "ON_TIME",
            }
        )
    )
    await async_session.execute(
        insert(InvoiceORM).values(
            [
                {
                    "id": str(invoice_id_1),
                    "client_id": str(client_id),
                    "folio": "INV-001",
                    "amount": 100.0,
                    "issue_date": datetime(2024, 1, 1, tzinfo=UTC),
                    "due_date": datetime(2024, 2, 1, tzinfo=UTC),
                    "days_overdue": 0,
                    "status": "PENDING",
                },
                {
                    "id": str(invoice_id_2),
                    "client_id": str(client_id),
                    "folio": "INV-002",
                    "amount": 200.0,
                    "issue_date": datetime(2024, 1, 2, tzinfo=UTC),
                    "due_date": datetime(2024, 2, 2, tzinfo=UTC),
                    "days_overdue": 0,
                    "status": "PENDING",
                },
            ]
        )
    )
    await async_session.commit()

    payments = [
        Payment(
            id=uuid4(),
            invoice_id=invoice_id_1,
            amount=30.0,
            payment_date=datetime(2024, 1, 10, tzinfo=UTC),
            method="CASH",
        ),
        Payment(
            id=uuid4(),
            invoice_id=invoice_id_2,
            amount=70.0,
            payment_date=datetime(2024, 1, 12, tzinfo=UTC),
            method="CARD",
        ),
    ]
    returned_payments = await repo.add_many(payments)
    assert len(returned_payments) == 2
    for p in returned_payments:
        assert isinstance(p, Payment)
        assert isinstance(p.id, UUID)
    # Verify both are in the database
    from sqlalchemy import select

    result = await async_session.execute(select(PaymentORM))
    orms = result.scalars().all()
    assert len(orms) == 2
    amounts = {orm.amount for orm in orms}
    assert amounts == {30.0, 70.0}
    methods = {orm.method for orm in orms}
    assert methods == {"CASH", "CARD"}


@pytest.mark.asyncio
async def test_get_by_scenario_id_returns_list_of_payments(async_session):
    repo = SQLAlchemyPaymentRepository(async_session)
    scenario_id = uuid4()
    client_id = uuid4()
    invoice_id = uuid4()
    from sqlalchemy import insert

    # scenario
    await async_session.execute(
        insert(ScenarioORM).values(
            {
                "id": str(scenario_id),
                "name": "Scenario for Payments",
                "sector": "TEST",
                "seed": None,
                "parameters": {},
                "source": "manual",
                "status": "active",
                "created_at": datetime.now(UTC),
            }
        )
    )
    # client
    await async_session.execute(
        insert(ClientORM).values(
            {
                "id": str(client_id),
                "scenario_id": str(scenario_id),
                "name": "Client Pay",
                "sector_description": None,
                "payment_history_pattern": "ON_TIME",
            }
        )
    )
    # invoice
    await async_session.execute(
        insert(InvoiceORM).values(
            {
                "id": str(invoice_id),
                "client_id": str(client_id),
                "folio": "INV-PAY",
                "amount": 250.0,
                "issue_date": datetime(2024, 1, 1, tzinfo=UTC),
                "due_date": datetime(2024, 2, 1, tzinfo=UTC),
                "days_overdue": 0,
                "status": "PENDING",
            }
        )
    )
    # two payments for this invoice
    payment_id_1 = uuid4()
    payment_id_2 = uuid4()
    await async_session.execute(
        insert(PaymentORM).values(
            [
                {
                    "id": str(payment_id_1),
                    "invoice_id": str(invoice_id),
                    "amount": 100.0,
                    "payment_date": datetime(2024, 1, 15, tzinfo=UTC),
                    "method": "BANK",
                },
                {
                    "id": str(payment_id_2),
                    "invoice_id": str(invoice_id),
                    "amount": 150.0,
                    "payment_date": datetime(2024, 1, 20, tzinfo=UTC),
                    "method": "CARD",
                },
            ]
        )
    )
    await async_session.commit()
    # Now call the method
    payments = await repo.get_by_scenario_id(scenario_id)
    assert len(payments) == 2
    assert all(isinstance(p, Payment) for p in payments)
    ids = {p.id for p in payments}
    assert ids == {payment_id_1, payment_id_2}
    amounts = {p.amount for p in payments}
    assert amounts == {100.0, 150.0}
    methods = {p.method for p in payments}
    assert methods == {"BANK", "CARD"}


@pytest.mark.asyncio
async def test_get_by_id_returns_payment_or_none(async_session):
    repo = SQLAlchemyPaymentRepository(async_session)
    # Need an invoice to link payment to
    scenario_id = uuid4()
    client_id = uuid4()
    invoice_id = uuid4()
    from sqlalchemy import insert

    await async_session.execute(
        insert(ScenarioORM).values(
            {
                "id": str(scenario_id),
                "name": "Scenario for GetById",
                "sector": "TEST",
                "seed": None,
                "parameters": {},
                "source": "manual",
                "status": "active",
                "created_at": datetime.now(UTC),
            }
        )
    )
    await async_session.execute(
        insert(ClientORM).values(
            {
                "id": str(client_id),
                "scenario_id": str(scenario_id),
                "name": "Client GetById",
                "sector_description": None,
                "payment_history_pattern": "ON_TIME",
            }
        )
    )
    await async_session.execute(
        insert(InvoiceORM).values(
            {
                "id": str(invoice_id),
                "client_id": str(client_id),
                "folio": "INV-GETBYID",
                "amount": 300.0,
                "issue_date": datetime(2024, 1, 1, tzinfo=UTC),
                "due_date": datetime(2024, 2, 1, tzinfo=UTC),
                "days_overdue": 0,
                "status": "PENDING",
            }
        )
    )
    payment_id = uuid4()
    await async_session.execute(
        insert(PaymentORM).values(
            {
                "id": str(payment_id),
                "invoice_id": str(invoice_id),
                "amount": 75.5,
                "payment_date": datetime(2024, 1, 10, tzinfo=UTC),
                "method": "PAYPAL",
            }
        )
    )
    await async_session.commit()
    # Fetch by ID
    payment = await repo.get_by_id(payment_id)
    assert isinstance(payment, Payment)
    assert payment.id == payment_id
    assert payment.amount == 75.5
    assert payment.method == "PAYPAL"
    # Fetch non-existing ID
    payment = await repo.get_by_id(uuid4())
    assert payment is None
