from pathlib import Path

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.llm.openrouter_adapter import OpenRouterAdapter
from app.adapters.persistence.sqlalchemy_client_repo import (
    SQLAlchemyClientRepository,
)
from app.adapters.persistence.sqlalchemy_communication_repo import (
    SQLAlchemyCommunicationRepository,
)
from app.adapters.persistence.sqlalchemy_contact_result_repo import (
    SQLAlchemyContactResultRepository,
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
from app.adapters.persistence.sqlalchemy_score_repo import (
    SQLAlchemyScoreRepository,
)
from app.application.services.case_aggregate_service import fetch_case_aggregate
from app.application.services.communication_draft_service import (
    CommunicationDraftService,
)
from app.application.services.llm_enrichment_service import LLMEnrichmentService
from app.application.use_cases.generate_communication_draft import (
    GenerateCommunicationDraft,
)
from app.application.use_cases.generate_dataset import GenerateDataset
from app.application.use_cases.prioritize_scenario import PrioritizeScenario
from app.application.use_cases.record_contact_result import RecordContactResult
from app.application.use_cases.rescore_scenario import RescoreScenario
from app.application.use_cases.score_and_persist_scenario import ScoreAndPersistScenario
from app.config import settings
from app.infrastructure.database import get_session
from app.ports.llm_port import ILLMPort
from app.ports.repositories import (
    IClientRepository,
    ICommunicationRepository,
    IContactResultRepository,
    IInvoiceRepository,
    IPaymentRepository,
    IScenarioRepository,
    IScoreRepository,
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


async def get_score_repo(
    session: AsyncSession = Depends(get_session),
) -> IScoreRepository:
    """Dependency that provides an IScoreRepository implementation."""
    return SQLAlchemyScoreRepository(session)


async def get_contact_result_repo(
    session: AsyncSession = Depends(get_session),
) -> IContactResultRepository:
    """Dependency that provides an IContactResultRepository implementation."""
    return SQLAlchemyContactResultRepository(session)


async def get_communication_repo(
    session: AsyncSession = Depends(get_session),
) -> ICommunicationRepository:
    """Dependency that provides an ICommunicationRepository implementation."""
    return SQLAlchemyCommunicationRepository(session)


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


async def get_draft_service(
    llm_port: ILLMPort = Depends(get_llm_port),
) -> CommunicationDraftService:
    """Dependency that provides a CommunicationDraftService instance."""
    prompt_dir = Path(__file__).resolve().parents[2] / "prompts"
    return CommunicationDraftService(
        llm_port=llm_port,
        prompt_dir=prompt_dir,
        model=settings.MODEL_COMMUNICATIONS,
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


async def get_score_and_persist_use_case(
    scenario_repo: IScenarioRepository = Depends(get_scenario_repo),
    score_repo: IScoreRepository = Depends(get_score_repo),
) -> ScoreAndPersistScenario:
    """Dependency that provides a ScoreAndPersistScenario use case instance."""
    return ScoreAndPersistScenario(scenario_repo=scenario_repo, score_repo=score_repo)


async def get_record_contact_result_use_case(
    scenario_repo: IScenarioRepository = Depends(get_scenario_repo),
    client_repo: IClientRepository = Depends(get_client_repo),
    contact_result_repo: IContactResultRepository = Depends(get_contact_result_repo),
) -> RecordContactResult:
    """Dependency that provides a RecordContactResult use case instance."""
    return RecordContactResult(
        scenario_repo=scenario_repo,
        client_repo=client_repo,
        contact_result_repo=contact_result_repo,
        rescore_use_case=RescoreScenario(),
    )


async def get_generate_communication_draft_use_case(
    scenario_repo: IScenarioRepository = Depends(get_scenario_repo),
    client_repo: IClientRepository = Depends(get_client_repo),
    invoice_repo: IInvoiceRepository = Depends(get_invoice_repo),
    payment_repo: IPaymentRepository = Depends(get_payment_repo),
    score_repo: IScoreRepository = Depends(get_score_repo),
    communication_repo: ICommunicationRepository = Depends(get_communication_repo),
    draft_service: CommunicationDraftService = Depends(get_draft_service),
) -> GenerateCommunicationDraft:
    """Dependency that provides a GenerateCommunicationDraft use case instance."""
    return GenerateCommunicationDraft(
        scenario_repo=scenario_repo,
        client_repo=client_repo,
        invoice_repo=invoice_repo,
        payment_repo=payment_repo,
        score_repo=score_repo,
        communication_repo=communication_repo,
        draft_service=draft_service,
    )


async def get_prioritize_scenario_use_case() -> PrioritizeScenario:
    """Dependency that provides a PrioritizeScenario use case instance."""
    return PrioritizeScenario()


async def get_rescore_scenario_use_case() -> RescoreScenario:
    """Dependency that provides a RescoreScenario use case instance."""
    return RescoreScenario()
