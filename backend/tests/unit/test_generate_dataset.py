from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest

from app.application.use_cases.generate_dataset import GenerateDataset
from app.application.services.llm_enrichment_service import LLMEnrichmentService
from app.domain.value_objects.raw_dataset import RawDataset
from app.domain.value_objects.generation_params import GenerationParams
from app.domain.enums import Sector


@pytest.mark.asyncio
async def test_generate_dataset_execute_calls_procedural_generator_and_llm_enrichment():
    # Arrange
    dummy_raw = RawDataset(
        clients=pd.DataFrame(),
        invoices=pd.DataFrame(),
        payments=pd.DataFrame(),
    )
    dummy_enriched = RawDataset(
        clients=pd.DataFrame(),
        invoices=pd.DataFrame(),
        payments=pd.DataFrame(),
    )

    mock_llm_enrichment_service = AsyncMock(spec=LLMEnrichmentService)
    mock_llm_enrichment_service.enrich.return_value = dummy_enriched

    params = GenerationParams(
        seed=42,
        sector=Sector.MANUFACTURING,
        client_count=10,
        invoice_volume=2.0,
        amount_mean=1000.0,
        amount_std=100.0,
        reference_date=None,
    )
    model = "test-model"

    use_case = GenerateDataset(enrichment_service=mock_llm_enrichment_service)

    with patch(
        "app.application.use_cases.generate_dataset.ProceduralGenerator"
    ) as mock_generator_cls:
        mock_generator_instance = MagicMock()
        mock_generator_instance.generate.return_value = dummy_raw
        mock_generator_cls.return_value = mock_generator_instance

        result = await use_case.execute(params, model)

        mock_generator_cls.assert_called_once_with(params)
        mock_generator_instance.generate.assert_called_once_with()

    mock_llm_enrichment_service.enrich.assert_awaited_once_with(dummy_raw, model)
    assert result is dummy_enriched
