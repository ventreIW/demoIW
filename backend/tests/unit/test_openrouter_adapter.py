import json
from unittest.mock import patch

import httpx
import pytest
import respx

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


@respx.mock
async def test_retries_on_503_success_on_third_attempt():
    # Arrange
    # Simulate two 503 responses then a 200
    route = respx.post("https://openrouter.ai/api/v1/chat/completions").mock(
        side_effect=[
            httpx.Response(503),
            httpx.Response(503),
            httpx.Response(
                200,
                json={
                    "choices": [{"message": {"content": "Success after retries"}}],
                    "usage": {"prompt_tokens": 5, "completion_tokens": 3},
                },
            ),
        ]
    )
    adapter = OpenRouterAdapter(api_key="test-key", base_url="https://openrouter.ai/api/v1")

    # Act
    result = await adapter.generate("test prompt", model="test-model")

    # Assert
    assert result == "Success after retries"
    assert route.called
    assert route.call_count == 3


@respx.mock
async def test_generate_raises_on_4xx_without_retry():
    # Simulate a 400 Bad Request
    route = respx.post("https://openrouter.ai/api/v1/chat/completions").mock(
        return_value=httpx.Response(400)
    )
    adapter = OpenRouterAdapter(api_key="test-key", base_url="https://openrouter.ai/api/v1")

    # Act & Assert
    with pytest.raises(ExternalServiceError):
        await adapter.generate("Bad request", model="test-model")

    # Assert: only one call was made (no retry)
    assert route.call_count == 1


@respx.mock
async def test_generate_logs_on_success():
    # Mock the logger to capture the call
    with patch("app.adapters.llm.openrouter_adapter.log") as mock_log:
        route = respx.post("https://openrouter.ai/api/v1/chat/completions").mock(
            return_value=httpx.Response(
                200,
                json={
                    "choices": [{"message": {"content": "Logged"}}],
                    "usage": {"prompt_tokens": 7, "completion_tokens": 5},
                },
            )
        )
        adapter = OpenRouterAdapter(api_key="test-key", base_url="https://openrouter.ai/api/v1")

        # Act
        result = await adapter.generate("Log me", model="test-model")

        # Assert
        assert result == "Logged"
        assert route.called
        # Verify that the log.info method was called with the expected event
        assert mock_log.info.called
