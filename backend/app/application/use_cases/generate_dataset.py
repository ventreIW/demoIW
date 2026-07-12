from datetime import date, datetime, timezone
from uuid import UUID, uuid4
import pandas as pd

from pydantic import BaseModel, Field

from app.domain.enums import Sector, ScenarioStatus, PaymentPattern
from app.domain.value_objects.generation_params import GenerationParams
from app.adapters.dataset.procedural_generator import ProceduralGenerator
from app.application.services.llm_enrichment_service import LLMEnrichmentService
from app.domain.value_objects.raw_dataset import RawDataset
from app.domain.entities.scenario import Scenario
from app.domain.entities.client import Client
from app.domain.entities.invoice import Invoice
from app.domain.entities.payment import Payment
from app.ports.repositories import (
    IScenarioRepository,
    IClientRepository,
    IInvoiceRepository,
    IPaymentRepository,
)


class GenerateDataset:
    def __init__(
        self,
        enrichment_service: LLMEnrichmentService,
        scenario_repo: IScenarioRepository,
        client_repo: IClientRepository,
        invoice_repo: IInvoiceRepository,
        payment_repo: IPaymentRepository,
    ) -> None:
        self._enrichment_service = enrichment_service
        self._scenario_repo = scenario_repo
        self._client_repo = client_repo
        self._invoice_repo = invoice_repo
        self._payment_repo = payment_repo

    async def execute(self, params: GenerationParams, model: str) -> RawDataset:
        # Step 1: Generate procedural dataset using the provided parameters.
        generator = ProceduralGenerator(params)
        raw_dataset = generator.generate()

        # Step 2: Enrich the dataset using the LLM service.
        enriched_dataset = await self._enrichment_service.enrich(
            raw_dataset, model
        )

        # Step 3: Create Scenario, persist and activate.
        scenario = Scenario(
            id=uuid4(),  # temporary ID, will be replaced by repository
            name=f"Scenario-{params.sector.value}",
            sector=params.sector,
            seed=params.seed,
            parameters=params.model_dump(),
            source="procedural+enrichment",
            status=ScenarioStatus.INACTIVE,
            created_at=datetime.now(timezone.utc),
        )
        saved_scenario = await self._scenario_repo.add(scenario)
        await self._scenario_repo.set_active(saved_scenario.id)

        # Step 4: Map and persist clients.
        client_entities = []
        for record in enriched_dataset.clients.to_dict('records'):
            sector_description = record.get("sector_description")
            if pd.isna(sector_description):
                sector_description = None
            client = Client(
                id=UUID(record["id"]),  # use original client id as id in Client object
                scenario_id=saved_scenario.id,
                name=record["name"],
                sector_description=sector_description,
                payment_history_pattern=PaymentPattern(record["payment_history_pattern"]),
            )
            client_entities.append(client)
        saved_clients = await self._client_repo.add_many(client_entities)
        client_id_map = {
            client.id: saved_client.id
            for client, saved_client in zip(client_entities, saved_clients)
        }

        # Step 5: Map and persist invoices.
        invoice_entities = []
        for record in enriched_dataset.invoices.to_dict('records'):
            invoice = Invoice(
                id=UUID(record["id"]),  # use original invoice id as id in Invoice object
                client_id=client_id_map[UUID(record["client_id"])],
                folio=record["folio"],
                amount=record["amount"],
                issue_date=record["issue_date"],
                due_date=record["due_date"],
                days_overdue=record["days_overdue"],
                status=record["status"],
            )
            invoice_entities.append(invoice)
        saved_invoices = await self._invoice_repo.add_many(invoice_entities)
        invoice_id_map = {
            invoice.id: saved_invoice.id
            for invoice, saved_invoice in zip(invoice_entities, saved_invoices)
        }

        # Step 6: Map and persist payments.
        payment_entities = []
        for record in enriched_dataset.payments.to_dict('records'):
            payment = Payment(
                id=UUID(record["id"]),  # use original payment id as id in Payment object
                invoice_id=invoice_id_map[UUID(record["invoice_id"])],
                amount=record["amount"],
                payment_date=record["paid_date"],
                method=record.get("method", "UNKNOWN"),
            )
            payment_entities.append(payment)
        await self._payment_repo.add_many(payment_entities)

        # Step 7: Return the enriched dataset (unchanged).
        return enriched_dataset