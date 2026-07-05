import json
import pytest
import respx
import httpx
from app.adapters.llm.openrouter_adapter import OpenRouterAdapter
from app.domain.exceptions import ExternalServiceError


@respx.mock
async def test_generate_returns_content():
    # Arrange
    mock_route = respx.post("https://openrouter.ai/api/v1/chat/completions").mock(
        return_value=httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": "Hello, world!"}}],
                "usage": {"prompt_tokens": 5, "completion_tokens": 3},
            },
        )
    )
    adapter = OpenRouterAdapter(api_key="test-key", base_url="https://openrouter.ai/api/v1")

    # Act
    result = await adapter.generate("Say hello", model="test-model")

    # Assert
    assert result == "Hello, world!"
    assert mock_route.called
    # Verify request payload
    request = mock_route.calls[0].request
    assert json.loads(request.content) == {
        "model": "test-model",
        "messages": [{"role": "user", "content": "Say hello"}],
        "max_tokens": 512,
    }


@respx.mock
async def test_query_returns_content():
    # Arrange
    mock_route = respx.post("https://openrouter.ai/api/v1/chat/completions").mock(
        return_value=httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": "Answer"}}],
                "usage": {"prompt_tokens": 7, "completion_tokens": 4},
            },
        )
    )
    adapter = OpenRouterAdapter(api_key="test-key", base_url="https://openrouter.ai/api/v1")

    # Act
    result = await adapter.query(
        system_prompt="You are helpful.", user_message="What is 2+2?", model="test-model"
    )

    # Assert
    assert result == "Answer"
    assert mock_route.called
    # Verify request payload
    request = mock_route.calls[0].request
    assert json.loads(request.content) == {
        "model": "test-model",
        "messages": [
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "What is 2+2?"},
        ],
        "max_tokens": 1024,
    }