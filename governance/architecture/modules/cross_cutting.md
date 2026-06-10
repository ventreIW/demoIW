# Module: Cross-Cutting Concerns

Traces to: `governance/guardrails.md`, `governance/prd.md § NFR-06`, `GR-AI-003`, `GR-AI-004`

Cross-cutting concerns apply across all modules. They are not a layer — they are conventions and shared utilities that every part of the system must respect.

---

## 1. Error handling strategy

### Domain errors → HTTP errors (adapter responsibility)
Domain exceptions defined in `app.domain.exceptions` are translated to HTTP responses by FastAPI exception handlers registered in `main.py`. No raw Python exceptions reach the client.

| Domain exception | HTTP status |
|---|---|
| `EntityNotFoundError` | 404 |
| `InvalidOperationError` | 422 |
| `ExternalServiceError` (OpenRouter timeout/5xx) | 503 |
| `ValidationError` (Pydantic) | 422 |

### LLM errors
- Transient failures (5xx, timeout): retry up to 3 times with exponential backoff in `OpenRouterAdapter`.
- Persistent failure: surface `ExternalServiceError` with a user-visible message indicating the LLM service is unavailable. Do not silently return empty drafts.

---

## 2. Audit log

**Requirement:** NFR-06 — every communication draft and send must be stored with: timestamp, operator_id, model_used, prompt_version.

The `Communication` entity carries these fields. Additionally:
- A structured log entry is written at draft creation and at send confirmation.
- Log format includes `event: communication_draft_created | communication_sent`, `communication_id`, `operator_id`, `model_used`, `prompt_version`.

This log is the audit trail — it is immutable once written.

---

## 3. Prompt template management

**Requirement:** RF-04.6, GR-AI-002 — prompt templates must be in configuration, not business logic.

### Storage
```
backend/
  prompts/
    communications/
      v1_email_professional.txt
      v1_whatsapp_friendly.txt
      v1_letter_formal.txt
    data_enrichment/
      v1_company_description.txt
    nl_query/
      v1_system_prompt.txt
```

### Versioning
- Templates are versioned by filename prefix (`v1_`, `v2_`, …).
- `PromptBuilder` selects the template by `(use_case, channel, tone, version)`.
- The active version per use case is set in `Settings` (config), defaulting to the latest.
- Changing a template = new version file + config bump. Old files are kept for audit continuity.

### Prompt constraints (GR-AI-004)
Communications prompts must:
- Instruct the model to use professional, respectful language.
- Include an explicit instruction: "Do not include threatening, legally actionable, or demeaning language."
- Be reviewed by a team member before any version is set as active in production.

---

## 4. Human-in-the-loop enforcement (GR-AI-003)

The send flow enforces human approval structurally:
1. Draft endpoint returns `status = DRAFT` — no send action is embedded in the generation response.
2. Frontend presents the draft in an editable text area. The "Confirm and send" button is a separate explicit action.
3. The send endpoint (`POST /api/communications/{id}/send`) requires `operator_id` in the request body. An empty or missing `operator_id` returns 422.
4. The backend validates `status == DRAFT` before transitioning to `SENT`. Re-sending an already-sent communication returns 409.

---

## 5. Request tracing

A `X-Request-ID` header (UUID) is injected by middleware on every inbound request and included in all structured log entries and error responses. This enables correlation of frontend errors with backend logs during demos.

---

## 6. Security notes (demo scope)

This is a demo application with no real users or real data. However, good practices are followed:
- No SQL string interpolation anywhere — all queries are parameterized.
- OpenRouter API key is never logged or returned in API responses.
- `.env` is gitignored; `.env.example` provides the key list without values.
- CORS is configured to allow only the deployed frontend origin in non-development environments.
