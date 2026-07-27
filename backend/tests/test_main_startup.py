import logging

import pytest

import app.main as main
from app.main import app, lifespan


@pytest.mark.asyncio
async def test_lifespan_warns_when_key_empty(monkeypatch, caplog) -> None:
    """An empty OPENROUTER_API_KEY must be loud, not silent (s4.8).

    A missing key silently degrades enrichment to raw Faker names; startup is
    the one place to make that unmistakable.
    """
    monkeypatch.setattr(main.settings, "OPENROUTER_API_KEY", "")
    with caplog.at_level(logging.WARNING):
        async with lifespan(app):
            pass
    assert any(
        "OPENROUTER_API_KEY is empty" in record.message for record in caplog.records
    ), "expected a startup WARNING naming the empty key"


@pytest.mark.asyncio
async def test_lifespan_silent_when_key_present(monkeypatch, caplog) -> None:
    """With a key configured, no enrichment-disabled warning is emitted."""
    monkeypatch.setattr(main.settings, "OPENROUTER_API_KEY", "sk-or-v1-test")
    with caplog.at_level(logging.WARNING):
        async with lifespan(app):
            pass
    assert not any("OPENROUTER_API_KEY is empty" in record.message for record in caplog.records)
