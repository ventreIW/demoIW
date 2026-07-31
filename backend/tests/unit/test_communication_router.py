"""Router/contract tests for POST /api/v1/scenarios/{scenario_id}/clients/{client_id}/communications"""

import uuid
import pytest
import respx
import httpx
from httpx import AsyncClient

from app.container import get_llm_port
from app.domain.exceptions import ExternalServiceError
from app.main import app
from app.ports.llm_port import ILLMPort


class _NoLLM(ILLMPort):
    """Stub LLM that raises ExternalServiceError to trigger graceful degradation."""

    async def generate(self, prompt: str, model: str, max_tokens: int = 512) -> str:
        raise ExternalServiceError("no LLM in test")

    async def query(self, system_prompt: str, user_message: str, model: str) -> str:
        raise ExternalServiceError("no LLM in test")


class _MockLLM(ILLMPort):
    """Mock LLM that returns a fixed response."""

    def __init__(self, response: str = "Estimado cliente, le recordamos su pago."):
        self.response = response

    async def generate(self, prompt: str, model: str, max_tokens: int = 512) -> str:
        return self.response

    async def query(self, system_prompt: str, user_message: str, model: str) -> str:
        return self.response


@pytest.fixture
def no_llm():
    """Override LLM port to raise ExternalServiceError (graceful degradation)."""
    app.dependency_overrides[get_llm_port] = lambda: _NoLLM()
    yield
    app.dependency_overrides.pop(get_llm_port, None)


@pytest.fixture
def mock_llm():
    """Override LLM port with a mock that returns a fixed response."""
    mock = _MockLLM()
    app.dependency_overrides[get_llm_port] = lambda: mock
    yield mock
    app.dependency_overrides.pop(get_llm_port, None)


async def _setup_scenario_with_client(client: AsyncClient) -> tuple[str, str]:
    """Helper to create a scenario with enough clients for scoring and return (scenario_id, client_id)."""
    # 1. Generate a scenario with enough clients for scoring (need >= 20 with outstanding)
    gen = await client.post(
        "/api/v1/scenarios/generate",
        json={
            "seed": 42,
            "sector": "retail",
            "client_count": 60,
            "invoice_volume": 3.0,
            "amount_mean": 10000.0,
            "amount_std": 3000.0,
            "reference_date": None,
        },
    )
    assert gen.status_code == 201, gen.text

    # 2. Get active scenario
    active = await client.get("/api/v1/scenarios/active")
    assert active.status_code == 200
    scenario_id = active.json()["id"]

    # 3. Score the scenario
    score = await client.post(f"/api/v1/scenarios/{scenario_id}/score")
    assert score.status_code == 201, score.text

    # 4. Get prioritized list to extract a client_id
    pri = await client.get(f"/api/v1/scenarios/{scenario_id}/prioritized")
    assert pri.status_code == 200, pri.text
    cases = pri.json()["cases"]
    assert len(cases) > 0
    client_id = cases[0]["client_id"]

    return scenario_id, client_id


@pytest.mark.anyio
@respx.mock
async def test_generate_communication_201_valid_input(
    client: AsyncClient, mock_llm: _MockLLM
) -> None:
    """POST with valid channel/tone returns 201 with CommunicationSummaryResponse shape."""
    # Setup
    scenario_id, client_id = await _setup_scenario_with_client(client)

    # Mock OpenRouter response for the communication endpoint
    respx.post("https://openrouter.ai/api/v1/chat/completions").mock(
        return_value=httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": "Estimado cliente, le recordamos su pago."}}],
                "usage": {"prompt_tokens": 50, "completion_tokens": 20},
            },
        )
    )

    # Act
    response = await client.post(
        f"/api/v1/scenarios/{scenario_id}/clients/{client_id}/communications",
        json={"channel": "email", "tone": "formal"},
    )

    # Assert
    assert response.status_code == 201
    body = response.json()

    # Verify CommunicationSummaryResponse shape
    assert "channel" in body
    assert body["channel"] == "email"
    assert "tone" in body
    assert body["tone"] == "formal"
    assert "draft_text" in body
    assert "Estimado cliente" in body["draft_text"]
    assert "status" in body
    assert body["status"] == "draft"
    assert "created_at" in body


@pytest.mark.anyio
@respx.mock
async def test_generate_communication_422_invalid_channel(
    client: AsyncClient, no_llm: None
) -> None:
    """POST with invalid channel returns 422."""
    scenario_id, client_id = await _setup_scenario_with_client(client)

    respx.post("https://openrouter.ai/api/v1/chat/completions").mock(
        return_value=httpx.Response(200, json={"choices": [{"message": {"content": "test"}}]})
    )

    response = await client.post(
        f"/api/v1/scenarios/{scenario_id}/clients/{client_id}/communications",
        json={"channel": "invalid_channel", "tone": "formal"},
    )

    assert response.status_code == 422


@pytest.mark.anyio
@respx.mock
async def test_generate_communication_422_invalid_tone(
    client: AsyncClient, no_llm: None
) -> None:
    """POST with invalid tone returns 422."""
    scenario_id, client_id = await _setup_scenario_with_client(client)

    respx.post("https://openrouter.ai/api/v1/chat/completions").mock(
        return_value=httpx.Response(200, json={"choices": [{"message": {"content": "test"}}]})
    )

    response = await client.post(
        f"/api/v1/scenarios/{scenario_id}/clients/{client_id}/communications",
        json={"channel": "email", "tone": "invalid_tone"},
    )

    assert response.status_code == 422


@pytest.mark.anyio
@respx.mock
async def test_generate_communication_422_missing_channel(
    client: AsyncClient, no_llm: None
) -> None:
    """POST with missing channel returns 422."""
    scenario_id, client_id = await _setup_scenario_with_client(client)

    respx.post("https://openrouter.ai/api/v1/chat/completions").mock(
        return_value=httpx.Response(200, json={"choices": [{"message": {"content": "test"}}]})
    )

    response = await client.post(
        f"/api/v1/scenarios/{scenario_id}/clients/{client_id}/communications",
        json={"tone": "formal"},
    )

    assert response.status_code == 422


@pytest.mark.anyio
@respx.mock
async def test_generate_communication_422_missing_tone(
    client: AsyncClient, no_llm: None
) -> None:
    """POST with missing tone returns 422."""
    scenario_id, client_id = await _setup_scenario_with_client(client)

    respx.post("https://openrouter.ai/api/v1/chat/completions").mock(
        return_value=httpx.Response(200, json={"choices": [{"message": {"content": "test"}}]})
    )

    response = await client.post(
        f"/api/v1/scenarios/{scenario_id}/clients/{client_id}/communications",
        json={"channel": "email"},
    )

    assert response.status_code == 422


@pytest.mark.anyio
@respx.mock
async def test_generate_communication_404_unknown_scenario(
    client: AsyncClient, no_llm: None
) -> None:
    """POST with unknown scenario_id returns 404."""
    fake_sid = str(uuid.uuid4())
    fake_cid = str(uuid.uuid4())

    respx.post("https://openrouter.ai/api/v1/chat/completions").mock(
        return_value=httpx.Response(200, json={"choices": [{"message": {"content": "test"}}]})
    )

    response = await client.post(
        f"/api/v1/scenarios/{fake_sid}/clients/{fake_cid}/communications",
        json={"channel": "email", "tone": "formal"},
    )

    assert response.status_code == 404


@pytest.mark.anyio
@respx.mock
async def test_generate_communication_404_unknown_client(
    client: AsyncClient, no_llm: None
) -> None:
    """POST with unknown client_id in valid scenario returns 404."""
    scenario_id, _ = await _setup_scenario_with_client(client)
    fake_cid = str(uuid.uuid4())

    respx.post("https://openrouter.ai/api/v1/chat/completions").mock(
        return_value=httpx.Response(200, json={"choices": [{"message": {"content": "test"}}]})
    )

    response = await client.post(
        f"/api/v1/scenarios/{scenario_id}/clients/{fake_cid}/communications",
        json={"channel": "email", "tone": "formal"},
    )

    assert response.status_code == 404


@pytest.mark.anyio
@respx.mock
async def test_generate_communication_all_channels(
    client: AsyncClient, mock_llm: _MockLLM
) -> None:
    """Test all valid channels work."""
    scenario_id, client_id = await _setup_scenario_with_client(client)

    respx.post("https://openrouter.ai/api/v1/chat/completions").mock(
        return_value=httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": "Draft message"}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5},
            },
        )
    )

    for channel in ["email", "phone", "whatsapp"]:
        response = await client.post(
            f"/api/v1/scenarios/{scenario_id}/clients/{client_id}/communications",
            json={"channel": channel, "tone": "formal"},
        )
        assert response.status_code == 201, f"Channel {channel} failed"
        assert response.json()["channel"] == channel


@pytest.mark.anyio
@respx.mock
async def test_generate_communication_all_tones(
    client: AsyncClient, mock_llm: _MockLLM
) -> None:
    """Test all valid tones work."""
    scenario_id, client_id = await _setup_scenario_with_client(client)

    respx.post("https://openrouter.ai/api/v1/chat/completions").mock(
        return_value=httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": "Draft message"}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5},
            },
        )
    )

    for tone in ["formal", "firm", "urgent"]:
        response = await client.post(
            f"/api/v1/scenarios/{scenario_id}/clients/{client_id}/communications",
            json={"channel": "email", "tone": tone},
        )
        assert response.status_code == 201, f"Tone {tone} failed"
        assert response.json()["tone"] == tone