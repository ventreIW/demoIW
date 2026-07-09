import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from app.domain.value_objects.raw_dataset import RawDataset
from app.ports.llm_port import ILLMPort


@pytest.mark.asyncio
async def test_enrich_with_mock_llm_returns_correct_enrichment():
    # Arrange
    # Mock the LLM port to return a valid JSON response
    mock_llm = AsyncMock(spec=ILLMPort)
    # Example response: two companies in the sector "Software"
    mock_llm.generate.return_value = json.dumps([
        {"name": "Innovatech Solutions", "sector_description": "Provides cutting-edge software development services."},
        {"name": "DataSys LLC", "sector_description": "Specializes in data analytics and business intelligence."}
    ])

    # Create a temporary directory for the prompt template
    with tempfile.TemporaryDirectory() as tmpdir:
        prompt_dir = Path(tmpdir)
        # Create the directory structure and the template file
        (prompt_dir / "data_enrichment").mkdir()
        template_file = prompt_dir / "data_enrichment" / "v1_company_description.txt"
        template_file.write_text(
            "You are generating fictional company data for a financial software demonstration.\n"
            "Generate names and descriptions for {count} companies in the {sector} sector operating in Mexico.\n\n"
            "Rules:\n"
            "- Names must be completely fictional — do not use real company names.\n"
            "- Descriptions must be one sentence, professional, and sector-appropriate.\n"
            "- Output ONLY a JSON array with no additional text:\n"
            "  [{\"name\": \"...\", \"sector_description\": \"...\"}, ...]\n\n"
            "Sector: {sector}\n"
            "Count: {count}"
        )

        # Import the service (will fail until we implement it, but that's expected for the red phase)
        from app.application.services.llm_enrichment_service import LLMEnrichmentService

        service = LLMEnrichmentService(llm_port=mock_llm, prompt_dir=prompt_dir)

        # Create a RawDataset with two clients (to match the mock response)
        clients_data = [
            {"name": "Acme Corporation", "sector": "Software"},
            {"name": "Beta LLC", "sector": "Software"}
        ]
        # We need to create a DataFrame for clients; the other DataFrames can be empty
        import pandas as pd
        clients_df = pd.DataFrame(clients_data)
        # For simplicity, we leave invoices and payments empty
        raw_dataset = RawDataset(
            clients=clients_df,
            invoices=pd.DataFrame(),
            payments=pd.DataFrame()
        )

        # Act
        enriched_dataset = await service.enrich(raw_dataset, model="test-model")

        # Assert
        # Check that the LLM generate method was called once (since we have 2 clients and batch size 20)
        assert mock_llm.generate.call_count == 1
        # Check the arguments passed to generate
        call_args = mock_llm.generate.call_args
        assert call_args is not None
        # The prompt should contain the template with the filled in sector and count
        prompt_arg = call_args[0][0]  # first positional argument is the prompt
        assert "Generate names and descriptions for 2 companies in the Software sector" in prompt_arg
        assert "Output ONLY a JSON array" in prompt_arg

        # Check the enriched dataset
        assert len(enriched_dataset.clients) == 2
        # The names should have been replaced
        assert enriched_dataset.clients.iloc[0]["name"] == "Innovatech Solutions"
        assert enriched_dataset.clients.iloc[1]["name"] == "DataSys LLC"
        # The sector_description should be added
        assert "sector_description" in enriched_dataset.clients.columns
        assert enriched_dataset.clients.iloc[0]["sector_description"] == "Provides cutting-edge software development services."
        assert enriched_dataset.clients.iloc[1]["sector_description"] == "Specializes in data analytics and business intelligence."
        # The sector should remain unchanged
        assert enriched_dataset.clients.iloc[0]["sector"] == "Software"
        assert enriched_dataset.clients.iloc[1]["sector"] == "Software"


@pytest.mark.asyncio
async def test_enrich_with_mock_llm_malformed_json_fallback_to_original():
    # Arrange
    mock_llm = AsyncMock(spec=ILLMPort)
    # Return malformed JSON (missing closing bracket)
    mock_llm.generate.return_value = "{ \"name\": \"Test\""

    with tempfile.TemporaryDirectory() as tmpdir:
        prompt_dir = Path(tmpdir)
        (prompt_dir / "data_enrichment").mkdir()
        template_file = prompt_dir / "data_enrichment" / "v1_company_description.txt"
        template_file.write_text(
            "You are generating fictional company data for a financial software demonstration.\n"
            "Generate names and descriptions for {count} companies in the {sector} sector operating in Mexico.\n\n"
            "Rules:\n"
            "- Names must be completely fictional — do not use real company names.\n"
            "- Descriptions must be one sentence, professional, and sector-appropriate.\n"
            "- Output ONLY a JSON array with no additional text:\n"
            "  [{\"name\": \"...\", \"sector_description\": \"...\"}, ...]\n\n"
            "Sector: {sector}\n"
            "Count: {count}"
        )

        from app.application.services.llm_enrichment_service import LLMEnrichmentService

        service = LLMEnrichmentService(llm_port=mock_llm, prompt_dir=prompt_dir)

        # Original data
        clients_data = [
            {"name": "Original Corp", "sector": "Software"},
            {"name": "Another LLC", "sector": "Software"}
        ]
        import pandas as pd
        clients_df = pd.DataFrame(clients_data)
        raw_dataset = RawDataset(
            clients=clients_df,
            invoices=pd.DataFrame(),
            payments=pd.DataFrame()
        )
        # Keep a copy to compare later
        original_clients = raw_dataset.clients.copy()

        # Act
        enriched_dataset = await service.enrich(raw_dataset, model="test-model")

        # Assert
        # LLM generate called once (batch size 20, 2 clients)
        assert mock_llm.generate.call_count == 1
        # sector_description column should exist (added for all rows)
        assert "sector_description" in enriched_dataset.clients.columns
        # Names should remain unchanged (fallback)
        pd.testing.assert_frame_equal(enriched_dataset.clients[["name", "sector"]], original_clients[["name", "sector"]])
        # sector_description should be NaN/None for all rows (since enrichment failed)
        assert enriched_dataset.clients["sector_description"].isna().all()
        # Ensure other tables unchanged (they were empty)
        assert enriched_dataset.invoices.equals(raw_dataset.invoices)
        assert enriched_dataset.payments.equals(raw_dataset.payments)