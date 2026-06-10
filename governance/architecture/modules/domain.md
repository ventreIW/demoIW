# Module: Domain Layer

Traces to: `governance/architecture/domain-model.md`, `governance/guardrails.md § GR-ARCH-004`

The domain layer contains pure business logic with zero external dependencies. No database imports, no HTTP clients, no framework code.

---

## Responsibilities

- Define entity classes and value objects
- Express domain invariants as methods and validators
- Implement domain rules that do not require external I/O

## Location (backend)

```
backend/
  app/
    domain/
      entities/
        scenario.py
        client.py
        invoice.py
        payment.py
        score.py
        communication.py
        contact_result.py
      value_objects/
        money.py          # decimal with currency; prevents float arithmetic
        score_value.py    # 0–100 range + category derivation
        priority_value.py # score × outstanding computation
      enums.py            # all Enum definitions (see domain-model.md)
      exceptions.py       # domain-level exceptions (InvalidScoreRange, etc.)
```

## Key domain rules

| Rule | Location | Source |
|---|---|---|
| ScoreCategory derived from score integer (HIGH ≥ 65, MEDIUM 35–64, LOW < 35) | `ScoreValue` value object | RF-02.2 |
| PriorityValue = score × total_outstanding | `PriorityValue` value object | RF-03.1 |
| Communication cannot transition DRAFT → SENT without operator_id | `Communication.confirm_send()` | GR-AI-003 |
| Only one ACTIVE scenario at a time | `Scenario.activate()` | Domain invariant |
| ContactResult triggers score invalidation | `Client.record_contact_result()` emits domain event | RF-02.5 |

## Design notes

- Entities use Pydantic `BaseModel` (or `dataclass`) — no SQLAlchemy mixins in this layer.
- Money amounts are stored and computed as `Decimal`, never `float`.
- Domain exceptions are distinct from HTTP exceptions — adapters translate them.
