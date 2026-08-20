# BUG-08: scope

**Reported:** 2026-08-20 · **Branch:** `bug/BUG-08/nfr06-auditability` · **From:** `main`
**Found:** project-completion review — NFR-06 was the only NFR never verified.

WHAT:      **NFR-06 (Auditability) is not implemented.** The PRD requires:

             "Every communication draft generated and every send action must be stored with
              timestamp, operator identifier, model used, and prompt version."

           Of the four mandated fields, one is stored.

WHEN:      Every communication draft and every send, since s5.4/s5.5 shipped (2026-08-01).
           Not a regression — the fields were never there.

WHERE:     `backend/app/adapters/persistence/models.py:75` `CommunicationORM` holds
           `id, client_id, scenario_id, channel, tone, draft_text, status, created_at`.

           | NFR-06 field | Status |
           |---|---|
           | timestamp (draft) | ✅ `created_at` |
           | operator identifier | ❌ absent |
           | model used | ❌ absent |
           | prompt version | ❌ absent |
           | timestamp (send) | ❌ absent — `send_communication` flips `status` to SENT and records no `sent_at` |

           There is no audit table among the seven; `/usr/bin/grep -rn "audit"` over `app/`
           returns only an unrelated docstring.

           The data exists but is discarded:
           - `communication_draft_service.py:43` holds `self._model`
           - `:47` loads `prompts/communications/v1_draft.txt` — the filename encodes `v1`
           - `generate_communication_draft.py:129` builds `Communication(...)` without either
           - `cases.py:284` rebuilds the entity on send, carrying `created_at` forward and
             adding nothing

EXPECTED:  Each communication record carries who initiated it, which model wrote it, which
           prompt version produced it, when it was drafted, and when it was sent.

Done when: 1. `CommunicationORM` stores `operator_id`, `model_used`, `prompt_version`, `sent_at`.
           2. A draft persists the real model and the real prompt version — read from the
              service that used them, not hardcoded at the call site.
           3. A send stamps `sent_at`; a draft leaves it null.
           4. The operator identifier is populated and **honest about being a demo
              placeholder** — this product has no authentication (B-17 is still "under
              consideration"), so an invented username would be a fabricated audit record.
           5. Migration `0005` applies and reverses cleanly; existing rows backfill without
              inventing provenance they never had.
           6. The API surfaces the audit fields, so the record is inspectable rather than
              merely stored.
           7. Full backend suite green; `ruff`, `ruff format`, `mypy` clean.

TRIAGE:
  Bug Type:    Functional
  Severity:    S2-Medium
  Origin:      Design
  Qualifier:   **Missing**

  Rationale:
  - Qualifier=Missing is the exact fit: nothing here is *wrong*, it is *absent*. This is the
    first Missing-qualified defect in this project; BUG-01…BUG-07 were all Incorrect.
  - Origin=Design: NFR-06 predates s5.4. The requirement was written, and the schema was
    designed without it. Not a coding slip — `CommunicationORM` is internally coherent, it
    simply implements a narrower contract than the PRD specifies.
  - Bug Type=Functional: required behaviour absent, rather than an interface or data-shape
    defect.
  - **S2, not S1.** No user-facing behaviour is broken and nothing produces a wrong answer,
    so the demo runs today. Not S3 because auditability is not cosmetic here: this product
    generates customer-facing collections messages with an LLM, and "which model wrote this
    and under which prompt" is the question a real deployment gets asked first. It is also a
    named PRD requirement blocking a completion claim.
  - Not a regression: `git log` shows the fields were never present.
