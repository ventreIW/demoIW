# BUG-04: scope

**Reported:** 2026-08-20 · **Branch:** `bug/BUG-04/reference-date-persist` · **From:** `main`

WHAT:      Generating a scenario with `reference_date` pinned crashes at persist:
             `StatementError: (builtins.TypeError) Object of type date is not JSON serializable`
           The scenario is not saved. Omitting `reference_date` works, so the single
           documented mechanism for cross-day reproducibility is the one thing that fails.

WHEN:      Every `POST /api/v1/scenarios/generate` whose body includes a non-null
           `reference_date`. Reproduced 2026-08-20 on `main` at the BUG-03 merge with
           `reference_date: "2026-06-01"`.

WHERE:     `backend/app/application/use_cases/generate_dataset.py:55`
             `parameters=params.model_dump()`
           `model_dump()` defaults to Python mode and returns `reference_date` as a live
           `datetime.date`. It is written to `ScenarioORM.parameters`, which is
           `Mapped[dict[str, Any]] = mapped_column(JSON)` (`models.py:17`), and the JSON
           serializer rejects `date`.

           Field declared at `app/domain/value_objects/generation_params.py:26` as
           `reference_date: date | None`, documented "pin it for cross-day reproducibility".

EXPECTED:  A pinned `reference_date` persists as an ISO-8601 string and round-trips, so the
           parameters that produced a scenario are recoverable from the stored record.

Done when: 1. `POST /generate` with `reference_date` pinned returns 201.
           2. The persisted `parameters` contains `reference_date` as an ISO date string.
           3. Ageing actually honours the pin: two scenarios generated with the same seed and
              the same pinned date produce identical `days_overdue`, and a different pinned
              date produces different ageing — so the parameter demonstrably does its job.
           4. Omitting `reference_date` still works and stores null.
           5. Every other value in `parameters` still round-trips (`sector` included).
           6. Full backend suite green; no test weakened or deleted.

TRIAGE:
  Bug Type:    Data
  Severity:    S2-Medium
  Origin:      Code
  Qualifier:   Incorrect

  Rationale:
  - Data: the defect is in the serialization of a value on its way to storage. The request is
    valid, the domain object is correct, and only the persisted representation is wrong.
  - S2: the default path (`reference_date` omitted) works, so the demo is not blocked today.
    It is not S3 because it makes reproducibility-across-days unusable — and reproducibility
    is exactly what is under scrutiny in BUG-05, where the same generator is producing
    different results for the same seed.
  - Origin=Code: Pydantic offers `mode="json"` precisely for this; the wrong overload was
    chosen. The model and the column are both correct.
  - Qualifier=Incorrect: a value is produced in the wrong representation, not omitted.

  Jira fields: not set — no backlog adapter configured (`.raise/backlog.yaml` absent).
