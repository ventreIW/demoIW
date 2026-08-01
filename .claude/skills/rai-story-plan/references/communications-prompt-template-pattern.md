# Communications Prompt Template Pattern (S5.4)

**Date:** 2026-07-31
**Story:** S5.4 Communications Generator Backend
**Epic:** E5 Operator Workspace

## Pattern Overview

Reuse the config-driven prompt template pattern established in S3.2 (`prompts/data_enrichment/v1_company_description.txt`) for LLM-based communication draft generation.

## Template Location

```
prompts/communications/v1_draft.txt
```

## Template Structure

```text
You are a collections specialist writing a communication draft for a debtor in Mexico.

Client Profile:
- Name: {client_name}
- Sector: {sector_description}
- Payment Pattern: {payment_history_pattern}

Outstanding Invoices:
{invoice_list}

Payment History:
{payment_history}

Current Collectability Score: {score_value} ({score_category})

Previous Communications:
{comms_log}

Channel: {channel}
Tone: {tone}

Generate a {tone} {channel} message in Spanish to collect payment.
Rules:
- Reference specific invoice(s) by folio and amount
- Do NOT invent facts not in the context
- Keep it professional and legally compliant
- Output ONLY the draft text (no explanations, no markdown)
```

## Placeholders

| Placeholder | Source | Description |
|-------------|--------|-------------|
| `{client_name}` | `Client.name` | Debtor company name |
| `{sector_description}` | `Client.sector_description` | Enriched sector description |
| `{payment_history_pattern}` | `Client.payment_history_pattern` | Enum: ON_TIME, DELAYED_30, etc. |
| `{invoice_list}` | Invoices from case aggregate | Formatted: "INV-001: $50,000 (due 10 days ago)" |
| `{payment_history}` | Payments from case aggregate | Formatted: "$5,000 on 2026-07-15 (transfer)" |
| `{score_value}` | Score.score_value | 0-100 collectability score |
| `{score_category}` | Score.category | HIGH/MEDIUM/LOW |
| `{comms_log}` | Existing communications | Previous drafts with channel/tone/status |
| `{channel}` | Request body | EMAIL, PHONE, WHATSAPP |
| `{tone}` | Request body | FORMAL, FIRM, URGENT |

## Service Integration

```python
class CommunicationDraftService:
    def __init__(self, llm_port: ILLMPort, prompt_dir: Path, model: str):
        self._llm = llm_port
        self._template = (prompt_dir / "communications" / "v1_draft.txt").read_text()
        self._model = model

    def _build_prompt(self, case_detail: CaseDetail, channel: Channel, tone: Tone) -> str:
        # Format all placeholders from case_detail
        return self._template.format(...)

    async def generate(self, case_detail: CaseDetail, channel: Channel, tone: Tone) -> str:
        prompt = self._build_prompt(case_detail, channel, tone)
        return await self._llm.generate(prompt, model=self._model, max_tokens=512)
```

## Configuration

- Model: `settings.MODEL_COMMUNICATIONS` (from `.env`)
- Prompt directory: `<project_root>/prompts` (passed via container)
- Max tokens: 512 (configurable per use case)

## Benefits

1. **Config-driven**: Prompt changes without code deployment
2. **Versioned**: `v1_draft.txt` → `v2_draft.txt` for iterations
3. **Testable**: Unit tests can load template and verify placeholder formatting
4. **Consistent**: Mirrors data_enrichment pattern (S3.2)
5. **Auditable**: Template version tracked in git

## Pitfalls Avoided

- ❌ Don't embed prompts in Python strings (hard to iterate)
- ❌ Don't hardcode model names (use config)
- ❌ Don't skip placeholder validation (template may drift)
- ✅ Do validate template placeholders on service init
- ✅ Do handle missing template gracefully (RuntimeError with clear path)

## Related Patterns

- `data_enrichment` pattern: Same template loading approach
- `LLMEnrichmentService`: Same `ILLMPort` + config-driven template pattern
- `RescoreScenario`: Same domain service pattern (stateless, injected dependencies)