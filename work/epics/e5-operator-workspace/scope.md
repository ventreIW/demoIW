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
- [x] Case list shows client, amount, days overdue, score, category per row (RF-05.1) — s5.1
- [ ] Case detail shows profile + invoices + payment history + comms log (RF-05.2)
- [x] Operator can record a contact result and update status (RF-05.3–4) — s5.3
- [x] Recording a result calls the E4 rescore endpoint and the score updates (RF-02.5) — s5.3
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

---

# Implementation Plan

Sequencing strategy: **walking-skeleton first**, then risk-first on the critical path. The riskiest
elements are the **new case-aggregate read API** (s5.2, the hub) and the **LLM comms generation**
(s5.4 — prompt quality, free-tier limits, reasoning-model noise per the s4.8 lesson). Prove the
frontend↔E4 seam early (s5.1+s5.2), then attack comms.

## Story sequence
| # | Story | Size | Depends on | Rationale | Unblocks |
|---|---|---|---|---|---|
| 1 | s5.1 Operations panel — case list | S | E4 `/prioritized` (done) | Quick win + foundation; proves the frontend↔E4 payload seam | s5.2 |
| 2 | s5.2 Case detail (+ aggregate read API) | M | s5.1 | **The hub.** New read model composed over existing repos; every action hangs off it | s5.3, s5.4 |
| 3 | s5.3 Contact result + status → rescore | S | s5.2, E4 s4.6 (done) | Operator can act; reuses the rescore endpoint | — |
| 3 | s5.4 Communications generator — backend | M | s5.2, s3.2 adapter (done) | **Highest-risk story** (LLM draft quality + audit). Parallel with s5.3 | s5.5 |
| 4 | s5.5 Communications generator — frontend flow | S | s5.4 | Editable draft, channel/tone, confirm-to-send from case detail | — |

**Critical path:** s5.1 → s5.2 → s5.4 → s5.5. s5.3 runs beside s5.4 once s5.2 lands.

## Parallel work streams
```
Frontend-led   s5.1 ──▶ s5.2 ──┬────────────────▶ s5.5
                               ├─▶ s5.3 (act)
Backend-led                    └─▶ s5.4 (comms) ─▶ (hands draft API to s5.5)
```
After s5.2, s5.3 (contact/rescore) and s5.4 (comms backend) are independent and can run concurrently.

## Milestones
### M1 — Walking skeleton: operator sees a case and its detail
**Stories:** s5.1, s5.2
- [x] Case list renders real `/prioritized` rows (client, amount, days overdue, score, category) — s5.1, verified against the running app
- [x] Opening a case shows profile + invoices + payment history + comms log (read-only) — s5.2, verified by 444 tests
- [ ] Frontend↔backend payload seam verified (client-contract test)
**Demo:** log in → prioritized list → open a case.

### M2 — Core MVP: the operator can act
**Stories:** + s5.3, s5.4
- [ ] Recording a contact result persists it, updates status, and the score changes (rescore)
- [ ] `POST …/communications` returns an OpenRouter draft from case+channel+tone; draft persisted + audited
- [ ] Prompt templates live in config, not code
**Demo:** open a case → record "promise to pay" → score updates → generate a draft (API).

### M3 — Feature complete: end-to-end operator workflow
**Stories:** + s5.5
- [ ] Draft is editable; channel/tone selector; send requires explicit confirmation
- [ ] Comms launched from within case detail; send transitions status → `sent` + audit row
- [ ] `es.json`/`en.json` key parity maintained
**Demo:** the full P-01 loop, list → detail → contact → draft → edit → send.

### M4 — E2E integration checkpoint + epic close
**Stories:** none new — verification only. **(Mandatory per E4's M4 lesson — mocked unit tests miss seams.)**
- [ ] Full path works E2E against real infrastructure: list → detail → contact result → rescore → generate → send
- [ ] Frontend consumes each new API with real payloads (contract seams verified)
- [ ] Every acceptance-gate item verified against observable state
- [ ] All retrospectives written; parking-lot follow-ups filed

## Progress tracking
| Story | Owner | Status | Started | Merged | Notes |
|---|---|---|---|---|---|
| s5.1 | Rodrigo | **done** ✓ | 2026-07-27 | 2026-07-28 | Backend contract extended (`client_name`, `days_overdue`) + repaired the never-working `days_overdue_min` filter and `days_overdue` sort. Manual integration caught a lowercase-enum seam bug and a middleware guard that made every operator route unreachable |
|| s5.2 | Renata | **done** ✓ | 2026-07-28 | 2026-07-28 | Case detail endpoint + frontend page. 444 tests (366 backend + 78 frontend) |
| s5.3 | Renor | **done** ✓ | 2026-07-30 | 2026-07-30 | Contact result form frontend — type dropdown, notes, record button, score update. 88 frontend tests + 377 backend tests pass |
| s5.4 | — | blocked | — | — | needs s5.2 |
| s5.5 | — | blocked | — | — | needs s5.4 |

## Sequencing risks
| Risk | Mitigation |
|---|---|
| s5.2 aggregate API balloons (composing 4 repos) | Keep it a thin read model; no new persistence; sized M deliberately |
| s5.4 comms quality/flakiness on the free reasoning model | Apply s4.8 lessons: generous max_tokens or `:super`/`:nano`; draft is editable so quality is human-gated |
| Backend+frontend split per story hides effort | Story-design splits tasks explicitly; M1 walking skeleton surfaces seam issues early |
| Plans are hypotheses | Re-sequence at M1 if the aggregate API or comms proves harder than sized |

