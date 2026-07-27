# E5 Scope — Operator Workspace (Operations Panel + Communications)

**Status:** Active — authorized (Gustavo, 2026-07-27). Designed after E4 merged (`3c07ae0`).
**Backlog:** B-08–B-11 · **Stories:** s5.1–s5.5 · **Size:** L (~7–10 days)
**Branch model:** logical container; stories branch from `main`.

## Objective
Give the collections operator (P-01) one continuous daily workspace: a prioritized case list (from
E4) → case detail → record a contact result (triggers E4 rescore) → generate an AI-assisted
communication draft, edit it, and send only on explicit confirmation, with every draft and send audited.

## Value
Turns E4's intelligence into an operator-usable product — the first end-user surface of the demo,
and the first consumer of the OpenRouter comms path (RF-04). Unblocks the P-01 demo narrative.

## In scope (MUST)
| Item | Story | New surface |
|---|---|---|
| Operations panel — prioritized case list (client, amount, days overdue, score, category); ES UI | s5.1 | frontend page + api client; consumes existing `/prioritized` |
| Case detail — profile + invoices + payment history + communications log | s5.2 | **new** read API (case aggregate) + frontend detail page |
| Record contact result + update status → triggers E4 rescore (s4.6) | s5.3 | **new** contact-result persistence endpoint (`ContactResultORM` exists) + UI action |
| Communications generator — backend: OpenRouter draft from case+channel+tone; prompt templates in config; draft persistence + audit | s5.4 | **new** use case + endpoint + `ICommunicationRepository`; prompt template file |
| Communications generator — frontend: editable draft, channel/tone selector, explicit send confirmation; launched from case detail | s5.5 | frontend flow |

## SHOULD
- Comms log on the case detail reflects drafts created in s5.4/s5.5 (audit visible to the operator).

## Out of scope
| Item | Reason / destination |
|---|---|
| Executive panel / KPI dashboard / NL query | E6 |
| Real message delivery (email/SMS gateways) | Demo: "send" = mark status `sent` + audit row; no external transport |
| Full English translation pass | E7 |
| Multi-operator auth / roles | Demo is single-operator; parking lot |
| Prioritized endpoint reading persisted scores | Parked E4 follow-up; s5.1 uses the live `/prioritized` as-is |

## Architecture decisions
No new ADRs. E5 reuses established patterns:
- OpenRouter via `ILLMPort` (s3.2) + config-driven prompt template (mirrors `prompts/data_enrichment/`).
- Hexagonal repos over existing `CommunicationORM` / `ContactResultORM` + mappers (E2).
- Next.js `[locale]` pages + `lib/api` client + next-intl (E4/b15).

## Stories
| ID | Title | Size | Depends on |
|---|---|---|---|
| s5.1 | Operations panel — prioritized case list | S | E4 `/prioritized` (done) |
| s5.2 | Case detail view (+ case-aggregate read API) | M | s5.1 |
| s5.3 | Contact result + status update (→ rescore) | S | s5.2, E4 s4.6 (done) |
| s5.4 | Communications generator — backend | M | s5.2, s3.2 adapter (done) |
| s5.5 | Communications generator — frontend flow | S | s5.4 |

Execution: `s5.1 → s5.2 → {s5.3, s5.4 → s5.5}`. Case detail (s5.2) is the hub.

## Done when
- [ ] Case list shows client, amount, days overdue, score, category per row (RF-05.1)
- [ ] Case detail shows profile + invoices + payment history + comms log (RF-05.2)
- [ ] Operator can record a contact result and update status (RF-05.3–4)
- [ ] Recording a result calls the E4 rescore endpoint and the score updates (RF-02.5)
- [ ] Draft produced via OpenRouter from case + channel + tone (RF-04.1–2)
- [ ] Draft is editable; send requires explicit confirmation (RF-04.3–4)
- [ ] Every draft + send stored with timestamp, operator, model, prompt version (RF-04.5, NFR-06)
- [ ] Prompt templates live in config, not code (RF-04.6)
- [ ] Comms launched from within case detail (RF-05.5)
- [ ] All tests pass (pytest + vitest); mypy + typecheck + lint + format clean
- [ ] All story retrospectives written; E2E covers list → detail → contact → draft

## Risks
| Risk | L/I | Mitigation |
|---|---|---|
| Each story spans backend + frontend → hidden scope inflation | M/M | Story-design splits backend/frontend tasks explicitly; s5.2 & s5.4 sized **M** to reflect the new APIs |
| Free-tier OpenRouter cap (50 req/day) during comms demos | M/L | Draft generation is on-demand + editable; batch runs unnecessary. Reasoning-model note from s4.8: set generous max_tokens or use `:super` |
| Contract seam between s5.1 UI and E4 `/prioritized` payload | L/M | Verified server-side by E4's E2E; s5.1 story-design adds a client-contract test |
| "Send" ambiguity in a demo (no real transport) | L/L | Explicitly scoped: send = status `sent` + audit row, no external delivery |
