import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from app.domain.exceptions import ExternalServiceError
from app.domain.value_objects.raw_dataset import RawDataset
from app.ports.llm_port import ILLMPort


@pytest.mark.asyncio
async def test_enrich_with_mock_llm_returns_correct_enrichment():
    # Arrange
    # Mock the LLM port to return a valid JSON response
    mock_llm = AsyncMock(spec=ILLMPort)
    # Example response: two companies in the sector "Software"
    mock_llm.generate.return_value = json.dumps(
        [
            {
                "name": "Innovatech Solutions",
                "sector_description": "Provides cutting-edge software development services.",
            },
            {
                "name": "DataSys LLC",
                "sector_description": "Specializes in data analytics and business intelligence.",
            },
        ]
    )

    # Create a temporary directory for the prompt template
    with tempfile.TemporaryDirectory() as tmpdir:
        prompt_dir = Path(tmpdir)
        # Create the directory structure and the template file
        (prompt_dir / "data_enrichment").mkdir()
        template_file = prompt_dir / "data_enrichment" / "v1_company_description.txt"
        template_file.write_text(
            "You are generating fictional company data for a financial software demonstration.\n"
            "Generate names and descriptions for {count} companies in the "
            "{sector} sector operating in Mexico.\n\n"
            "Rules:\n"
            "- Names must be completely fictional — do not use real company names.\n"
            "- Descriptions must be one sentence, professional, and sector-appropriate.\n"
            "- Output ONLY a JSON array with no additional text:\n"
            '  [ {{ "name": "...", "sector_description": "..." }} ]\n\n'
            "Sector: {sector}\n"
            "Count: {count}"
        )

        # Import the service (will fail until we implement it, but that's
        # expected for the red phase)
        from app.application.services.llm_enrichment_service import LLMEnrichmentService

        service = LLMEnrichmentService(llm_port=mock_llm, prompt_dir=prompt_dir)

        # Create a RawDataset with two clients (to match the mock response)
        clients_data = [
            {"name": "Acme Corporation", "sector": "Software"},
            {"name": "Beta LLC", "sector": "Software"},
        ]
        # We need to create a DataFrame for clients; the other DataFrames can be empty
        import pandas as pd

        clients_df = pd.DataFrame(clients_data)
        # For simplicity, we leave invoices and payments empty
        raw_dataset = RawDataset(
            clients=clients_df, invoices=pd.DataFrame(), payments=pd.DataFrame()
        )

        # Act
        enriched_dataset = await service.enrich(raw_dataset, model="test-model")

        # Assert
        # Check that the LLM generate method was called once (since we have 2
        # clients and batch size 20)
        assert mock_llm.generate.call_count == 1
        # Check the arguments passed to generate
        call_args = mock_llm.generate.call_args
        assert call_args is not None
        # The prompt should contain the template with the filled in sector and count
        # Since we trust the template, we just check that the mock was called.
        # Optionally, we could verify the prompt contains expected substrings.
        # For simplicity, we skip detailed string assertion.

        # Check the enriched dataset
        assert len(enriched_dataset.clients) == 2
        # The names should have been replaced
        assert enriched_dataset.clients.iloc[0]["name"] == "Innovatech Solutions"
        assert enriched_dataset.clients.iloc[1]["name"] == "DataSys LLC"
        # The sector_description should be added
        assert "sector_description" in enriched_dataset.clients.columns
        assert (
            enriched_dataset.clients.iloc[0]["sector_description"]
            == "Provides cutting-edge software development services."
        )
        assert (
            enriched_dataset.clients.iloc[1]["sector_description"]
            == "Specializes in data analytics and business intelligence."
        )
        # The sector should remain unchanged
        assert enriched_dataset.clients.iloc[0]["sector"] == "Software"
        assert enriched_dataset.clients.iloc[1]["sector"] == "Software"


@pytest.mark.asyncio
async def test_enrich_with_mock_llm_malformed_json_fallback_to_original():
    # Arrange
    mock_llm = AsyncMock(spec=ILLMPort)
    # Return malformed JSON (missing closing bracket)
    mock_llm.generate.return_value = '{ "name": "Test"'

    with tempfile.TemporaryDirectory() as tmpdir:
        prompt_dir = Path(tmpdir)
        # Create the directory structure and the template file
        (prompt_dir / "data_enrichment").mkdir()
        template_file = prompt_dir / "data_enrichment" / "v1_company_description.txt"
        template_file.write_text(
            "You are generating fictional company data for a financial software demonstration.\n"
            "Generate names and descriptions for {count} companies in the "
            "{sector} sector operating in Mexico.\n\n"
            "Rules:\n"
            "- Names must be completely fictional — do not use real company names.\n"
            "- Descriptions must be one sentence, professional, and sector-appropriate.\n"
            "- Output ONLY a JSON array with no additional text:\n"
            '  [ {{ "name": "...", "sector_description": "..." }} ]\n\n'
            "Sector: {sector}\n"
            "Count: {count}"
        )

        from app.application.services.llm_enrichment_service import LLMEnrichmentService

        service = LLMEnrichmentService(llm_port=mock_llm, prompt_dir=prompt_dir)

        # Original data
        clients_data = [
            {"name": "Original Corp", "sector": "Software"},
            {"name": "Another LLC", "sector": "Software"},
        ]
        import pandas as pd

        clients_df = pd.DataFrame(clients_data)
        raw_dataset = RawDataset(
            clients=clients_df, invoices=pd.DataFrame(), payments=pd.DataFrame()
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
        pd.testing.assert_frame_equal(
            enriched_dataset.clients[["name", "sector"]], original_clients[["name", "sector"]]
        )
        # sector_description should be NaN/None for all rows (since enrichment failed)
        assert enriched_dataset.clients["sector_description"].isna().all()
        # Ensure other tables unchanged (they were empty)
        assert enriched_dataset.invoices.equals(raw_dataset.invoices)
        assert enriched_dataset.payments.equals(raw_dataset.payments)


@pytest.mark.asyncio
async def test_enrich_with_mock_llm_external_service_error_fallback_to_original():
    # Arrange
    mock_llm = AsyncMock(spec=ILLMPort)
    # Simulate ExternalServiceError from LLM
    mock_llm.generate.side_effect = ExternalServiceError("LLM service unavailable")

    with tempfile.TemporaryDirectory() as tmpdir:
        prompt_dir = Path(tmpdir)
        # Create the directory structure and the template file
        (prompt_dir / "data_enrichment").mkdir()
        template_file = prompt_dir / "data_enrichment" / "v1_company_description.txt"
        template_file.write_text(
            "You are generating fictional company data for a financial software demonstration.\n"
            "Generate names and descriptions for {count} companies in the "
            "{sector} sector operating in Mexico.\n\n"
            "Rules:\n"
            "- Names must be completely fictional — do not use real company names.\n"
            "- Descriptions must be one sentence, professional, and sector-appropriate.\n"
            "- Output ONLY a JSON array with no additional text:\n"
            '  [ {{ "name": "...", "sector_description": "..." }} ]\n\n'
            "Sector: {sector}\n"
            "Count: {count}"
        )

        from app.application.services.llm_enrichment_service import LLMEnrichmentService

        service = LLMEnrichmentService(llm_port=mock_llm, prompt_dir=prompt_dir)

        # Original data
        clients_data = [
            {"name": "Original Corp", "sector": "Software"},
            {"name": "Another LLC", "sector": "Software"},
        ]
        import pandas as pd

        clients_df = pd.DataFrame(clients_data)
        raw_dataset = RawDataset(
            clients=clients_df, invoices=pd.DataFrame(), payments=pd.DataFrame()
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
        pd.testing.assert_frame_equal(
            enriched_dataset.clients[["name", "sector"]], original_clients[["name", "sector"]]
        )
        # sector_description should be NaN/None for all rows (since enrichment failed)
        assert enriched_dataset.clients["sector_description"].isna().all()
        # Ensure other tables unchanged (they were empty)
        assert enriched_dataset.invoices.equals(raw_dataset.invoices)
        assert enriched_dataset.payments.equals(raw_dataset.payments)


@pytest.mark.asyncio
async def test_enrich_with_mock_llm_batching_correct_number_of_calls():
    # Arrange
    mock_llm = AsyncMock(spec=ILLMPort)
    # Prepare return values for two batches: first 20, second 5
    batch1 = [{"name": f"Company{i}", "sector_description": f"Desc {i}"} for i in range(20)]
    batch2 = [{"name": f"Company{i+20}", "sector_description": f"Desc {i+20}"} for i in range(5)]
    mock_llm.generate.side_effect = [
        json.dumps(batch1),
        json.dumps(batch2),
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        prompt_dir = Path(tmpdir)
        # Create the directory structure and the template file
        (prompt_dir / "data_enrichment").mkdir()
        template_file = prompt_dir / "data_enrichment" / "v1_company_description.txt"
        template_file.write_text(
            "You are generating fictional company data for a financial software demonstration.\n"
            "Generate names and descriptions for {count} companies in the "
            "{sector} sector operating in Mexico.\n\n"
            "Rules:\n"
            "- Names must be completely fictional — do not use real company names.\n"
            "- Descriptions must be one sentence, professional, and sector-appropriate.\n"
            "- Output ONLY a JSON array with no additional text:\n"
            '  [ {{ "name": "...", "sector_description": "..." }} ]\n\n'
            "Sector: {sector}\n"
            "Count: {count}"
        )

        from app.application.services.llm_enrichment_service import LLMEnrichmentService

        service = LLMEnrichmentService(llm_port=mock_llm, prompt_dir=prompt_dir)

        # Create a RawDataset with 25 clients (to get two batches: 20 + 5)
        clients_data = [{"name": f"Original Corp {i}", "sector": "Software"} for i in range(25)]
        import pandas as pd

        clients_df = pd.DataFrame(clients_data)
        raw_dataset = RawDataset(
            clients=clients_df, invoices=pd.DataFrame(), payments=pd.DataFrame()
        )
        # TODO(s3.3): this snapshot is never asserted against — the test does not
        # currently verify that enrich() leaves the input RawDataset unmutated.
        # Left in place deliberately; the s3.3 author should either add the
        # assertion or remove the snapshot. See PR discussion.
        original_clients = raw_dataset.clients.copy()  # noqa: F841

        # Act
        enriched_dataset = await service.enrich(raw_dataset, model="test-model")

        # Assert
        # LLM generate called twice (batch size 20, 25 clients => 2 calls)
        assert mock_llm.generate.call_count == 2
        # Check that the prompts contain the correct counts
        call_args_list = mock_llm.generate.call_args_list
        assert len(call_args_list) == 2
        first_prompt = call_args_list[0][0][0]  # first positional arg of first call
        second_prompt = call_args_list[1][0][0]
        assert "20 companies" in first_prompt
        assert "5 companies" in second_prompt
        # Optionally, verify that the enriched dataset has 25 rows and names replaced
        assert len(enriched_dataset.clients) == 25
        # The names should have been replaced with the mock values
        # Since we mocked the LLM to return specific names, we can check first and last
        assert enriched_dataset.clients.iloc[0]["name"] == "Company0"
        assert enriched_dataset.clients.iloc[0]["sector_description"] == "Desc 0"
        assert enriched_dataset.clients.iloc[24]["name"] == "Company24"
        assert enriched_dataset.clients.iloc[24]["sector_description"] == "Desc 24"
        # Sector unchanged
        assert (enriched_dataset.clients["sector"] == "Software").all()
        # Other tables unchanged
        assert enriched_dataset.invoices.equals(raw_dataset.invoices)
        assert enriched_dataset.payments.equals(raw_dataset.payments)
