from __future__ import annotations

import json
import logging
from pathlib import Path

import numpy as np
import pandas as pd

from app.domain.exceptions import ExternalServiceError
from app.domain.value_objects.raw_dataset import RawDataset
from app.ports.llm_port import ILLMPort

log = logging.getLogger(__name__)


class LLMEnrichmentService:
    """
    Service that enriches a RawDataset with LLM-generated company names and sector descriptions.
    """

    DEFAULT_BATCH_SIZE = 20

    def __init__(
        self, llm_port: ILLMPort, prompt_dir: Path | str, batch_size: int = DEFAULT_BATCH_SIZE
    ):
        self._llm = llm_port
        self._prompt_dir = Path(prompt_dir)
        self._batch_size = batch_size
        # Load the template once
        self._template = self._load_template()

    def _load_template(self) -> str:
        template_path = self._prompt_dir / "data_enrichment" / "v1_company_description.txt"
        try:
            return template_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            raise RuntimeError(f"Prompt template not found at {template_path}")

    async def enrich(self, raw_dataset: RawDataset, model: str) -> RawDataset:
        """
        Enrich the client data in the RawDataset using the LLM.
        Returns a new RawDataset with enriched client data.
        """
        # Work on a copy to avoid mutating the frozen RawDataset
        clients = raw_dataset.clients.copy()
        # If no clients, return early
        if clients.empty:
            return RawDataset(
                clients=clients,
                invoices=raw_dataset.invoices,
                payments=raw_dataset.payments,
            )

        # Split into batches
        batches = [
            clients.iloc[i : i + self._batch_size] for i in range(0, len(clients), self._batch_size)
        ]

        enriched_dfs = []
        for batch in batches:
            try:
                enriched_batch = await self._enrich_batch(batch, model)
                enriched_dfs.append(enriched_batch)
            except (ExternalServiceError, json.JSONDecodeError, ValueError):
                # Graceful degradation: keep original batch data (no enrichment)
                log.warning(
                    "LLM enrichment failed for a batch, falling back to original data",
                    extra={"batch_size": len(batch)},
                )
                # Still we need to ensure the sector_description column exists (with NaN)
                batch_with_nan = batch.copy()
                batch_with_nan["sector_description"] = np.nan
                enriched_dfs.append(batch_with_nan)

        # Combine enriched batches
        if enriched_dfs:
            enriched_clients = pd.concat(enriched_dfs, ignore_index=True)
        else:
            enriched_clients = clients

        # Ensure sector_description column exists (if all batches failed, it may be missing)
        if "sector_description" not in enriched_clients.columns:
            enriched_clients["sector_description"] = np.nan

        # Ensure we have the same columns as original (plus sector_description if any)
        # The enrichment should have added sector_description and possibly changed name.
        # Return a new RawDataset with enriched clients, original invoices and payments.
        return RawDataset(
            clients=enriched_clients,
            invoices=raw_dataset.invoices,
            payments=raw_dataset.payments,
        )

    async def _enrich_batch(self, batch: pd.DataFrame, model: str) -> pd.DataFrame:
        """
        Enrich a single batch of client data.
        Returns a DataFrame with enriched data (same index as batch).
        """
        # Build the prompt using the template
        # Use the first row's sector; assume homogeneous within batch (as per design)
        sector = batch["sector"].iloc[0] if not batch["sector"].empty else "unknown"
        count = len(batch)
        try:
            # The template has placeholders {sector} and {count}
            # Ensure we don't have other placeholders
            if "{sector}" not in self._template or "{count}" not in self._template:
                raise ValueError("Template missing required placeholders")
            # Use format to substitute placeholders
            prompt = self._template.format(sector=sector, count=count)
        except KeyError as e:
            # If the template has placeholders other than sector and count, raise a clear error
            raise ValueError(f"Template contains unknown placeholder: {e}")

        # Call the LLM
        llm_response = await self._llm.generate(prompt, model=model)

        # Parse the JSON response
        try:
            enriched_list = json.loads(llm_response)
        except json.JSONDecodeError:
            # If the response is not valid JSON, raise to trigger fallback
            log.debug(f"LLM returned malformed JSON: {llm_response}")
            raise

        # Validate that we got a list
        if not isinstance(enriched_list, list):
            raise ValueError("LLM response is not a JSON array")

        # Validate length matches batch size
        if len(enriched_list) != len(batch):
            log.warning(
                "LLM returned %d items, expected %d",
                len(enriched_list),
                len(batch),
            )
            # Fail loudly rather than pad or truncate: a length mismatch means the
            # LLM response cannot be aligned to the batch, so enriching would
            # silently attach the wrong description to the wrong client.
            raise ValueError("LLM response length mismatch")

        # Convert list of dicts to DataFrame
        enriched_df = pd.DataFrame(enriched_list)

        # Ensure required columns exist
        if "name" not in enriched_df.columns or "sector_description" not in enriched_df.columns:
            log.warning(
                "LLM response missing required fields: %s",
                enriched_df.columns.tolist(),
            )
            raise ValueError("LLM response missing 'name' or 'sector_description'")

        # At this point, we have valid enriched data.
        # We need to keep other columns from the original batch (e.g., sector, any other).
        # The enriched_df only has name and sector_description; we want to keep the rest.
        # So we'll create a copy of batch and update the two columns.
        # Align index to avoid mismatch.
        enriched_df = enriched_df.reset_index(drop=True)
        enriched_df.index = batch.index
        result = batch.copy()
        result["name"] = enriched_df["name"]
        result["sector_description"] = enriched_df["sector_description"]
        return result
