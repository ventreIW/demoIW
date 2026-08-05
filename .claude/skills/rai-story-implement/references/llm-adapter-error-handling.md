# LLM Adapter Error Handling Patterns

Patterns for hardening LLM adapters (OpenRouter, etc.) so provider failures degrade to `ExternalServiceError` → HTTP 502, not raw exceptions → 500.

## OpenRouterAdapter Hardening (S6.0)

### Two Known Failure Modes on Free Tier

| Failure | Raw Exception | Degraded To | HTTP Status |
|---------|---------------|-------------|-------------|
| Missing/empty `choices` in 200 response | `KeyError` / `IndexError` | `ExternalServiceError` | 502 |
| Request timeout (`ReadTimeout`, `ConnectTimeout`) | `httpx.TimeoutException` | `ExternalServiceError` | 502 |

### Implementation Pattern

Wrap response parsing in try/except **inside the retry loop**, before any retry logic:

```python
# Inside _call() retry loop
try:
    response = await self._client.post(...)
    if response.status_code in self._RETRY_STATUSES and attempt < self._MAX_RETRIES - 1:
        await asyncio.sleep(2**attempt)
        continue
    response.raise_for_status()
    data = response.json()
    self._log(model, data, time.monotonic() - start)
    
    # Parse with defensive checks
    try:
        content: str = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError) as e:
        raise ExternalServiceError(f"OpenRouter response missing expected content: {e}")
    return content

except httpx.TimeoutException as e:
    # Timeout (ReadTimeout, ConnectTimeout, etc.) - fail fast, NO retry
    raise ExternalServiceError(f"OpenRouter request timed out: {e}")

except httpx.HTTPStatusError as e:
    # Existing 5xx retry logic unchanged
    last_error = e
    if e.response.status_code not in self._RETRY_STATUSES:
        break
    await asyncio.sleep(2**attempt)
```

**Key points:**
- Catch `TimeoutException` (base class) **before** `HTTPStatusError` — timeout is not a 5xx, must not retry
- Fail fast on timeout: raise `ExternalServiceError` immediately, no exponential backoff
- Catch `KeyError`/`IndexError` on `data["choices"][0]["message"]["content"]` — free tier sometimes returns 200 with malformed body

### Testing Pattern with respx

```python
@respx.mock
async def test_generate_raises_on_timeout():
    mock_route = respx.post("https://openrouter.ai/api/v1/chat/completions").mock(
        side_effect=httpx.ReadTimeout("Request timed out")
    )
    adapter = OpenRouterAdapter(api_key="test-key", base_url="https://openrouter.ai/api/v1")
    
    with pytest.raises(ExternalServiceError):
        await adapter.generate("test prompt", model="test-model")
    
    assert mock_route.call_count == 1  # No retry on timeout

@respx.mock
async def test_generate_raises_on_missing_choices():
    mock_route = respx.post("https://openrouter.ai/api/v1/chat/completions").mock(
        return_value=httpx.Response(200, json={})  # Missing choices key
    )
    # ... same pattern for empty list: json={"choices": []}
```

**Note:** `respx` wraps exception `side_effect` in `SideEffectError`; the original exception (`ReadTimeout`) is re-raised by the router context manager, so the adapter sees the real `httpx.ReadTimeout`.

### Integration Test Verification

Existing integration test verifies 502 path through router:
```python
# tests/integration/test_communications_integration.py
def test_generate_communication_llm_500_returns_502:
    # Mocks OpenRouter 500 → adapter retries 3x → ExternalServiceError → router returns 502
```

### Router Mapping (Pre-existing)

In `cases.py:256-257`:
```python
except ExternalServiceError as e:
    raise HTTPException(status_code=502, detail=str(e))
```

---

## Generalization Checklist for New LLM Adapters

When adding a new `ILLMPort` implementation:

- [ ] Wrap response content extraction in try/except `(KeyError, IndexError)`
- [ ] Catch `httpx.TimeoutException` (or provider SDK equivalent) before retry logic
- [ ] Raise `ExternalServiceError` for both cases
- [ ] Add unit tests for missing content and timeout
- [ ] Verify integration test covers 502 through router
- [ ] Ensure timeout does NOT trigger retry (fail fast)