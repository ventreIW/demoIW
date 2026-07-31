from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app.application.services.communication_draft_service import (
    CaseDetail,
    CommunicationDraftService,
    case_detail_response_to_domain,
)
from app.domain.enums import Channel, Tone
from app.ports.llm_port import ILLMPort


class MockLLMPort(ILLMPort):
    """Mock ILLMPort for testing."""

    def __init__(self) -> None:
        self.generate_calls: list[tuple[str, str, int]] = []

    async def generate(self, prompt: str, model: str, max_tokens: int = 512) -> str:
        self.generate_calls.append((prompt, model, max_tokens))
        return "Estimado cliente, le recordamos su saldo pendiente de $50,000."

    async def query(self, system_prompt: str, user_message: str, model: str) -> str:
        return "mock response"


@pytest.fixture
def mock_llm_port() -> MockLLMPort:
    return MockLLMPort()


@pytest.fixture
def prompt_dir() -> Path:
    return Path(__file__).resolve().parents[3] / "prompts"


@pytest.fixture
def sample_case_detail() -> CaseDetail:
    return CaseDetail(
        client_name="Empresa ABC",
        sector_description="Manufacturing company",
        payment_history_pattern="DELAYED_30",
        invoices=[
            {
                "folio": "INV-001",
                "amount": 50000.0,
                "due_date": "2026-07-01",
                "days_overdue": 30,
                "status": "OVERDUE",
            }
        ],
        payments=[
            {
                "amount": 10000.0,
                "payment_date": "2026-06-15",
                "method": "TRANSFER",
            }
        ],
        score_value=65.0,
        score_category="medium",
        communications=[
            {
                "channel": "email",
                "tone": "formal",
                "draft_text": "Previous draft text",
                "status": "draft",
                "created_at": "2026-07-20T10:00:00",
            }
        ],
    )


class TestCommunicationDraftService:
    """Tests for CommunicationDraftService."""

    def test_load_template_success(self, mock_llm_port: MockLLMPort, prompt_dir: Path) -> None:
        """Template loads correctly from known path."""
        service = CommunicationDraftService(
            llm_port=mock_llm_port,
            prompt_dir=prompt_dir,
            model="test-model",
        )
        assert "{client_name}" in service._template
        assert "{channel}" in service._template
        assert "{tone}" in service._template

    def test_load_template_missing_raises_runtime_error(self, mock_llm_port: MockLLMPort) -> None:
        """Missing template raises RuntimeError with path during construction."""
        with pytest.raises(RuntimeError) as exc_info:
            CommunicationDraftService(
                llm_port=mock_llm_port,
                prompt_dir="/nonexistent/path",
                model="test-model",
            )
        assert "Prompt template not found" in str(exc_info.value)
        assert "nonexistent" in str(exc_info.value)

    def test_build_prompt_fills_all_placeholders(
        self,
        mock_llm_port: MockLLMPort,
        prompt_dir: Path,
        sample_case_detail: CaseDetail,
    ) -> None:
        """_build_prompt produces expected output with all placeholders filled."""
        service = CommunicationDraftService(
            llm_port=mock_llm_port,
            prompt_dir=prompt_dir,
            model="test-model",
        )
        prompt = service._build_prompt(sample_case_detail, Channel.EMAIL, Tone.FORMAL)

        # Check all placeholders are filled
        assert "Empresa ABC" in prompt
        assert "Manufacturing company" in prompt
        assert "DELAYED_30" in prompt
        assert "INV-001" in prompt
        assert "50000" in prompt
        assert "2026-07-01" in prompt
        assert "30" in prompt  # days_overdue
        assert "OVERDUE" in prompt
        assert "10000" in prompt
        assert "TRANSFER" in prompt
        assert "65.0" in prompt
        assert "medium" in prompt
        assert "email" in prompt
        assert "formal" in prompt
        assert "Previous draft text" in prompt
        assert "draft" in prompt
        # Template placeholders should be gone
        assert "{client_name}" not in prompt
        assert "{channel}" not in prompt
        assert "{tone}" not in prompt

    def test_build_prompt_with_no_invoices(
        self,
        mock_llm_port: MockLLMPort,
        prompt_dir: Path,
    ) -> None:
        """Handles empty invoices list."""
        case_detail = CaseDetail(
            client_name="Test Client",
            sector_description=None,
            payment_history_pattern="ON_TIME",
            invoices=[],
            payments=[],
            score_value=None,
            score_category=None,
            communications=[],
        )
        service = CommunicationDraftService(
            llm_port=mock_llm_port,
            prompt_dir=prompt_dir,
            model="test-model",
        )
        prompt = service._build_prompt(case_detail, Channel.WHATSAPP, Tone.URGENT)

        assert "No outstanding invoices." in prompt
        assert "No payment history." in prompt
        assert "No previous communications." in prompt
        assert "N/A" in prompt  # for missing sector_description, score_value, score_category

    def test_build_prompt_with_none_sector_description(
        self,
        mock_llm_port: MockLLMPort,
        prompt_dir: Path,
    ) -> None:
        """Handles None sector_description."""
        case_detail = CaseDetail(
            client_name="Test Client",
            sector_description=None,
            payment_history_pattern="ON_TIME",
            invoices=[],
            payments=[],
            score_value=None,
            score_category=None,
            communications=[],
        )
        service = CommunicationDraftService(
            llm_port=mock_llm_port,
            prompt_dir=prompt_dir,
            model="test-model",
        )
        prompt = service._build_prompt(case_detail, Channel.EMAIL, Tone.FORMAL)
        assert "N/A" in prompt

    @ pytest.mark.asyncio
    async def test_generate_calls_llm_with_correct_params(
        self,
        mock_llm_port: MockLLMPort,
        prompt_dir: Path,
        sample_case_detail: CaseDetail,
    ) -> None:
        """generate calls LLM with correct model and max_tokens."""
        service = CommunicationDraftService(
            llm_port=mock_llm_port,
            prompt_dir=prompt_dir,
            model="test-model",
        )
        result = await service.generate(sample_case_detail, Channel.PHONE, Tone.FIRM)

        assert result == "Estimado cliente, le recordamos su saldo pendiente de $50,000."
        assert len(mock_llm_port.generate_calls) == 1
        prompt, model, max_tokens = mock_llm_port.generate_calls[0]
        assert model == "test-model"
        assert max_tokens == 512
        assert "Empresa ABC" in prompt
        assert "phone" in prompt  # channel value (lowercase)
        assert "firm" in prompt   # tone value (lowercase)

    @pytest.mark.asyncio
    async def test_generate_uses_default_model_from_settings(
        self,
        mock_llm_port: MockLLMPort,
        prompt_dir: Path,
        sample_case_detail: CaseDetail,
    ) -> None:
        """generate uses MODEL_COMMUNICATIONS from settings when model not provided."""
        # Import settings to check default
        from app.config import settings

        service = CommunicationDraftService(
            llm_port=mock_llm_port,
            prompt_dir=prompt_dir,
            model=None,  # Should default to settings.MODEL_COMMUNICATIONS
        )
        await service.generate(sample_case_detail, Channel.EMAIL, Tone.FORMAL)

        prompt, model, max_tokens = mock_llm_port.generate_calls[0]
        assert model == settings.MODEL_COMMUNICATIONS


class TestCaseDetailResponseToDomain:
    """Tests for case_detail_response_to_domain converter."""

    def test_converts_all_fields(self) -> None:
        """Converts CaseDetailResponse to internal CaseDetail correctly."""
        # Create mock response objects
        client_mock = MagicMock()
        client_mock.name = "Test Client"
        client_mock.sector_description = "Test Sector"
        client_mock.payment_history_pattern = "DELAYED_60"

        invoice_mock = MagicMock()
        invoice_mock.folio = "INV-001"
        invoice_mock.amount = 25000.0
        invoice_mock.due_date = "2026-06-15"
        invoice_mock.days_overdue = 45
        invoice_mock.status = "OVERDUE"

        payment_mock = MagicMock()
        payment_mock.amount = 5000.0
        payment_mock.payment_date = "2026-06-01"
        payment_mock.method = "CASH"

        score_mock = MagicMock()
        score_mock.score_value = 75.0
        score_mock.category = "high"

        comm_mock = MagicMock()
        comm_mock.channel = "email"
        comm_mock.tone = "formal"
        comm_mock.draft_text = "Test draft"
        comm_mock.status = "draft"
        comm_mock.created_at = "2026-07-20T10:00:00"

        response_mock = MagicMock()
        response_mock.client = client_mock
        response_mock.invoices = [invoice_mock]
        response_mock.payments = [payment_mock]
        response_mock.score = score_mock
        response_mock.communications = [comm_mock]

        result = case_detail_response_to_domain(response_mock)

        assert result.client_name == "Test Client"
        assert result.sector_description == "Test Sector"
        assert result.payment_history_pattern == "DELAYED_60"
        assert len(result.invoices) == 1
        assert result.invoices[0]["folio"] == "INV-001"
        assert result.invoices[0]["amount"] == 25000.0
        assert len(result.payments) == 1
        assert result.payments[0]["amount"] == 5000.0
        assert result.score_value == 75.0
        assert result.score_category == "high"
        assert len(result.communications) == 1
        assert result.communications[0]["channel"] == "email"

    def test_handles_none_score(self) -> None:
        """Handles None score in response."""
        client_mock = MagicMock()
        client_mock.name = "Test Client"
        client_mock.sector_description = None
        client_mock.payment_history_pattern = "ON_TIME"

        response_mock = MagicMock()
        response_mock.client = client_mock
        response_mock.invoices = []
        response_mock.payments = []
        response_mock.score = None
        response_mock.communications = []

        result = case_detail_response_to_domain(response_mock)

        assert result.score_value is None
        assert result.score_category is None

    def test_handles_empty_lists(self) -> None:
        """Handles empty invoices, payments, communications."""
        client_mock = MagicMock()
        client_mock.name = "Test Client"
        client_mock.sector_description = "Test"
        client_mock.payment_history_pattern = "ON_TIME"

        response_mock = MagicMock()
        response_mock.client = client_mock
        response_mock.invoices = []
        response_mock.payments = []
        response_mock.score = None
        response_mock.communications = []

        result = case_detail_response_to_domain(response_mock)

        assert result.invoices == []
        assert result.payments == []
        assert result.communications == []
