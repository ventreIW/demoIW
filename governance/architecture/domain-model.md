# Domain Model

Traces to: `governance/prd.md § RF-01–RF-06`, `governance/guardrails.md § GR-DATA-001–002`

All entities represent **synthetic data only**. No real legal entity, RFC, or personal identifier may appear (GR-DATA-001, GR-DATA-002).

---

## Entities

### Scenario
The container for a synthetic dataset. All other entities belong to a scenario.

| Field | Type | Notes |
|---|---|---|
| id | UUID | PK |
| name | string | Human label (e.g., "Manufacturing — 200 clients") |
| sector | enum | MANUFACTURING, RETAIL, PROFESSIONAL_SERVICES, … |
| seed | integer | Deterministic reproducibility (RF-01.6) |
| parameters | JSON | client_count, invoice_volume, overdue_rate_dist, payment_pattern_dist |
| source | enum | GENERATED, CSV_UPLOAD |
| status | enum | ACTIVE, INACTIVE |
| created_at | datetime | |

**Invariant:** Only one scenario may be ACTIVE at a time per user session.

---

### Client
A synthetic company with overdue accounts.

| Field | Type | Notes |
|---|---|---|
| id | UUID | PK |
| scenario_id | UUID | FK → Scenario |
| name | string | Synthetic company name (LLM-enriched) |
| sector_description | string | LLM-enriched qualitative descriptor |
| total_outstanding | decimal | Computed from invoices |
| payment_history_pattern | enum | GOOD_PAYER, SLOW_PAYER, IRREGULAR, DEFAULTER |

---

### Invoice
An individual overdue invoice belonging to a client.

| Field | Type | Notes |
|---|---|---|
| id | UUID | PK |
| client_id | UUID | FK → Client |
| amount | decimal | Original invoice amount |
| issue_date | date | |
| due_date | date | |
| days_overdue | integer | Computed at query time from due_date |
| status | enum | OVERDUE, PAID, DISPUTED, WRITTEN_OFF |

---

### Payment
A partial or full payment against an invoice.

| Field | Type | Notes |
|---|---|---|
| id | UUID | PK |
| invoice_id | UUID | FK → Invoice |
| amount | decimal | |
| payment_date | date | |

---

### Score
The collectability score for a client in a scenario, produced by the scoring engine.

| Field | Type | Notes |
|---|---|---|
| id | UUID | PK |
| client_id | UUID | FK → Client |
| scenario_id | UUID | FK → Scenario |
| score | integer | 0–100, probability of recovery (RF-02.1) |
| category | enum | HIGH, MEDIUM, LOW (RF-02.2) |
| factors | JSON | Top factors with direction and weight (RF-02.3) |
| model_version | string | Version of the scoring model used |
| calculated_at | datetime | |

**Invariant:** One active score per client per scenario. Recalculated on ContactResult (RF-02.5).

---

### PriorityEntry *(computed — not persisted)*
The prioritized view of a client for the operations panel.

| Field | Type | Notes |
|---|---|---|
| client_id | UUID | |
| priority_value | decimal | score × total_outstanding (RF-03.1) |
| rank | integer | Ascending rank in the queue |
| pareto_flag | boolean | True if this case is in the 20% that concentrates 80% of expected value (RF-03.2) |

---

### Communication
A generated draft or sent message for a client case.

| Field | Type | Notes |
|---|---|---|
| id | UUID | PK |
| client_id | UUID | FK → Client |
| scenario_id | UUID | FK → Scenario |
| channel | enum | EMAIL, WHATSAPP, FORMAL_LETTER |
| tone | enum | PROFESSIONAL, FORMAL, FRIENDLY_REMINDER |
| draft_content | text | LLM-generated draft (editable by operator) |
| final_content | text | Content at time of send (may differ from draft) |
| operator_id | string | Identifier of the reviewing operator |
| model_used | string | OpenRouter model ID (GR-AI-002 / NFR-06) |
| prompt_version | string | Version of prompt template used (NFR-06) |
| status | enum | DRAFT, SENT, CANCELLED |
| created_at | datetime | |
| sent_at | datetime | Null until sent |

**Invariant:** `status = SENT` requires explicit operator confirmation (GR-AI-003). `final_content` is captured at send time.

---

### ContactResult
The outcome recorded by the operator after a contact attempt.

| Field | Type | Notes |
|---|---|---|
| id | UUID | PK |
| client_id | UUID | FK → Client |
| communication_id | UUID | FK → Communication (nullable if no draft sent) |
| result | enum | CONTACTED, NO_ANSWER, COMMITTED_TO_PAY, DISPUTE_RAISED, PAID |
| notes | text | Optional operator notes |
| operator_id | string | |
| recorded_at | datetime | |

**Side effect:** Recording a ContactResult triggers score recalculation (RF-02.5).

---

## Aggregate boundaries

```
Scenario ─┬─► Client ─┬─► Invoice ──► Payment
           │           ├─► Score
           │           ├─► Communication ──► ContactResult
           │           └─► (PriorityEntry — computed)
           │
           └── (top-level root for scenario lifecycle)
```

- **Scenario** is the aggregate root for dataset operations (generate, load, switch).
- **Client** is the aggregate root for collection operations (score, prioritize, communicate, record result).

---

## Enumerations

```python
class Sector(str, Enum):
    MANUFACTURING = "manufacturing"
    RETAIL = "retail"
    PROFESSIONAL_SERVICES = "professional_services"

class PaymentPattern(str, Enum):
    GOOD_PAYER = "good_payer"
    SLOW_PAYER = "slow_payer"
    IRREGULAR = "irregular"
    DEFAULTER = "defaulter"

class ScoreCategory(str, Enum):
    HIGH = "high"       # score >= 65
    MEDIUM = "medium"   # score 35–64
    LOW = "low"         # score < 35

class Channel(str, Enum):
    EMAIL = "email"
    WHATSAPP = "whatsapp"
    FORMAL_LETTER = "formal_letter"

class Tone(str, Enum):
    PROFESSIONAL = "professional"
    FORMAL = "formal"
    FRIENDLY_REMINDER = "friendly_reminder"

class CommunicationStatus(str, Enum):
    DRAFT = "draft"
    SENT = "sent"
    CANCELLED = "cancelled"

class ContactResultType(str, Enum):
    CONTACTED = "contacted"
    NO_ANSWER = "no_answer"
    COMMITTED_TO_PAY = "committed_to_pay"
    DISPUTE_RAISED = "dispute_raised"
    PAID = "paid"
```
