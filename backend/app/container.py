from pathlib import Path

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.llm.openrouter_adapter import OpenRouterAdapter
from app.adapters.persistence.sqlalchemy_client_repo import (
    SQLAlchemyClientRepository,
)
from app.adapters.persistence.sqlalchemy_invoice_repo import (
    SQLAlchemyInvoiceRepository,
)
from app.adapters.persistence.sqlalchemy_payment_repo import (
    SQLAlchemyPaymentRepository,
)
from app.adapters.persistence.sqlalchemy_scenario_repo import (
    SQLAlchemyScenarioRepository,
)
from app.application.services.llm_enrichment_service import LLMEnrichmentService
from app.application.use_cases.generate_dataset import GenerateDataset
from app.application.use_cases.prioritize_scenario import PrioritizeScenario
from app.config import settings
from app.infrastructure.database import get_session
from app.ports.llm_port import ILLMPort
from app.ports.repositories import (
    IClientRepository,
    IInvoiceRepository,
    IPaymentRepository,
    IScenarioRepository,
)


async def get_scenario_repo(
    session: AsyncSession = Depends(get_session),
) -> IScenarioRepository:
    """Dependency that provides an IScenarioRepository implementation."""
    return SQLAlchemyScenarioRepository(session)


async def get_client_repo(
    session: AsyncSession = Depends(get_session),
) -> IClientRepository:
    """Dependency that provides an IClientRepository implementation."""
    return SQLAlchemyClientRepository(session)


async def get_invoice_repo(
    session: AsyncSession = Depends(get_session),
) -> IInvoiceRepository:
    """Dependency that provides an IInvoiceRepository implementation."""
    return SQLAlchemyInvoiceRepository(session)


async def get_payment_repo(
    session: AsyncSession = Depends(get_session),
) -> IPaymentRepository:
    """Dependency that provides an IPaymentRepository implementation."""
    return SQLAlchemyPaymentRepository(session)


async def get_llm_port() -> ILLMPort:
    """Dependency that provides an ILLMPort implementation."""
    return OpenRouterAdapter(
        api_key=settings.OPENROUTER_API_KEY,
        base_url=settings.OPENROUTER_BASE_URL,
    )


async def get_enrichment_service(
    llm_port: ILLMPort = Depends(get_llm_port),
) -> LLMEnrichmentService:
    """Dependency that provides an LLMEnrichmentService instance."""
    # Assuming prompts directory is located at <project_root>/prompts
    prompt_dir = Path(__file__).resolve().parents[2] / "prompts"
    return LLMEnrichmentService(
        llm_port=llm_port,
        prompt_dir=prompt_dir,
    )


async def get_generate_dataset_use_case(
    enrichment_service: LLMEnrichmentService = Depends(get_enrichment_service),
    scenario_repo: IScenarioRepository = Depends(get_scenario_repo),
    client_repo: IClientRepository = Depends(get_client_repo),
    invoice_repo: IInvoiceRepository = Depends(get_invoice_repo),
    payment_repo: IPaymentRepository = Depends(get_payment_repo),
) -> GenerateDataset:
    """Dependency that provides a GenerateDataset use case instance."""
    return GenerateDataset(
        enrichment_service=enrichment_service,
        scenario_repo=scenario_repo,
        client_repo=client_repo,
        invoice_repo=invoice_repo,
        payment_repo=payment_repo,
    )


async def get_prioritize_scenario_use_case() -> PrioritizeScenario:
    """Dependency that provides a PrioritizeScenario use case instance."""
    return PrioritizeScenario()
