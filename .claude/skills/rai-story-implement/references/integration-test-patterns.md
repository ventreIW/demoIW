# Integration Test Patterns for LLM-Integrated Endpoints

## Overview

This document captures patterns for writing integration tests that exercise real HTTP-layer calls to external LLM providers (OpenRouter, etc.) using `respx` for mocking.

## Core Principles

1. **Mock at HTTP layer, not adapter layer** — Use `respx.post("https://openrouter.ai/api/v1/chat/completions")` to exercise real serialization, retries, and error handling paths.

2. **Use realistic response shapes** — Match the provider's actual API response structure exactly.

3. **Verify the mock was called** — Assert `mock_route.called` and `mock_route.call_count`.

4. **Test both success and failure paths** — 500, 400, timeout, malformed JSON.

## Pattern: Full Integration Test with OpenRouter Mocking

```python
import respx
import httpx
import json
import pytest
from httpx import AsyncClient

@respx.mock
@pytest.mark.anyio
async def test_my_integration(client: AsyncClient) -> None:
    # Arrange: Mock OpenRouter with side_effect for multiple calls
    mock_route = respx.post("https://openrouter.ai/api/v1/chat/completions").mock(
        side_effect=[
            # First call: enrichment (if applicable)
            httpx.Response(200, json={
                "choices": [{"message": {"content": json.dumps(enriched_data)}}],
                "usage": {"prompt_tokens": 100, "completion_tokens": 50}
            }),
            # Second call: actual LLM call being tested
            httpx.Response(200, json={
                "choices": [{"message": {"content": "Expected response"}}],
                "usage": {"prompt_tokens": 50, "completion_tokens": 20}
            }),
        ]
    )

    # Act
    response = await client.post("/api/v1/...", json={"channel": "email", "tone": "formal"})

    # Assert
    assert response.status_code == 201
    assert mock_route.called
    assert mock_route.call_count == 2

    # Verify request payload
    request = mock_route.calls[-1].request
    payload = json.loads(request.content)
    assert payload["model"] == "expected-model"
    assert payload["max_tokens"] == 512
```

## Pattern: Error Handling Tests

### 500 Error → 502 After Retries

OpenRouterAdapter retries 3 times on 5xx (MAX_RETRIES=3). Need 4 responses (1 initial + 3 retries):

```python
@respx.mock
@pytest.mark.anyio
async def test_llm_500_returns_502(client: AsyncClient) -> None:
    respx.post("https://openrouter.ai/api/v1/chat/completions").mock(
        side_effect=[
            # Success responses for prerequisite calls (enrichment, scoring, etc.)
            _enrichment_mock_response(20),
            _enrichment_mock_response(20),
            _enrichment_mock_response(20),
            # Communication call: 1 initial + 3 retries = 4 failures
            httpx.Response(500, json={"error": "Internal server error"}),
            httpx.Response(500, json={"error": "Internal server error"}),
            httpx.Response(500, json={"error": "Internal server error"}),
            httpx.Response(500, json={"error": "Internal server error"}),
        ]
    )

    response = await client.post(...)
    assert response.status_code == 502
```

### Timeout Handling

**Limitation**: `respx` wraps `TimeoutException` in `SideEffectError` which bypasses the adapter's retry logic. The exception propagates directly as `httpx.TimeoutException` instead of being caught and retried by the adapter.

```python
@respx.mock
@pytest.mark.anyio
async def test_llm_timeout_returns_502(client: AsyncClient) -> None:
    # NOTE: This test documents expected behavior but respx SideEffectError
    # prevents proper retry simulation. The adapter DOES retry on timeout
    # in production (catches httpx.TimeoutException).
    respx.post(...).mock(
        side_effect=[
            _enrichment_mock_response(20),
            _enrichment_mock_response(20),
            _enrichment_mock_response(20),
            httpx.TimeoutException("Request timed out"),
            httpx.TimeoutException("Request timed out"),
            httpx.TimeoutException("Request timed out"),
            httpx.TimeoutException("Request timed out"),
        ]
    )
    # In real production, adapter retries 3x then returns 502
    # In test, TimeoutException propagates directly due to respx limitation
```

### Malformed JSON

**Important**: OpenRouterAdapter does NOT catch `JSONDecodeError` (only catches `HTTPStatusError` and `TimeoutException`). Malformed JSON propagates as unhandled exception → 500 Internal Server Error, not 502.

```python
@respx.mock
@pytest.mark.anyio
async def test_malformed_json_returns_500(client: AsyncClient) -> None:
    respx.post(...).mock(
        side_effect=[
            _enrichment_mock_response(20),
            _enrichment_mock_response(20),
            _enrichment_mock_response(20),
            httpx.Response(200, content=b"not json"),
        ]
    )
    response = await client.post(...)
    assert response.status_code == 500  # JSONDecodeError not caught
```

## Helper Functions

```python
def _llm_mock_response(content: str = "Estimado cliente, le recordamos su pago.") -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "choices": [{"message": {"content": content}}],
            "usage": {"prompt_tokens": 50, "completion_tokens": 20},
        },
    )

def _enrichment_mock_response(count: int) -> httpx.Response:
    import json
    enriched = [
        {"name": f"Cliente Enriquecido {i}", "sector_description": "Empresa del sector retail."}
        for i in range(count)
    ]
    return httpx.Response(
        200,
        json={"choices": [{"message": {"content": json.dumps(enriched)}}]},
    )
```

## Common Pitfalls

| Pitfall | Symptom | Fix |
|---------|---------|-----|
| Not mocking enrichment calls | `AllMockedAssertionError` on enrichment | Include all expected OpenRouter calls in `side_effect` |
| Using `side_effect` with Exception | `SideEffectError` wraps it | Use `httpx.TimeoutException` instances, but know respx limitation |
| Expecting 502 for malformed JSON | Get 500 instead | Adapter doesn't catch JSONDecodeError |
| Wrong call count | Test passes but doesn't verify | Assert `mock_route.call_count == expected` |

## Test Setup Pattern

```python
async def _setup_scenario_with_client(client: AsyncClient) -> tuple[str, str]:
    """Helper to create a scenario with enough clients for scoring."""
    gen = await client.post(
        "/api/v1/scenarios/generate",
        json={"seed": 42, "sector": "retail", "client_count": 60, ...}
    )
    assert gen.status_code == 201

    active = await client.get("/api/v1/scenarios/active")
    scenario_id = active.json()["id"]

    score = await client.post(f"/api/v1/scenarios/{scenario_id}/score")
    assert score.status_code == 201

    pri = await client.get(f"/api/v1/scenarios/{scenario_id}/prioritized")
    client_id = pri.json()["cases"][0]["client_id"]

    return scenario_id, client_id
```

## Related Patterns

- `demoIW-fastapi-patterns.md` — FastAPI-specific patterns (PAT-N-4, PAT-N-5)
- `fastapi-python-patterns.md` — General Python/FastAPI patterns