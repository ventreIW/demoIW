# E3 Design — Synthetic Dataset Generator

Traces to: `governance/prd.md § RF-01`, `governance/architecture/modules/adapters.md`

---

## Generation architecture

```
GenerateDataset use case
  │
  ├─► IDatasetPort.generate_procedural(params)
  │     └─► ProceduralGenerator
  │           ├─ numpy.random.default_rng(seed)   ← determinism
  │           ├─ Faker(locale='es_MX')             ← synthetic names
  │           └─ Pandas DataFrame assembly
  │
  └─► ILLMPort.generate(prompt, model)
        └─► OpenRouterAdapter
              └─ POST https://openrouter.ai/api/v1/chat/completions
```

The two phases are sequential: procedural generates the quantitative skeleton, then LLM enriches qualitative fields (company descriptions, sector narratives, previous communication summaries).

---

## Procedural generation parameters

```python
class GenerationParams(BaseModel):
    sector: Sector
    client_count: int = Field(ge=10, le=500)   # NFR-02: up to 500 clients
    invoice_volume: int = Field(ge=1, le=10)   # avg invoices per client
    overdue_rate: float = Field(ge=0.1, le=1.0) # fraction of invoices that are overdue
    seed: int = Field(ge=0)
    # Distribution parameters (optional overrides)
    amount_mean: Decimal = Decimal("15000")
    amount_std: Decimal = Decimal("8000")
    days_overdue_lambda: float = 45.0  # exponential distribution mean
```

### Statistical distributions

| Attribute | Distribution | Rationale |
|---|---|---|
| Invoice amount | Normal(mean, std), clipped > 0 | Realistic invoice spread |
| Days overdue | Exponential(λ=45) | Most accounts cluster at 30–60 days; long tail for chronic delinquents |
| Payment history pattern | Weighted choice per sector | Manufacturing = more SLOW_PAYER; Retail = more IRREGULAR |
| Number of invoices per client | Poisson(λ=invoice_volume) | Natural clustering |

### Pandas assembly

1. Generate `client_count` client rows (UUID, Faker name, sector, payment pattern)
2. For each client, generate Poisson(λ) invoice rows (amount, issue_date, due_date)
3. Assign overdue status to `overdue_rate` fraction of invoices by due_date < today
4. Generate payment rows for non-overdue invoices
5. Return as `RawDataset(clients: DataFrame, invoices: DataFrame, payments: DataFrame)`

---

## OpenRouter adapter

```python
class OpenRouterAdapter(ILLMPort):
    def __init__(self, api_key: str, base_url: str):
        self._client = httpx.AsyncClient(
            base_url=base_url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=30.0,
        )

    async def generate(self, prompt: str, model: str, max_tokens: int = 512) -> str:
        for attempt in range(3):
            try:
                response = await self._client.post(
                    "/chat/completions",
                    json={"model": model, "messages": [{"role": "user", "content": prompt}], "max_tokens": max_tokens}
                )
                response.raise_for_status()
                return response.json()["choices"][0]["message"]["content"]
            except httpx.HTTPStatusError as e:
                if e.response.status_code < 500 or attempt == 2:
                    raise ExternalServiceError(str(e))
                await asyncio.sleep(2 ** attempt)
```

Model names are always caller-provided (from `Settings`) — never hardcoded (GR-AI-002).

---

## LLM enrichment

Enriched fields per client:
- `name`: sector-appropriate synthetic company name (replaces Faker name)
- `sector_description`: 1-sentence company profile

Prompt template `prompts/data_enrichment/v1_company_description.txt`:
```
You are generating synthetic company names for a financial demo application.
Generate {count} company names and 1-sentence profiles for companies in the {sector} sector in Mexico.
Output as JSON array: [{"name": "...", "description": "..."}]
Companies must be completely fictional — no real company names.
```

Enrichment is batched: one LLM call per 20 clients (reduces latency and token cost).

---

## "Generar nuevo" form (frontend)

```
┌─────────────────────────────────────┐
│  Generar nuevo escenario            │
│                                     │
│  Sector: [Manufactura ▼]            │
│  Clientes: [100]  Facturas/cliente: [3] │
│  Tasa de vencimiento: [40%]         │
│  Semilla: [auto] (checkbox)         │
│                                     │
│  [Cancelar]  [Generar escenario]    │
└─────────────────────────────────────┘
```

On submit: `POST /api/scenarios/generate` → loading state (spinner + "Generando datos...") → on success, activate scenario + redirect to operations panel placeholder.

---

## ADRs to be written

- **ADR-003:** Faker + NumPy + Pandas for procedural generation (vs. purely LLM-generated data).
- **ADR-004:** Batched LLM enrichment strategy (20 clients/call vs. one-by-one).
