from datetime import datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.adapters.persistence.models import Base, ClientORM, InvoiceORM
from app.adapters.persistence.sqlalchemy_invoice_repo import SQLAlchemyInvoiceRepository
from app.domain.entities.invoice import Invoice
from app.ports.repositories import IInvoiceRepository


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


def test_sqlalchemy_invoice_repository_exists():
    assert SQLAlchemyInvoiceRepository is not None


def test_sqlalchemy_invoice_repository_is_subclass_of_iinvoice_repository():
    assert issubclass(SQLAlchemyInvoiceRepository, IInvoiceRepository)


def test_sqlalchemy_invoice_repository_has_required_methods():
    assert hasattr(SQLAlchemyInvoiceRepository, "add")
    assert hasattr(SQLAlchemyInvoiceRepository, "add_many")
    assert hasattr(SQLAlchemyInvoiceRepository, "get_by_scenario_id")
    assert hasattr(SQLAlchemyInvoiceRepository, "get_by_id")


@pytest.mark.asyncio
async def test_sqlalchemy_invoice_repository_can_be_instantiated(async_session):
    repo = SQLAlchemyInvoiceRepository(async_session)
    assert isinstance(repo, SQLAlchemyInvoiceRepository)


@pytest.mark.asyncio
async def test_add_returns_invoice(async_session):
    repo = SQLAlchemyInvoiceRepository(async_session)
    invoice_id = uuid4()
    client_id = uuid4()
    invoice = Invoice(
        id=invoice_id,
        client_id=client_id,
        folio="FOL-001",
        amount=100.0,
        issue_date=datetime(2024, 1, 1),
        due_date=datetime(2024, 1, 30),
        days_overdue=0,
        status="PENDING",
    )
    returned_invoice = await repo.add(invoice)
    assert isinstance(returned_invoice, Invoice)
    # The ID should have been generated (different from input)
    assert returned_invoice.id != invoice_id
    assert isinstance(returned_invoice.id, UUID)
    # Verify it's in the database
    from sqlalchemy import select

    result = await async_session.execute(
        select(InvoiceORM).where(InvoiceORM.id == str(returned_invoice.id))
    )
    orm = result.scalar_one_or_none()
    assert orm is not None
    assert orm.folio == "FOL-001"


@pytest.mark.asyncio
async def test_add_many_returns_list_of_invoices(async_session):
    repo = SQLAlchemyInvoiceRepository(async_session)
    invoices = [
        Invoice(
            id=uuid4(),
            client_id=uuid4(),
            folio=f"FOL-{i:03d}",
            amount=float(100 + i * 10),
            issue_date=datetime(2024, 1, 1),
            due_date=datetime(2024, 1, 30),
            days_overdue=0,
            status="PENDING",
        )
        for i in range(2)
    ]
    returned_invoices = await repo.add_many(invoices)
    assert len(returned_invoices) == 2
    for inv in returned_invoices:
        assert isinstance(inv, Invoice)
        assert isinstance(inv.id, UUID)
    # Verify both are in the database
    from sqlalchemy import select

    result = await async_session.execute(select(InvoiceORM))
    orms = result.scalars().all()
    assert len(orms) == 2
    folios = {orm.folio for orm in orms}
    assert folios == {"FOL-000", "FOL-001"}


@pytest.mark.asyncio
async def test_get_by_scenario_id_returns_list_of_invoices(async_session):
    repo = SQLAlchemyInvoiceRepository(async_session)
    scenario_id = uuid4()
    client_id = uuid4()
    # Create a client linked to the scenario
    from sqlalchemy import insert

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
    # Create two invoices for this client
    invoice_id_1 = uuid4()
    invoice_id_2 = uuid4()
    await async_session.execute(
        insert(InvoiceORM).values(
            [
                {
                    "id": str(invoice_id_1),
                    "client_id": str(client_id),
                    "folio": "INV-001",
                    "amount": 250.0,
                    "issue_date": datetime(2024, 2, 1),
                    "due_date": datetime(2024, 3, 1),
                    "days_overdue": 0,
                    "status": "PAID",
                },
                {
                    "id": str(invoice_id_2),
                    "client_id": str(client_id),
                    "folio": "INV-002",
                    "amount": 500.0,
                    "issue_date": datetime(2024, 2, 5),
                    "due_date": datetime(2024, 3, 5),
                    "days_overdue": 10,
                    "status": "OVERDUE",
                },
            ]
        )
    )
    await async_session.commit()
    # Now call the method
    invoices = await repo.get_by_scenario_id(scenario_id)
    assert len(invoices) == 2
    assert all(isinstance(inv, Invoice) for inv in invoices)
    folios = {inv.folio for inv in invoices}
    assert folios == {"INV-001", "INV-002"}
    # Check amounts
    amounts = {inv.amount for inv in invoices}
    assert amounts == {250.0, 500.0}


@pytest.mark.asyncio
async def test_get_by_id_returns_invoice_or_none(async_session):
    repo = SQLAlchemyInvoiceRepository(async_session)
    # Create a client
    client_id = uuid4()
    from sqlalchemy import insert

    await async_session.execute(
        insert(ClientORM).values(
            {
                "id": str(client_id),
                "scenario_id": str(uuid4()),
                "name": "Client To Find",
                "sector_description": None,
                "payment_history_pattern": "ON_TIME",
            }
        )
    )
    # Create an invoice
    invoice_id = uuid4()
    await async_session.execute(
        insert(InvoiceORM).values(
            {
                "id": str(invoice_id),
                "client_id": str(client_id),
                "folio": "INV-FIND",
                "amount": 123.45,
                "issue_date": datetime(2024, 1, 1),
                "due_date": datetime(2024, 2, 1),
                "days_overdue": 5,
                "status": "PENDING",
            }
        )
    )
    await async_session.commit()
    # Fetch by ID
    invoice = await repo.get_by_id(invoice_id)
    assert isinstance(invoice, Invoice)
    assert invoice.id == invoice_id
    assert invoice.folio == "INV-FIND"
    assert invoice.amount == 123.45
    # Fetch non-existing ID
    invoice = await repo.get_by_id(uuid4())
    assert invoice is None
