# Product Requirements Document

Traces to: `governance/vision.md`

---

## User profiles

### P-01 — Collections operator
A staff-level user responsible for contacting overdue accounts daily. Needs a clear prioritized list, case detail, and communication drafts ready to review. Not technical.

### P-02 — Executive / Finance director
A decision-maker who monitors portfolio health, spots risks, and asks analytical questions. Needs a high-level dashboard and the ability to query the data in natural language.

### P-03 — Demo facilitator (InterWare)
An InterWare consultant running a live demonstration for a prospect. Needs to load a sector-specific scenario quickly, navigate both user profiles, and show the full value proposition within 10 minutes.

---

## Functional requirements

### RF-01 — Synthetic dataset generator (§6)
The system must generate complete, realistic accounts receivable portfolios without using real customer data.

- RF-01.1: Generate a scenario from configurable parameters: sector, number of clients, invoice volume, overdue rate distribution, payment history patterns.
- RF-01.2: Use statistical distributions (NumPy) for quantitative attributes (amounts, dates, frequencies).
- RF-01.3: Use LLM enrichment (OpenRouter) for qualitative attributes (company names, sector descriptions, communication history narratives).
- RF-01.4: Support at least three pre-loaded sector scenarios on first launch (e.g., manufacturing, retail, professional services).
- RF-01.5: Accept CSV upload of a user-provided dataset as an alternative to generated scenarios.
- RF-01.6: Scenario selection must be available as the entry point before accessing any other module.

### RF-02 — Collectability evaluation engine (§1, §2)
The system must score each overdue account with an estimated probability of recovery.

- RF-02.1: Score each account on a 0–100 scale representing probability of recovery within the configured horizon.
- RF-02.2: Categorize each account into at least three levels (e.g., High / Medium / Low recoverability).
- RF-02.3: Generate a human-readable explanation of the top factors driving each score.
- RF-02.4: The model must be trained on synthetic data produced by RF-01.
- RF-02.5: Recalculate scores when an operator records a contact result.

### RF-03 — Prioritization engine (§3)
The system must produce a daily ordered list of cases to contact.

- RF-03.1: Combine recoverability score and outstanding amount to compute a priority value per case.
- RF-03.2: Apply Pareto-based filtering to identify the subset of cases concentrating 80% of expected recoverable value.
- RF-03.3: Present the prioritized list as the default view in the operations panel.
- RF-03.4: Allow the operator to filter and re-sort the list by dimensions (amount, days overdue, category).

### RF-04 — Assisted communications generator (§4, §5)
The system must generate personalized, professional collection message drafts.

- RF-04.1: Accept as input: case detail, contact channel (email / WhatsApp / formal letter), desired tone (professional / formal / friendly reminder).
- RF-04.2: Generate a draft via OpenRouter using a configurable model and prompt template.
- RF-04.3: Present the draft in an editable text area before any send action is available.
- RF-04.4: Send action must require explicit operator click confirmation.
- RF-04.5: Record each generated and sent communication in the database, linked to the case.
- RF-04.6: Prompt templates must be stored in configuration, not hardcoded in business logic.

### RF-05 — Operations panel (§1)
The operator's daily workspace.

- RF-05.1: Display the prioritized case list with key metrics per row (client, amount, days overdue, score, category).
- RF-05.2: Open a case detail view with full client profile, invoice list, payment history, and previous communications.
- RF-05.3: Allow the operator to record a contact result (Contacted / No answer / Committed to pay / Dispute raised / Paid).
- RF-05.4: Allow the operator to update case status.
- RF-05.5: Trigger the communications generator from within the case detail view.

### RF-06 — Executive panel (§1)
The director's portfolio intelligence view.

- RF-06.1: Display portfolio-level KPIs: total overdue amount, expected recoverable value, number of cases by category, recovery rate (actual vs. expected).
- RF-06.2: Display a segmentation breakdown by at least two dimensions (e.g., sector, days overdue bucket, amount range).
- RF-06.3: Provide a natural language query input that translates the user's question into structured database queries and returns an answer with data visualization and narrative explanation.
- RF-06.4: Natural language responses must cite the data source (which dataset/scenario is active).

### RF-07 — Scenario management
- RF-07.1: The active scenario must be clearly indicated in the UI at all times.
- RF-07.2: Switching scenarios must reset the operations state (contact history, status updates) for the new scenario.
- RF-07.3: Generated scenarios must be persisted and re-loadable within the same session.

---

## Non-functional requirements

### NFR-01 — Demonstrability
A new user must be able to complete the full demo flow (load scenario → view priority queue → open case → generate communication → view executive dashboard → run NL query) in under 10 minutes without assistance.

### NFR-02 — Performance
The priority queue must load within 3 seconds for a scenario of up to 500 clients and 2,000 invoices.  
LLM-backed operations (communication generation, NL query) must show a loading state and complete within 30 seconds.

### NFR-03 — Multilingual interface
The user interface must support Spanish as the primary language. English must be available as an alternative language for the same interface.

### NFR-04 — Progressive web app
The frontend must be installable as a PWA on Android and iOS devices.

### NFR-05 — Accessibility
The interface must meet WCAG 2.1 AA contrast requirements. All interactive elements must be keyboard-navigable.

### NFR-06 — Auditability
Every communication draft generated and every send action must be stored with timestamp, operator identifier, model used, and prompt version.
