# BUG-03: scope

**Reported:** 2026-08-20 · **Branch:** `bug/BUG-03/csv-scenarios-unscorable` · **From:** `main`

WHAT:      A scenario created via CSV upload can never be scored, prioritized, or shown on the
           executive dashboard. Upload returns 201 and the scenario persists correctly, but
           every downstream consumer sees zero outstanding balance. `/prioritized` raises an
           unhandled `InsufficientOutstandingError` (500), rather than degrading.

           The error text is actively misleading:
             "no clients with an outstanding balance — nothing to label.
              Every invoice in this scenario is settled."
           Nothing is settled. The invoices match neither the open branch nor the settled
           branch, so they are invisible to both, and the diagnostic names the wrong cause.

WHEN:      Every CSV-uploaded scenario, regardless of size or content. Reproduced 2026-08-20 on
           `main` at the BUG-02 merge, with 30 clients (above the MIN_CLIENTS=20 floor) all
           genuinely past due — so client count and ageing are excluded as causes.

WHERE:     `backend/app/adapters/persistence/sqlalchemy_scenario_repo.py:118`
             `status="pending"` — a literal that appears nowhere else in the domain.

           Consumers, which never match it:
           - `app/application/services/feature_extractor.py:28-29`
             `_OPEN_STATUS = "overdue"`, `_SETTLED_STATUS = "paid"`
           - `app/adapters/dataset/procedural_generator.py:129,158`
             writes `"overdue"` and `"paid"`

           **There is no `InvoiceStatus` enum.** `app/domain/enums.py` defines eight StrEnums
           (Sector, ScenarioStatus, PaymentPattern, ScoreCategory, Channel, Tone,
           CommunicationStatus, ContactResultType) and invoice status is not among them.
           `InvoiceORM.status` is a bare `Mapped[str]`. Every producer and consumer spells the
           value as its own string literal.

           Concealed by `backend/tests/test_csv_upload.py`, which asserts upload returns 201
           and that bad input returns 422 — and never that an uploaded scenario can be used
           for anything afterwards. The path is tested to the point of persistence and no
           further.

EXPECTED:  A CSV-uploaded scenario behaves like a generated one: its unpaid invoices count as
           outstanding, it scores, it prioritizes, and it appears on the dashboard.

Done when: 1. Upload a ≥20-client CSV, then `/prioritized` returns 200 with a non-empty case
              list whose outstanding total equals the sum of the uploaded amounts.
           2. `/kpis` returns 200 for the same scenario with non-zero total overdue.
           3. Invoice status has a single source of truth — an enum — used by the CSV path,
              the procedural generator, and the feature extractor alike.
           4. Existing persisted data keeps working: the enum's *values* stay `"overdue"` and
              `"paid"`, so no migration of existing rows is required.
           5. A regression test covers upload → prioritize end to end, not just upload.
           6. Full backend suite green; no test weakened or deleted.

TRIAGE:
  Bug Type:    Data
  Severity:    S1-High
  Origin:      Design
  Qualifier:   Incorrect

  Rationale:
  - Data, not Interface: unlike BUG-02 the HTTP contract is fine. The defect is in the value
    written to storage — a domain attribute persisted in a vocabulary no reader shares.
  - S1: this removes an entire advertised product capability. B-07/RF-07 ("Scenario management
    API + UI — pre-loaded scenarios, CSV upload") is a delivered feature that cannot do the
    thing it exists for. It also fails as a 500 rather than a handled error, and the CSV
    upload is part of the demo narrative s7.4 must validate.
  - **Origin=Design, not Code.** This is the one meaningful difference from BUG-02. There is
    no `InvoiceStatus` enum to have been used incorrectly — the type was never modelled. Seven
    other domain concepts got StrEnums; invoice status did not, so every site was free to
    invent its own spelling and two of them agreed only by luck. Fixing the literal alone
    would leave the next writer equally free.
  - Qualifier=Incorrect: a value is written and it is the wrong one.

  Jira fields: not set — no backlog adapter configured (`.raise/backlog.yaml` absent).
