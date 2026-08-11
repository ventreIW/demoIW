"""Full-path live check for s6.3 (T6): HTTP → real model → answer. **Spends quota.**

Runs the actual endpoint against the **real** ``OpenRouterAdapter``, so the
narrative is written by the model that will write it in the demo. The stubbed
integration suite proves the contract; this proves the prose.

Cost is exactly **two** requests — one translate, one narrate. Enrichment is
stubbed out because dataset generation calls the LLM in batches of 20 and that
is not the path under test; leaving it live would spend five requests proving
nothing new.

Runs on **SQLite in-memory**, the same way the test suite does. The backend is
otherwise Postgres-only and this host has neither Postgres nor Docker (parked
2026-08-07), so this is as close to a real end-to-end as the environment
allows — and that limitation is recorded in the retrospective rather than
glossed over.

Usage::

    cd backend && .venv/bin/python scripts/verify_nl_query_e2e.py
"""

import asyncio
import json
import sys
from collections.abc import AsyncGenerator
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy.ext.asyncio import (  # noqa: E402
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.adapters.persistence import models as _models  # noqa: E402,F401
from app.application.services.llm_enrichment_service import LLMEnrichmentService  # noqa: E402
from app.container import get_enrichment_service  # noqa: E402
from app.infrastructure.database import Base, get_session  # noqa: E402
from app.main import app  # noqa: E402
from app.ports.llm_port import ILLMPort  # noqa: E402

QUESTION = "¿Cuánto está vencido por categoría de score?"


class NoEnrichment(ILLMPort):
    """Returns an empty enrichment array. Never used by the NL query path."""

    async def generate(self, prompt: str, model: str, max_tokens: int = 512) -> str:
        return "[]"

    async def query(self, system_prompt: str, user_message: str, model: str) -> str:
        return "[]"


async def main() -> int:
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def override_session() -> AsyncGenerator[AsyncSession, None]:
        async with maker() as session:
            yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_enrichment_service] = lambda: LLMEnrichmentService(
        llm_port=NoEnrichment(),
        prompt_dir=Path(__file__).resolve().parents[2] / "prompts",
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        gen = await client.post(
            "/api/v1/scenarios/generate",
            json={
                "seed": 42,
                "sector": "retail",
                "client_count": 60,
                "invoice_volume": 3.0,
                "amount_mean": 10000.0,
                "amount_std": 3000.0,
                "enrich": False,
            },
        )
        gen.raise_for_status()
        scenario_id = gen.json()["id"]
        await client.post(f"/api/v1/scenarios/{scenario_id}/score")

        print(f"question: {QUESTION}\n")
        response = await client.post(
            f"/api/v1/scenarios/{scenario_id}/query", json={"question": QUESTION}
        )
        body = response.json()
        print(f"status: {response.status_code}")
        print(f"answerable: {body['answerable']}")
        print(f"intent: {json.dumps(body.get('intent'), ensure_ascii=False)}")
        print(f"citation: {body['scenario']['name']} ({body['scenario']['id']})")
        print(f"scored_at: {body['scored_at']}")
        print("\nresult:")
        for point in (body.get("result") or {}).get("series", []):
            print(f"  {point['label']:>8}: {point['value']:>14,.2f}")
        print(f"\nnarrative:\n  {body.get('narrative')}")

        kpis = await client.get(f"/api/v1/scenarios/{scenario_id}/kpis")
        dashboard = {
            b["label"]: b["outstanding"] for b in kpis.json()["segmentation"]["score_category"]
        }
        answer = {p["label"]: p["value"] for p in (body.get("result") or {}).get("series", [])}
        print(f"\nagrees with /kpis: {answer == dashboard}")

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
