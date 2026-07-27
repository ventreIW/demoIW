# E5 Design — Operator Workspace

## Gemba findings (what already exists)
- **Backend / E4 APIs (reuse as-is):** `GET /scenarios/{id}/prioritized` (sortable/filterable),
  `POST /scenarios/{id}/clients/{client_id}/rescore` (s4.6), `POST /scenarios/{id}/score` (s4.10).
- **Domain + persistence (E2, reuse):** `Communication` + `ContactResult` entities;
  `CommunicationORM` (channel, tone, draft_text, status, created_at) and `ContactResultORM`
  (result_type, notes, communication_id, recorded_at); both mappers exist in `mappers.py`.
- **LLM (E3, reuse):** `OpenRouterAdapter`/`ILLMPort`; config-driven prompt templates under
  `prompts/` (mirror `data_enrichment/v1_company_description.txt`).
- **Frontend (E4/b15, extend):** Next.js `[locale]` routing, `lib/api/scenarios.ts` client,
  next-intl messages (`messages/{es,en}.json`), shadcn/ui components, `MainLayout`.

**Gap analysis — what E5 must build:** case-aggregate read API (s5.2), contact-result persistence
endpoint + repo (s5.3), communications use case + endpoint + `ICommunicationRepository` + prompt
template (s5.4), and the operator frontend surfaces (s5.1, s5.2, s5.5). No new domain entities,
ORMs, or migrations — the tables exist.

## Target components by story
| Story | Backend | Frontend |
|---|---|---|
| s5.1 | — (reuse `/prioritized`) | cases list page under `[locale]/cases`; `lib/api/cases.ts`; row metrics; ES messages |
| s5.2 | **new** `GET /scenarios/{id}/clients/{client_id}/detail` returning profile + invoices + payments + comms log (aggregate over existing repos) | case detail page; detail api client |
| s5.3 | **new** `POST /scenarios/{id}/clients/{client_id}/contact-result` → persist `ContactResult` + update status + call rescore; `IContactResultRepository` + adapter | contact-result form/action on detail; optimistic score refresh |
| s5.4 | **new** `GenerateCommunication` use case + `POST …/communications` endpoint; `ICommunicationRepository` + adapter; prompt template `prompts/communications/v1_*.txt`; audit fields (model, prompt version) | — |
| s5.5 | — | editable draft area, channel/tone selector, confirm-to-send; launched from case detail |

## Key contracts
- **Case aggregate (s5.2):** `{ client, invoices[], payments[], score, communications[] }` — a read
  model composed in the endpoint from existing repos; no new persistence.
- **Contact result (s5.3):** request `{ result_type, notes? }`; effect: persist `ContactResult`,
  update case/scenario status, invoke rescore, return updated score/prioritization (reuse
  `PrioritizedPortfolioResponse` where natural).
- **Communication (s5.4):** request `{ channel, tone }`; effect: `ILLMPort.generate` with a config
  template → persist `Communication` (status `draft`, model + prompt_version recorded) → return draft.
  "Send" (s5.5) transitions status `draft → sent` with an audit row; **no external transport** (demo).

## Approach notes
- **Follow the s4.8 enrichment lesson:** the free reasoning model needs generous `max_tokens`; if
  drafts come back noisy, switch the comms model to a non-reasoning `:super`/`:nano` (config-only).
- **Contract-first (per s4.5-API pattern):** response models mirror domain; router stays a thin adapter.
- **i18n-first:** every new operator string goes through next-intl; keep `es.json`/`en.json` key-parity
  (E4 close verified 56/56 — do not regress).
- **Prompt-injection surface:** comms drafts include client data in the prompt; keep templates
  config-owned and treat model output as untrusted display text (no eval/HTML injection in the UI).

## Legacy sweep
Net-new epic; nothing superseded. Reuses E2 entities/ORMs and E4 APIs unchanged.
