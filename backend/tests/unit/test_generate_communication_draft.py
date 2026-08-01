from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from app.application.use_cases.generate_communication_draft import (
    GenerateCommunicationDraft,
    GenerateCommunicationDraftRequest,
)
from app.domain.entities.client import Client
from app.domain.entities.communication import Communication
from app.domain.entities.invoice import Invoice
from app.domain.entities.payment import Payment
from app.domain.entities.score import Score
from app.domain.enums import Channel, CommunicationStatus, PaymentPattern, ScoreCategory, Tone
from app.domain.exceptions import EntityNotFoundError
from app.ports.repositories import (
    IClientRepository,
    ICommunicationRepository,
    IInvoiceRepository,
    IPaymentRepository,
    IScenarioRepository,
    IScoreRepository,
)


class MockLLMPort:
    """Mock ILLMPort for testing."""

    def __init__(self) -> None:
        self.generate_calls: list[tuple[str, str, int]] = []

    async def generate(self, prompt: str, model: str, max_tokens: int = 512) -> str:
        self.generate_calls.append((prompt, model, max_tokens))
        return "Estimado cliente, le recordamos su saldo pendiente de $50,000."

    async def query(self, system_prompt: str, user_message: str, model: str) -> str:
        return "mock response"


@pytest.fixture
def mock_scenario_repo() -> MagicMock:
    repo = AsyncMock(spec=IScenarioRepository)
    repo.get_by_id = AsyncMock()
    return repo


@pytest.fixture
def mock_client_repo() -> MagicMock:
    repo = AsyncMock(spec=IClientRepository)
    repo.get_by_id = AsyncMock()
    return repo


@pytest.fixture
def mock_invoice_repo() -> MagicMock:
    repo = AsyncMock(spec=IInvoiceRepository)
    repo.get_by_client_id = AsyncMock()
    return repo


@pytest.fixture
def mock_payment_repo() -> MagicMock:
    repo = AsyncMock(spec=IPaymentRepository)
    repo.get_by_client_id = AsyncMock()
    return repo


@pytest.fixture
def mock_score_repo() -> MagicMock:
    repo = AsyncMock(spec=IScoreRepository)
    repo.get_by_scenario = AsyncMock()
    return repo


@pytest.fixture
def mock_communication_repo() -> MagicMock:
    repo = AsyncMock(spec=ICommunicationRepository)
    repo.add = AsyncMock()
    repo.get_by_client_id = AsyncMock()
    return repo


@pytest.fixture
def mock_draft_service() -> MagicMock:
    service = AsyncMock()
    service.generate = AsyncMock(return_value="Estimado cliente, le recordamos su saldo pendiente.")
    return service


@pytest.fixture
def scenario_id() -> UUID:
    return uuid4()


@pytest.fixture
def client_id() -> UUID:
    return uuid4()


@pytest.fixture
def sample_client(client_id: UUID, scenario_id: UUID) -> Client:
    return Client(
        id=client_id,
        scenario_id=scenario_id,
        name="Empresa ABC",
        sector_description="Manufacturing company",
        payment_history_pattern=PaymentPattern.DELAYED_30,
    )


@pytest.fixture
def sample_invoices(client_id: UUID) -> list[Invoice]:
    return [
        Invoice(
            id=uuid4(),
            client_id=client_id,
            folio="INV-001",
            amount=50000.0,
            issue_date=datetime(2026, 6, 1, tzinfo=UTC),
            due_date=datetime(2026, 7, 1, tzinfo=UTC),
            days_overdue=30,
            status="OVERDUE",
        )
    ]


@pytest.fixture
def sample_payments(client_id: UUID) -> list[Payment]:
    return [
        Payment(
            id=uuid4(),
            invoice_id=uuid4(),
            amount=10000.0,
            payment_date=datetime(2026, 6, 15, tzinfo=UTC),
            method="TRANSFER",
        )
    ]


@pytest.fixture
def sample_score(client_id: UUID, scenario_id: UUID) -> Score:
    return Score(
        id=uuid4(),
        client_id=client_id,
        scenario_id=scenario_id,
        score_value=65.0,
        category=ScoreCategory.MEDIUM,
        explanation="Medium collectability",
        scored_at=datetime.now(UTC),
    )


@pytest.fixture
def sample_communications(client_id: UUID, scenario_id: UUID) -> list[Communication]:
    return [
        Communication(
            id=uuid4(),
            client_id=client_id,
            scenario_id=scenario_id,
            channel=Channel.EMAIL,
            tone=Tone.FORMAL,
            draft_text="Previous draft",
            status=CommunicationStatus.DRAFT,
            created_at=datetime(2026, 7, 20, 10, 0, 0, tzinfo=UTC),
        )
    ]


class TestGenerateCommunicationDraft:
    """Tests for GenerateCommunicationDraft use case."""

    @pytest.mark.asyncio
    async def test_scenario_not_found_raises_entity_not_found(
        self,
        mock_scenario_repo: MagicMock,
        mock_client_repo: MagicMock,
        mock_invoice_repo: MagicMock,
        mock_payment_repo: MagicMock,
        mock_score_repo: MagicMock,
        mock_communication_repo: MagicMock,
        mock_draft_service: MagicMock,
        scenario_id: UUID,
        client_id: UUID,
    ) -> None:
        """Scenario not found raises EntityNotFoundError."""
        mock_scenario_repo.get_by_id.return_value = None

        use_case = GenerateCommunicationDraft(
            scenario_repo=mock_scenario_repo,
            client_repo=mock_client_repo,
            invoice_repo=mock_invoice_repo,
            payment_repo=mock_payment_repo,
            score_repo=mock_score_repo,
            communication_repo=mock_communication_repo,
            draft_service=mock_draft_service,
        )

        request = GenerateCommunicationDraftRequest(
            scenario_id=scenario_id,
            client_id=client_id,
            channel=Channel.EMAIL,
            tone=Tone.FORMAL,
        )

        with pytest.raises(EntityNotFoundError) as exc_info:
            await use_case.execute(request)

        assert exc_info.value.entity_type == "Scenario"
        assert str(scenario_id) in str(exc_info.value)
        mock_scenario_repo.get_by_id.assert_awaited_once_with(scenario_id)

    @pytest.mark.asyncio
    async def test_client_not_found_raises_entity_not_found(
        self,
        mock_scenario_repo: MagicMock,
        mock_client_repo: MagicMock,
        mock_invoice_repo: MagicMock,
        mock_payment_repo: MagicMock,
        mock_score_repo: MagicMock,
        mock_communication_repo: MagicMock,
        mock_draft_service: MagicMock,
        scenario_id: UUID,
        client_id: UUID,
        sample_client: Client,
    ) -> None:
        """Client not found raises EntityNotFoundError."""
        mock_scenario_repo.get_by_id.return_value = MagicMock()  # scenario exists
        mock_client_repo.get_by_id.return_value = None  # but client doesn't

        use_case = GenerateCommunicationDraft(
            scenario_repo=mock_scenario_repo,
            client_repo=mock_client_repo,
            invoice_repo=mock_invoice_repo,
            payment_repo=mock_payment_repo,
            score_repo=mock_score_repo,
            communication_repo=mock_communication_repo,
            draft_service=mock_draft_service,
        )

        request = GenerateCommunicationDraftRequest(
            scenario_id=scenario_id,
            client_id=client_id,
            channel=Channel.EMAIL,
            tone=Tone.FORMAL,
        )

        with pytest.raises(EntityNotFoundError) as exc_info:
            await use_case.execute(request)

        assert exc_info.value.entity_type == "Client"
        assert str(client_id) in str(exc_info.value)
        mock_client_repo.get_by_id.assert_awaited_once_with(client_id)

    @pytest.mark.asyncio
    async def test_successful_generation_persists_communication(
        self,
        mock_scenario_repo: MagicMock,
        mock_client_repo: MagicMock,
        mock_invoice_repo: MagicMock,
        mock_payment_repo: MagicMock,
        mock_score_repo: MagicMock,
        mock_communication_repo: MagicMock,
        mock_draft_service: MagicMock,
        scenario_id: UUID,
        client_id: UUID,
        sample_client: Client,
        sample_invoices: list[Invoice],
        sample_payments: list[Payment],
        sample_score: Score,
        sample_communications: list[Communication],
    ) -> None:
        """Successful generation persists Communication with DRAFT status."""
        mock_scenario_repo.get_by_id.return_value = MagicMock()
        mock_client_repo.get_by_id.return_value = sample_client
        mock_invoice_repo.get_by_client_id.return_value = sample_invoices
        mock_payment_repo.get_by_client_id.return_value = sample_payments
        mock_score_repo.get_by_scenario.return_value = [sample_score]
        mock_communication_repo.get_by_client_id.return_value = sample_communications

        use_case = GenerateCommunicationDraft(
            scenario_repo=mock_scenario_repo,
            client_repo=mock_client_repo,
            invoice_repo=mock_invoice_repo,
            payment_repo=mock_payment_repo,
            score_repo=mock_score_repo,
            communication_repo=mock_communication_repo,
            draft_service=mock_draft_service,
        )

        request = GenerateCommunicationDraftRequest(
            scenario_id=scenario_id,
            client_id=client_id,
            channel=Channel.WHATSAPP,
            tone=Tone.URGENT,
        )

        response = await use_case.execute(request)

        # Verify response
        assert isinstance(response.communication, Communication)
        assert response.communication.client_id == client_id
        assert response.communication.scenario_id == scenario_id
        assert response.communication.channel == Channel.WHATSAPP
        assert response.communication.tone == Tone.URGENT
        assert response.communication.status == CommunicationStatus.DRAFT
        assert response.communication.draft_text == (
            "Estimado cliente, le recordamos su saldo pendiente."
        )

        # Verify draft_service.generate was called
        mock_draft_service.generate.assert_awaited_once()
        call_args = mock_draft_service.generate.call_args
        # generate(case_detail, channel, tone) - positional args
        assert call_args.args[1] == Channel.WHATSAPP
        assert call_args.args[2] == Tone.URGENT

        # Verify communication was persisted
        mock_communication_repo.add.assert_awaited_once()
        persisted_comm = mock_communication_repo.add.call_args[0][0]
        assert isinstance(persisted_comm, Communication)
        assert persisted_comm.client_id == client_id
        assert persisted_comm.scenario_id == scenario_id
        assert persisted_comm.channel == Channel.WHATSAPP
        assert persisted_comm.tone == Tone.URGENT
        assert persisted_comm.status == CommunicationStatus.DRAFT

    @pytest.mark.asyncio
    async def test_fetches_case_aggregate_in_correct_order(
        self,
        mock_scenario_repo: MagicMock,
        mock_client_repo: MagicMock,
        mock_invoice_repo: MagicMock,
        mock_payment_repo: MagicMock,
        mock_score_repo: MagicMock,
        mock_communication_repo: MagicMock,
        mock_draft_service: MagicMock,
        scenario_id: UUID,
        client_id: UUID,
        sample_client: Client,
        sample_invoices: list[Invoice],
        sample_payments: list[Payment],
        sample_score: Score,
        sample_communications: list[Communication],
    ) -> None:
        """Verifies repos are called in correct order and data sorted correctly."""
        mock_scenario_repo.get_by_id.return_value = MagicMock()
        mock_client_repo.get_by_id.return_value = sample_client
        mock_invoice_repo.get_by_client_id.return_value = sample_invoices
        mock_payment_repo.get_by_client_id.return_value = sample_payments
        mock_score_repo.get_by_scenario.return_value = [sample_score]
        mock_communication_repo.get_by_client_id.return_value = sample_communications

        use_case = GenerateCommunicationDraft(
            scenario_repo=mock_scenario_repo,
            client_repo=mock_client_repo,
            invoice_repo=mock_invoice_repo,
            payment_repo=mock_payment_repo,
            score_repo=mock_score_repo,
            communication_repo=mock_communication_repo,
            draft_service=mock_draft_service,
        )

        request = GenerateCommunicationDraftRequest(
            scenario_id=scenario_id,
            client_id=client_id,
            channel=Channel.EMAIL,
            tone=Tone.FORMAL,
        )

        await use_case.execute(request)

        # Verify all repos called
        mock_scenario_repo.get_by_id.assert_awaited_once_with(scenario_id)
        mock_client_repo.get_by_id.assert_awaited_once_with(client_id)
        mock_invoice_repo.get_by_client_id.assert_awaited_once_with(client_id)
        mock_payment_repo.get_by_client_id.assert_awaited_once_with(client_id)
        mock_score_repo.get_by_scenario.assert_awaited_once_with(scenario_id)
        mock_communication_repo.get_by_client_id.assert_awaited_once_with(client_id)

    @pytest.mark.asyncio
    async def test_handles_no_invoices_no_payments_no_score_no_comms(
        self,
        mock_scenario_repo: MagicMock,
        mock_client_repo: MagicMock,
        mock_invoice_repo: MagicMock,
        mock_payment_repo: MagicMock,
        mock_score_repo: MagicMock,
        mock_communication_repo: MagicMock,
        mock_draft_service: MagicMock,
        scenario_id: UUID,
        client_id: UUID,
        sample_client: Client,
    ) -> None:
        """Handles empty invoices, payments, score, and communications."""
        mock_scenario_repo.get_by_id.return_value = MagicMock()
        mock_client_repo.get_by_id.return_value = sample_client
        mock_invoice_repo.get_by_client_id.return_value = []
        mock_payment_repo.get_by_client_id.return_value = []
        mock_score_repo.get_by_scenario.return_value = []  # no score for client
        mock_communication_repo.get_by_client_id.return_value = []

        use_case = GenerateCommunicationDraft(
            scenario_repo=mock_scenario_repo,
            client_repo=mock_client_repo,
            invoice_repo=mock_invoice_repo,
            payment_repo=mock_payment_repo,
            score_repo=mock_score_repo,
            communication_repo=mock_communication_repo,
            draft_service=mock_draft_service,
        )

        request = GenerateCommunicationDraftRequest(
            scenario_id=scenario_id,
            client_id=client_id,
            channel=Channel.EMAIL,
            tone=Tone.FORMAL,
        )

        response = await use_case.execute(request)

        assert response.communication.status == CommunicationStatus.DRAFT
        mock_draft_service.generate.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_draft_service_failure_propagates(
        self,
        mock_scenario_repo: MagicMock,
        mock_client_repo: MagicMock,
        mock_invoice_repo: MagicMock,
        mock_payment_repo: MagicMock,
        mock_score_repo: MagicMock,
        mock_communication_repo: MagicMock,
        mock_draft_service: MagicMock,
        scenario_id: UUID,
        client_id: UUID,
        sample_client: Client,
        sample_invoices: list[Invoice],
        sample_payments: list[Payment],
        sample_score: Score,
        sample_communications: list[Communication],
    ) -> None:
        """Draft service failure propagates (no communication persisted)."""
        mock_scenario_repo.get_by_id.return_value = MagicMock()
        mock_client_repo.get_by_id.return_value = sample_client
        mock_invoice_repo.get_by_client_id.return_value = sample_invoices
        mock_payment_repo.get_by_client_id.return_value = sample_payments
        mock_score_repo.get_by_scenario.return_value = [sample_score]
        mock_communication_repo.get_by_client_id.return_value = sample_communications

        # Make draft service fail
        mock_draft_service.generate.side_effect = Exception("OpenRouter error")

        use_case = GenerateCommunicationDraft(
            scenario_repo=mock_scenario_repo,
            client_repo=mock_client_repo,
            invoice_repo=mock_invoice_repo,
            payment_repo=mock_payment_repo,
            score_repo=mock_score_repo,
            communication_repo=mock_communication_repo,
            draft_service=mock_draft_service,
        )

        request = GenerateCommunicationDraftRequest(
            scenario_id=scenario_id,
            client_id=client_id,
            channel=Channel.EMAIL,
            tone=Tone.FORMAL,
        )

        with pytest.raises(Exception, match="OpenRouter error"):
            await use_case.execute(request)

        # Communication should NOT be persisted on failure
        mock_communication_repo.add.assert_not_awaited()
