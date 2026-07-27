"""M4 in-process E2E: the full intelligence path across story boundaries.

generate -> score+persist -> prioritized -> rescore-on-contact, driven through the
real ASGI app and real repositories (SQLite in-memory via the `client` fixture).
Unit tests mock repositories; this exercises the actual contract seams between
s4.2/s4.3 (scoring), s4.9/s4.10 (persistence), s4.5 (prioritization) and s4.6
(rescore) — the mismatches M4 exists to catch.

NOTE: the epic's M4 gate additionally requires a run against **real PostgreSQL**.
This SQLite path verifies the API/contract seams; the Postgres run (FK enforcement,
type coercion) remains an environment-dependent step documented at epic close.
"""

import pytest
from httpx import AsyncClient

from app.container import get_llm_port
from app.domain.exceptions import ExternalServiceError
from app.main import app
from app.ports.llm_port import ILLMPort


class _NoLLM(ILLMPort):
    """Stub LLM so /generate degrades gracefully (enriched=false) without network."""

    async def generate(self, prompt: str, model: str, max_tokens: int = 512) -> str:
        raise ExternalServiceError("no LLM in E2E")

    async def query(self, system_prompt: str, user_message: str, model: str) -> str:
        raise ExternalServiceError("no LLM in E2E")


@pytest.mark.anyio
async def test_full_intelligence_path(client: AsyncClient) -> None:
    app.dependency_overrides[get_llm_port] = lambda: _NoLLM()
    try:
        # 1. Generate a scenario (enrichment degrades — no LLM — but data persists).
        gen = await client.post(
            "/api/v1/scenarios/generate",
            json={
                "seed": 42,
                "sector": "retail",
                "client_count": 120,
                "invoice_volume": 3.0,
                "amount_mean": 10000.0,
                "amount_std": 3000.0,
                # reference_date left None: pinning a date currently crashes scenario
                # persistence (date not JSON-serializable in the `parameters` column).
                # Pre-existing generation-layer bug parked at M4 — out of scope here.
                "reference_date": None,
            },
        )
        assert gen.status_code == 201, gen.text
        assert gen.json()["enriched"] is False  # degraded but generated

        active = await client.get("/api/v1/scenarios/active")
        assert active.status_code == 200
        sid = active.json()["id"]

        # 2. Score + persist.
        score = await client.post(f"/api/v1/scenarios/{sid}/score")
        assert score.status_code == 201, score.text
        scored = score.json()["scored_count"]
        assert scored > 0

        # Idempotent re-score persists no duplicates.
        again = await client.post(f"/api/v1/scenarios/{sid}/score")
        assert again.json()["already_persisted"] is True
        assert again.json()["scored_count"] == scored

        # 3. Prioritized list.
        pri = await client.get(f"/api/v1/scenarios/{sid}/prioritized")
        assert pri.status_code == 200, pri.text
        cases = pri.json()["cases"]
        assert len(cases) > 0
        assert pri.json()["pareto_subset"]  # non-empty subset
        target_client = cases[0]["client_id"]

        # 4. Record contact -> rescore.
        res = await client.post(
            f"/api/v1/scenarios/{sid}/clients/{target_client}/rescore",
            json={"contact_result": "promise_to_pay"},
        )
        assert res.status_code == 200, res.text
        assert len(res.json()["cases"]) > 0
    finally:
        app.dependency_overrides.pop(get_llm_port, None)
