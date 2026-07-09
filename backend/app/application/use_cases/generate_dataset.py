from datetime import date

from pydantic import BaseModel, Field

from app.domain.enums import Sector
from app.domain.value_objects.generation_params import GenerationParams
from app.adapters.dataset.procedural_generator import ProceduralGenerator
from app.application.services.llm_enrichment_service import LLMEnrichmentService
from app.domain.value_objects.raw_dataset import RawDataset


class GenerateDataset:
    def __init__(self, enrichment_service: LLMEnrichmentService) -> None:
        self._enrichment_service = enrichment_service

    async def execute(self, params: GenerationParams, model: str) -> RawDataset:
        # Step 1: Generate procedural dataset using the provided parameters.
        generator = ProceduralGenerator(params)
        raw_dataset = generator.generate()

        # Step 2: Enrich the dataset using the LLM service.
        enriched_dataset = await self._enrichment_service.enrich(
            raw_dataset, model
        )
        return enriched_dataset
