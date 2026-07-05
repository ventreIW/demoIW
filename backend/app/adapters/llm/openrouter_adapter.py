from __future__ import annotations

import httpx
import asyncio
import time
import logging
from typing import Any, Optional

from app.ports.llm_port import ILLMPort
from app.domain.exceptions import ExternalServiceError

log = logging.getLogger(__name__)


class OpenRouterAdapter(ILLMPort):
    """OpenRouter implementation of ILLMPort."""

    _MAX_RETRIES = 3
    _RETRY_STATUSES = {500, 502, 503, 504}

    def __init__(self, api_key: str, base_url: str = "https://openrouter.ai/api/v1") -> None:
        self._client = httpx.AsyncClient(base_url=base_url, headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        })

    async def generate(self, prompt: str, model: str, max_tokens: int = 512) -> str:
        return await self._call(
            messages=[{"role": "user", "content": prompt}],
            model=model,
            max_tokens=max_tokens,
        )

    async def query(self, system_prompt: str, user_message: str, model: str) -> str:
        return await self._call(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            model=model,
            max_tokens=1024,  # default for query, can be overridden if needed
        )

    async def _call(self, *, messages: list[dict[str, Any]], model: str, max_tokens: int) -> str:
        start = time.monotonic()
        last_error: Optional[Exception] = None
        for attempt in range(self._MAX_RETRIES):
            try:
                response = await self._client.post(
                    "/chat/completions",
                    json={"model": model, "messages": messages, "max_tokens": max_tokens},
                )
                if response.status_code in self._RETRY_STATUSES and attempt < self._MAX_RETRIES - 1:
                    await asyncio.sleep(2 ** attempt)  # exponential backoff
                    continue
                response.raise_for_status()
                data = response.json()
                self._log(model, data, time.monotonic() - start)
                content: str = data["choices"][0]["message"]["content"]
                return content
            except httpx.HTTPStatusError as e:
                last_error = e
                if e.response.status_code not in self._RETRY_STATUSES:
                    break
                # retry on 5xx
                await asyncio.sleep(2 ** attempt)
        raise ExternalServiceError(f"OpenRouter call failed: {last_error}")

    def _log(self, model: str, data: dict[str, Any], latency: float) -> None:
        usage = data.get("usage", {})
        log.info(
            "llm_call_complete",
            extra={
                "model": model,
                "prompt_tokens": usage.get("prompt_tokens"),
                "completion_tokens": usage.get("completion_tokens"),
                "latency_ms": round(latency * 1000),
            },
        )