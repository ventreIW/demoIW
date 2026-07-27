"""Manual verification that LLM enrichment runs against a real model (s4.8).

Drives ``LLMEnrichmentService`` directly — no DB, no server. Prints before/after
company names so a human can confirm the AI actually ran and the output reads as
plausible Mexican companies. Also exercises a >20-client batch boundary.

Usage (from backend/, with the venv active and OPENROUTER_API_KEY set):

    python scripts/verify_enrichment.py                # uses MODEL_DATA_ENRICHMENT
    python scripts/verify_enrichment.py openai/gpt-4o-mini   # override the model
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pandas as pd

from app.adapters.llm.openrouter_adapter import OpenRouterAdapter
from app.application.services.llm_enrichment_service import LLMEnrichmentService
from app.config import settings
from app.domain.value_objects.raw_dataset import RawDataset
from app.ports.llm_port import ILLMPort

PROMPT_DIR = Path(__file__).resolve().parents[2] / "prompts"


class _CountingLLM(ILLMPort):
    """Wraps a real ILLMPort and counts calls, to prove batching."""

    def __init__(self, inner: ILLMPort) -> None:
        self._inner = inner
        self.calls = 0

    async def generate(self, prompt: str, model: str, max_tokens: int = 512) -> str:
        self.calls += 1
        # Reasoning models spend tokens before emitting JSON — give them room.
        return await self._inner.generate(prompt, model=model, max_tokens=2048)

    async def query(self, system_prompt: str, user_message: str, model: str) -> str:
        return await self._inner.query(system_prompt, user_message, model=model)


def _dataset(names: list[str], sector: str) -> RawDataset:
    clients = pd.DataFrame({"name": names, "sector": [sector] * len(names)})
    return RawDataset(clients=clients, invoices=pd.DataFrame(), payments=pd.DataFrame())


async def main() -> int:
    model = sys.argv[1] if len(sys.argv) > 1 else settings.MODEL_DATA_ENRICHMENT
    if not settings.OPENROUTER_API_KEY:
        print("OPENROUTER_API_KEY is empty — set it in backend/.env first.")
        return 1
    print(f"model: {model}\n")

    adapter = OpenRouterAdapter(
        api_key=settings.OPENROUTER_API_KEY, base_url=settings.OPENROUTER_BASE_URL
    )
    counting = _CountingLLM(adapter)
    service = LLMEnrichmentService(llm_port=counting, prompt_dir=PROMPT_DIR)

    # Run 1 — 3 Faker-style names, before/after.
    faker_names = ["Hernández y Asociados S.A.", "Grupo Faker 12", "Test Corp"]
    ds = _dataset(faker_names, "retail")
    print("before:", faker_names)
    after: list[str] = faker_names
    run1_ok = False
    try:
        outcome = await service.enrich(ds, model=model)
        after = outcome.dataset.clients["name"].tolist()
        descs = outcome.dataset.clients["sector_description"].tolist()
        print("after :", after)
        print("desc  :", descs)
        print(f"enriched={outcome.enriched}  names_changed={after != faker_names}\n")
        run1_ok = outcome.enriched and after != faker_names
    except Exception as exc:  # noqa: BLE001 — evidence script, surface any provider hiccup
        print(f"run 1 raised: {exc!r}\n")

    # Space calls to stay under the free-tier per-minute limit.
    await asyncio.sleep(5)

    # Run 2 — 25 clients, confirm the batch boundary (>20 => 2 calls).
    counting.calls = 0
    big = _dataset([f"Empresa Faker {i}" for i in range(25)], "manufacturing")
    calls = 0
    try:
        outcome2 = await service.enrich(big, model=model)
        calls = counting.calls
        populated = int(outcome2.dataset.clients["sector_description"].notna().sum())
        print(
            f"batch run: 25 clients, llm_calls={calls}, "
            f"enriched={outcome2.enriched}, sector_description_populated={populated}/25"
        )
    except Exception as exc:  # noqa: BLE001
        print(f"run 2 raised: {exc!r}")

    print("\nRESULT:", "PASS" if run1_ok else "CHECK OUTPUT ABOVE")
    return 0 if run1_ok else 2


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
