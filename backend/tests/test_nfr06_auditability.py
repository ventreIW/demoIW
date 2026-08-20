"""NFR-06 — auditability of generated communications.

    "Every communication draft generated and every send action must be stored with
     timestamp, operator identifier, model used, and prompt version."
     — governance/prd.md, NFR-06

NFR-01 through NFR-05 each acquired a verifying test during E7. NFR-06 acquired none, and
was consequently the only requirement in the PRD that nothing checked — which is why it
reached project close unimplemented (BUG-08). This is that test.
"""

import pytest
from httpx import AsyncClient

from app.config import settings
from app.container import get_llm_port
from app.main import app
from tests.test_e2e_demo_flow import GENERATION, _ScriptedLLM

#: Tests must not depend on whether the developer happens to have a .env. CI does not, so
#: MODEL_COMMUNICATIONS is "" there — which is how the blank-provenance defect was found.
TEST_MODEL = "test/communications-model"


@pytest.fixture
def _scripted(monkeypatch):
    monkeypatch.setattr(settings, "MODEL_COMMUNICATIONS", TEST_MODEL)
    app.dependency_overrides[get_llm_port] = lambda: _ScriptedLLM()
    yield
    app.dependency_overrides.pop(get_llm_port, None)


async def _case_ready(client: AsyncClient) -> tuple[str, str]:
    """Generate, activate and score a scenario; return (scenario_id, client_id)."""
    generated = await client.post("/api/v1/scenarios/generate", json=GENERATION)
    assert generated.status_code == 201, generated.text[:300]
    scenario_id = generated.json()["id"]
    await client.patch(f"/api/v1/scenarios/{scenario_id}/activate")
    await client.post(f"/api/v1/scenarios/{scenario_id}/score")
    queue = await client.get(f"/api/v1/scenarios/{scenario_id}/prioritized")
    cases = queue.json()["cases"]
    assert cases, "empty queue — the audit assertions would be vacuous"
    return scenario_id, cases[0]["client_id"]


@pytest.mark.anyio
async def test_draft_records_all_nfr06_provenance(client: AsyncClient, _scripted) -> None:
    """A draft must record timestamp, operator, model and prompt version."""
    scenario_id, client_id = await _case_ready(client)

    drafted = await client.post(
        f"/api/v1/scenarios/{scenario_id}/clients/{client_id}/communications",
        json={"channel": "email", "tone": "formal"},
        headers={"X-Operator-Id": "renata.ortiz"},
    )
    assert drafted.status_code == 201, drafted.text[:300]
    record = drafted.json()

    assert record["created_at"], "NFR-06: no draft timestamp"
    assert (
        record["operator_id"] == "renata.ortiz"
    ), f"NFR-06: operator identifier not recorded from the request: {record.get('operator_id')!r}"
    assert record["model_used"], "NFR-06: no model recorded — cannot say which model wrote this"
    assert record["prompt_version"], "NFR-06: no prompt version recorded"
    assert record["sent_at"] is None, "a draft that was never sent must not carry a send time"


@pytest.mark.anyio
async def test_operator_defaults_to_a_self_describing_placeholder(
    client: AsyncClient, _scripted
) -> None:
    """With no header, the operator must be recorded honestly rather than invented.

    This product has no authentication (B-17 is still under consideration). A plausible-looking
    username would falsify the audit record, which is worse than an obvious placeholder.
    """
    scenario_id, client_id = await _case_ready(client)

    drafted = await client.post(
        f"/api/v1/scenarios/{scenario_id}/clients/{client_id}/communications",
        json={"channel": "whatsapp", "tone": "firm"},
    )
    assert drafted.status_code == 201, drafted.text[:300]
    operator = drafted.json()["operator_id"]

    assert operator, "NFR-06: operator identifier is empty"
    assert "demo" in operator.lower(), (
        f"the default operator {operator!r} does not identify itself as a demo placeholder — "
        "an audit record with invented provenance is worse than none"
    )


@pytest.mark.anyio
async def test_send_stamps_sent_at_and_preserves_provenance(client: AsyncClient, _scripted) -> None:
    """The send action is the second thing NFR-06 names, and it needs its own timestamp."""
    scenario_id, client_id = await _case_ready(client)

    drafted = await client.post(
        f"/api/v1/scenarios/{scenario_id}/clients/{client_id}/communications",
        json={"channel": "email", "tone": "urgent"},
        headers={"X-Operator-Id": "nano"},
    )
    assert drafted.status_code == 201, drafted.text[:300]
    draft = drafted.json()
    comm_id = draft["id"]

    sent = await client.patch(
        f"/api/v1/scenarios/{scenario_id}/clients/{client_id}" f"/communications/{comm_id}/send"
    )
    assert sent.status_code == 200, sent.text[:300]
    record = sent.json()

    assert record["status"] == "sent"
    assert record["sent_at"], "NFR-06: the send action recorded no timestamp"
    assert (
        record["sent_at"] != record["created_at"]
    ), "sent_at duplicates created_at — the send action is not being timed independently"
    # Provenance must survive the status transition; the send handler rebuilds the entity.
    assert record["operator_id"] == "nano"
    assert record["model_used"] == draft["model_used"]
    assert record["prompt_version"] == draft["prompt_version"]


@pytest.mark.anyio
async def test_recorded_model_is_the_model_actually_configured(
    client: AsyncClient, _scripted
) -> None:
    """The recorded model must come from the service that used it, not a hardcoded string."""
    scenario_id, client_id = await _case_ready(client)
    drafted = await client.post(
        f"/api/v1/scenarios/{scenario_id}/clients/{client_id}/communications",
        json={"channel": "email", "tone": "formal"},
    )
    assert drafted.status_code == 201, drafted.text[:300]

    assert drafted.json()["model_used"] == TEST_MODEL, (
        "model_used does not match the configured communications model — it is being "
        "recorded from somewhere other than the service that made the call"
    )


@pytest.mark.anyio
async def test_unconfigured_model_records_unknown_not_blank(
    client: AsyncClient, monkeypatch
) -> None:
    """An unset model must record NULL, never an empty string.

    MODEL_COMMUNICATIONS defaults to "" when no .env is present — the state CI runs in. An
    empty string in an audit column occupies the field while carrying no information, which
    is the "invented provenance" failure this whole bug exists to prevent, in its quietest
    form. Unknown must read as unknown.
    """
    monkeypatch.setattr(settings, "MODEL_COMMUNICATIONS", "")
    app.dependency_overrides[get_llm_port] = lambda: _ScriptedLLM()
    try:
        scenario_id, client_id = await _case_ready(client)
        drafted = await client.post(
            f"/api/v1/scenarios/{scenario_id}/clients/{client_id}/communications",
            json={"channel": "email", "tone": "formal"},
        )
        assert drafted.status_code == 201, drafted.text[:300]
        assert drafted.json()["model_used"] is None, (
            f"an unconfigured model recorded {drafted.json()['model_used']!r} — "
            "a blank string in an audit column looks like a recorded value"
        )
    finally:
        app.dependency_overrides.pop(get_llm_port, None)
