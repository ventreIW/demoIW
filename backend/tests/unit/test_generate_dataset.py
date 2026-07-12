from unittest.mock import AsyncMock, MagicMock, patch
import pandas as pd
import pytest
from uuid import UUID, uuid4
from datetime import datetime, timezone

from app.domain.entities.client import Client
from app.domain.entities.invoice import Invoice
from app.domain.entities.payment import Payment
from app.domain.entities.scenario import Scenario
from app.domain.value_objects.generation_params import GenerationParams
from app.domain.enums import Sector, ScenarioStatus, PaymentPattern
from app.domain.value_objects.raw_dataset import RawDataset
from app.application.use_cases.generate_dataset import GenerateDataset
from app.application.services.llm_enrichment_service import LLMEnrichmentService
from app.ports.repositories import (
    IScenarioRepository,
    IClientRepository,
    IInvoiceRepository,
    IPaymentRepository,
)


@pytest.mark.asyncio
async def test_generate_dataset_execute_persists_via_repositories():
    # Arrange
    raw_dataset = RawDataset(
        clients=pd.DataFrame({"id": ["11111111-1111-1111-1111-111111111111"], "name": ["Client A"], "sector": [Sector.MANUFACTURING.value], "payment_history_pattern": [PaymentPattern.ON_TIME.value]}),
        invoices=pd.DataFrame({"id": ["33333333-3333-3333-3333-333333333333"], "client_id": ["11111111-1111-1111-1111-111111111111"], "folio": ["INV-001"], "amount": [100.0], "issue_date": [datetime(2024, 1, 1, tzinfo=timezone.utc)], "due_date": [datetime(2024, 2, 1, tzinfo=timezone.utc)], "days_overdue": [0], "status": ["PENDING"]}),
        payments=pd.DataFrame({"id": ["55555555-5555-5555-5555-555555555555"], "invoice_id": ["33333333-3333-3333-3333-333333333333"], "amount": [50.0], "payment_date": [datetime(2024, 1, 15, tzinfo=timezone.utc)], "method": ["UNKNOWN"]}),
    )
    enriched_dataset = RawDataset(
        clients=pd.DataFrame({"id": ["11111111-1111-1111-1111-111111111111"], "name": ["Client A"], "sector": [Sector.MANUFACTURING.value], "payment_history_pattern": [PaymentPattern.ON_TIME.value], "sector_description": ["Desc A"]}),
        invoices=pd.DataFrame({"id": ["33333333-3333-3333-3333-333333333333"], "client_id": ["11111111-1111-1111-1111-111111111111"], "folio": ["INV-001"], "amount": [100.0], "issue_date": [datetime(2024, 1, 1, tzinfo=timezone.utc)], "due_date": [datetime(2024, 2, 1, tzinfo=timezone.utc)], "days_overdue": [0], "status": ["PENDING"]}),
        payments=pd.DataFrame({"id": ["55555555-5555-5555-5555-555555555555"], "invoice_id": ["33333333-3333-3333-3333-333333333333"], "amount": [50.0], "payment_date": [datetime(2024, 1, 15, tzinfo=timezone.utc)], "method": ["UNKNOWN"]}),
    )

    mock_enrichment_service = AsyncMock(spec=LLMEnrichmentService)
    mock_enrichment_service.enrich.return_value = enriched_dataset

    mock_scenario_repo = AsyncMock(spec=IScenarioRepository)
    mock_scenario_repo.add.return_value = Scenario(
        id=uuid4(),
        name="Test Scenario",
        sector=Sector.MANUFACTURING,
        seed=None,
        parameters={},
        source="procedural+enrichment",
        status=ScenarioStatus.INACTIVE,
        created_at=datetime.now(timezone.utc),
    )
    mock_scenario_repo.set_active = AsyncMock()

    mock_client_repo = AsyncMock(spec=IClientRepository)
    mock_client_repo.add_many.return_value = [
        Client(
            id=uuid4(),
            scenario_id=uuid4(),
            name="Client A",
            sector_description="Desc A",
            payment_history_pattern=PaymentPattern.ON_TIME,
        )
    ]

    mock_invoice_repo = AsyncMock(spec=IInvoiceRepository)
    mock_invoice_repo.add_many.return_value = [
        Invoice(
            id=uuid4(),
            client_id=uuid4(),
            folio="INV-001",
            amount=100.0,
            issue_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
            due_date=datetime(2024, 2, 1, tzinfo=timezone.utc),
            days_overdue=0,
            status="PENDING",
        )
    ]

    mock_payment_repo = AsyncMock(spec=IPaymentRepository)
    mock_payment_repo.add_many.return_value = [
        Payment(
            id=uuid4(),
            invoice_id=uuid4(),
            amount=50.0,
            payment_date=datetime(2024, 1, 15, tzinfo=timezone.utc),
            method="UNKNOWN",
        )
    ]

    params = GenerationParams(
        seed=42,
        sector=Sector.MANUFACTURING,
        client_count=1,
        invoice_volume=1.0,
        amount_mean=100.0,
        amount_std=100.0,
        reference_date=None,
    )
    model = "test-model"

    use_case = GenerateDataset(
        enrichment_service=mock_enrichment_service,
        scenario_repo=mock_scenario_repo,
        client_repo=mock_client_repo,
        invoice_repo=mock_invoice_repo,
        payment_repo=mock_payment_repo,
    )

    # Patch ProceduralGenerator to return our raw dataset
    with patch(
        "app.application.use_cases.generate_dataset.ProceduralGenerator"
    ) as mock_generator_cls:
        mock_generator_instance = MagicMock()
        mock_generator_instance.generate.return_value = raw_dataset
        mock_generator_cls.return_value = mock_generator_instance

        # Act
        result = await use_case.execute(params, model)

    # Assert
    mock_generator_cls.assert_called_once_with(params)
    mock_generator_instance.generate.assert_called_once_with()
    mock_enrichment_service.enrich.assert_awaited_once_with(raw_dataset, model)
    mock_scenario_repo.add.assert_awaited_once()
    mock_scenario_repo.set_active.assert_awaited_once()
    mock_client_repo.add_many.assert_awaited_once()
    mock_invoice_repo.add_many.assert_awaited_once()
    mock_payment_repo.add_many.assert_awaited_once()
    assert result is enriched_dataset