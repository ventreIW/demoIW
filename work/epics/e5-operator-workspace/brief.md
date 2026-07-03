# E5 Brief — Operator Workspace (Operations Panel + Communications)

**Backlog source:** B-08, B-09, B-10, B-11
**Status:** Proposed — not yet authorized
**Estimated size:** L (~7–10 days)
**Branch model:** logical container; stories branch from `main` after E4 merges

---

## Goal

Give the collections operator (P-01) their daily workspace. A **prioritized case list** (from E4)
is the default view; each row shows client, amount, days overdue, score, and category. Opening a
case reveals its full profile — invoices, payment history, and communications log. The operator
can **record a contact result** and **update status**, which triggers a rescore (E4). From within
the case, the operator launches the **AI-assisted communications generator**: a draft is produced
via OpenRouter, shown in an editable area, and only sent after explicit confirmation — with every
draft and send fully audited.

This is one continuous operator workflow, which is why the panel and the communications generator
live in the same epic (RF-05.5: comms is triggered *from* the case detail view).

---

## Success criteria

| Criterion | Verifiable signal | RF |
|---|---|---|
| Prioritized list | Case list shows client, amount, days overdue, score, category per row | RF-05.1 |
| Case detail | Detail view shows profile + invoices + payment history + comms log | RF-05.2 |
| Record contact result | Operator can log Contacted / No answer / Committed / Dispute / Paid | RF-05.3 |
| Update status | Operator can change case status | RF-05.4 |
| Rescore on contact | Recording a result calls the E4 rescore endpoint and updates the score | RF-02.5 |
| Generate draft | Draft produced via OpenRouter from case + channel + tone | RF-04.1–2 |
| Editable + confirm | Draft is editable; send requires explicit confirmation | RF-04.3–4 |
| Audited | Every draft + send stored with timestamp, operator, model, prompt version | RF-04.5, NFR-06 |
| Config-driven prompts | Prompt templates live in config, not code | RF-04.6 |
| Triggered from case | Comms launched from within case detail | RF-05.5 |

---

## Stories

| ID | Title | Size | Notes |
|---|---|---|---|
| s5.1 | Operations panel — prioritized case list | S | Consumes E4 prioritized API; per-row metrics; ES UI (via s4.1 i18n) |
| s5.2 | Case detail view | S | Profile + invoices + payment history + comms log |
| s5.3 | Contact result + status update | S | Record result, update status, trigger E4 rescore (s4.6) |
| s5.4 | Communications generator — backend | S | OpenRouter call via s3.2 adapter; prompt templates in config; draft persistence + audit log |
| s5.5 | Communications generator — frontend flow | S | Editable draft UI, channel/tone selector, confirmation; launched from case detail |

---

## Execution order

```
s5.1 → s5.2 → s5.3
          └─→ s5.4 → s5.5
```

Case detail (s5.2) is the hub: status/contact actions (s5.3) and the comms flow (s5.4→s5.5) both
hang off it. s5.4 needs the OpenRouter adapter (s3.2).

## Dependencies

- **E4** — prioritized list + scores to display; rescore endpoint (s4.6) for RF-02.5.
- **E3 · s3.2 (OpenRouter adapter / `ILLMPort`)** — required for communications generation. This
  is the first *consumer* of the shared LLM adapter; confirm s3.2 is done before s5.4.
- **E2** — reuse existing `Communication` and `ContactResult` domain entities (already modelled).
- **s4.1** — i18n foundation, so this UI is ES-first.

## Risks

- **Contract coupling (frontend/backend)** — comms draft request/response shape must be agreed up
  front, exactly as E2 did for CSV upload (s2.4/s2.5 split worked because the contract was fixed
  first). Recommend a contract-first design for s5.4/s5.5.
- **Audit completeness (NFR-06)** — every generate *and* send must persist model + prompt version;
  design the audit record before building the flow.

## Out of scope

- Executive KPIs / NL query (E6)
- PWA, accessibility pass, English translation (E7)
- Real outbound sending (email/WhatsApp integration) — "send" records the action; no real delivery
