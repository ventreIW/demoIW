# Integration Test Patterns with Mocked External Services

## Purpose
Document patterns for writing integration tests that exercise real code paths while mocking external HTTP services (LLMs, payment APIs, etc.).

## LLM Mocking with `respx`

Follow the pattern from `tests/unit/test_openrouter_adapter.py`:

```python
import pytest
import respx
import httpx
from httpx import AsyncClient

@pytest.mark.anyio
@respx.mock
async def test_generate_scenario_valid(client: AsyncClient) -> None:
    # Arrange: Mock LLM response
    mock_llm_response = [
        {"name": "Enriched Client 1", "sector_description": "A retail company in Mexico."},
        {"name": "Enriched Client 2", "sector_description": "A retail business operating in Mexico."},
    ]
    mock_route = respx.post("https://openrouter.ai/api/v1/chat/completions").mock(
        return_value=httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": str(mock_llm_response).replace("'", '"')}}],
                "usage": {"prompt_tokens": 100, "completion_tokens": 50},
            },
        )
    )

    # Act
    payload = {
        "seed": 42,
        "sector": "retail",
        "client_count": 2,
        "invoice_volume": 5.0,
        "amount_mean": 1000.0,
        "amount_std": 200.0,
    }
    response = await client.post("/api/v1/scenarios/generate", json=payload)

    # Assert
    assert response.status_code == 201
    assert mock_route.called
    # Verify response shape matches ScenarioSummary
    body = response.json()
    assert body["client_count"] == 2
    assert body["status"] == "active"
```

## Key Principles

1. **Mock at HTTP layer** - Use `respx.post("https://api.example.com/...")` not `AsyncMock` on the adapter
2. **Realistic response shapes** - Match the provider's actual API schema (OpenRouter returns `choices[0].message.content`)
3. **Test both paths** - Success (200) and failure (500, 400, timeout)
4. **Verify mock called** - `assert mock_route.called` ensures the integration actually happened
5. **Use existing fixtures** - Reuse `client: AsyncClient` fixture from `conftest.py`

## Common Patterns

### Graceful Degradation Test
```python
@respx.mock
async def test_llm_failure_fallback(client: AsyncClient) -> None:
    respx.post("https://openrouter.ai/api/v1/chat/completions").mock(
        return_value=httpx.Response(500, json={"error": "Internal server error"})
    )
    response = await client.post("/api/v1/scenarios/generate", json=payload)
    # Service should still succeed with fallback data
    assert response.status_code == 201
```

### Validation Error Test
```python
async def test_invalid_params_returns_422(client: AsyncClient) -> None:
    payload = {"sector": "retail", "client_count": 3}  # missing seed
    response = await client.post("/api/v1/scenarios/generate", json=payload)
    assert response.status_code == 422
```

## Bug Detection Lesson

Integration tests with **real persistence** (not mocked repositories) catch bugs that unit tests miss.

Example: Unit test mocked `enriched_dataset.payments` with `payment_date` key, but the actual procedural generator produces `paid_date`. The unit test passed; the integration test failed with `KeyError: 'payment_date'`.

**Rule**: Ensure integration test mock data matches the **actual producer's output**, not the consumer's expectation. When producer (s3.1 procedural generator) and consumer (s3.4 generate_dataset) are owned by different developers/stories, this mismatch is a common bug source.

## File Locations

- LLM mocking pattern: `tests/unit/test_openrouter_adapter.py`
- Integration test example: `tests/integration/test_generate_scenario.py`
- Conftest fixture: `tests/conftest.py` (provides `client: AsyncClient`)