# Communications Prompt Template Pattern (S5.4)

## Template File

**Location:** `prompts/communications/v1_draft.txt`

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

## Placeholders (11 total)

| Placeholder | Source | Notes |
|-------------|--------|-------|
| `{client_name}` | `Client.name` | Required |
| `{sector_description}` | `Client.sector_description` | Can be None → "N/A" |
| `{payment_history_pattern}` | `Client.payment_history_pattern.value` | Enum value (lowercase) |
| `{invoice_list}` | Formatted from invoices | "No outstanding invoices." if empty |
| `{payment_history}` | Formatted from payments | "No payment history." if empty |
| `{score_value}` | `Score.score_value` | Can be None → "N/A" |
| `{score_category}` | `Score.category.value` | Can be None → "N/A" |
| `{comms_log}` | Formatted from communications | "No previous communications." if empty |
| `{channel}` | `Channel.value` | **lowercase**: "email", "phone", "whatsapp" |
| `{tone}` | `Tone.value` | **lowercase**: "formal", "firm", "urgent" |

## Service Integration

```python
# In CommunicationDraftService._build_prompt():
return self._template.format(
    client_name=case_detail.client_name,
    sector_description=case_detail.sector_description or "N/A",
    payment_history_pattern=case_detail.payment_history_pattern,
    invoice_list=invoice_list,
    payment_history=payment_history,
    score_value=case_detail.score_value if case_detail.score_value is not None else "N/A",
    score_category=case_detail.score_category or "N/A",
    comms_log=comms_log,
    channel=channel.value,   # "email", "phone", "whatsapp"
    tone=tone.value,         # "formal", "firm", "urgent"
)
```

## Key Rules

1. **Config-driven** — template lives in `prompts/communications/`, not in code
2. **Versioned** — `v1_draft.txt` allows future iterations without breaking existing tests
3. **Enum values are lowercase** — `channel.value` → `"email"` not `"EMAIL"`
4. **Fail fast** — missing template raises `RuntimeError` during service construction
5. **Spanish output** — prompt explicitly requests Spanish; LLM must honor
6. **No markdown** — "Output ONLY the draft text" prevents LLM formatting