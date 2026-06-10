# Module: Adapters

Traces to: `governance/architecture/modules/ports.md`, `governance/guardrails.md § GR-ARCH-004`, `GR-AI-001`

Adapters implement port interfaces and bridge application logic to external systems (PostgreSQL, OpenRouter, file system). No business logic lives here.

---

## Location (backend)

```
backend/
  app/
    adapters/
      persistence/
        sqlalchemy_scenario_repo.py
        sqlalchemy_client_repo.py
        sqlalchemy_score_repo.py
        sqlalchemy_communication_repo.py
        sqlalchemy_contact_result_repo.py
        models.py          # SQLAlchemy ORM models (separate from domain entities)
        mappers.py         # ORM model ↔ domain entity conversion
      llm/
        openrouter_adapter.py   # ILLMPort implementation
      dataset/
        procedural_generator.py  # NumPy + Faker + Pandas implementation of IDatasetPort
        csv_loader.py
      analytics/
        sql_analytics_adapter.py # IAnalyticsPort implementation (raw SQL via SQLAlchemy core)
      scoring/
        sklearn_scoring_model.py # IScoringModel implementation
```

---

## Adapter notes

### OpenRouterAdapter (ILLMPort)
- Uses `httpx` (async) to call the OpenRouter API.
- Reads `OPENROUTER_API_KEY` and default model names from environment config.
- Implements retry logic with exponential backoff (do not fail silently on transient errors).
- Always passes the `model` parameter from the caller — never hardcodes a model name (GR-AI-001, GR-AI-002).
- Logs: request model, prompt token count, response token count, latency.

### SQLAlchemy repositories
- ORM models (`models.py`) are flat table representations — they are NOT the domain entities.
- `mappers.py` handles bidirectional conversion between ORM models and domain entities.
- This keeps the domain layer free of SQLAlchemy imports.

### ProceduralGenerator (IDatasetPort)
- Uses `numpy.random.default_rng(seed)` for all distributions — ensures reproducibility from seed (RF-01.6).
- Uses `Faker(locale='es_MX')` for synthetic identities.
- After procedural generation, calls `ILLMPort` for qualitative enrichment (RF-01.3) — this means the dataset generator use case injects both `IDatasetPort` and `ILLMPort`.

### SqlAnalyticsAdapter (IAnalyticsPort)
- Executes parameterized SQL via SQLAlchemy Core (not ORM).
- Query plans produced by the NL query use case are validated before execution (no raw string interpolation — prevent injection even on synthetic data, as a good practice).

---

## Dependency injection

Adapters are wired at application startup via a dependency injection container (FastAPI's `Depends` or a simple factory module):

```
app/
  container.py   # instantiates adapters and injects into use cases
```

The FastAPI router layer calls use cases via the container — it never instantiates adapters directly.
