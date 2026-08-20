# BUG-03: analysis

## Method: Producer/consumer vocabulary audit

The reproduction named the value immediately, so the useful question was not "where" but
"who else writes this field, and do they agree?" Enumerating every producer and consumer of
`InvoiceORM.status` gives the whole picture in one table.

## Every site that touches invoice status

| Role | Location | Vocabulary | Declared where |
|---|---|---|---|
| Producer (generated) | `procedural_generator.py:129` | `"overdue"` | inline literal |
| Producer (generated) | `procedural_generator.py:158` | `"paid"` | inline literal |
| Producer (**CSV**) | `sqlalchemy_scenario_repo.py:118` | **`"pending"`** | inline literal |
| Consumer (open) | `feature_extractor.py:28` | `"overdue"` | module constant `_OPEN_STATUS` |
| Consumer (settled) | `feature_extractor.py:29` | `"paid"` | module constant `_SETTLED_STATUS` |
| Storage | `models.py:77` | `Mapped[str]`, `String(20)` | no constraint |

Three producers, two consumers, five independent declarations of the same vocabulary, and
**zero shared definition**. The generated path works only because two literals happen to
match two other literals.

## Root cause

**Invoice status was never modelled as a type.** `app/domain/enums.py` defines StrEnums for
eight domain concepts — Sector, ScenarioStatus, PaymentPattern, ScoreCategory, Channel, Tone,
CommunicationStatus, ContactResultType — and invoice status is not one of them, despite being
the field the entire scoring pipeline pivots on. The column is a bare `String(20)` with no
constraint.

With no type to violate, `create_from_csv` was free to write `"pending"`, which is a perfectly
reasonable word for an unpaid invoice and simply not the word this codebase uses. No reviewer,
type checker, linter, or database constraint could have flagged it.

This is the same underlying failure as BUG-02 — a value with no single source of truth — but
one stage earlier. In BUG-02 an enum existed and a hand-written copy drifted from it. Here the
enum was never created, so there was nothing to drift *from*. Both were found the same way:
asking which value a comparison expects and who guarantees it.

## Why the failure is silent then explosive

The extractor's two branches partition on equality against distinct literals:

    open_invoices = invoices[invoices["status"] == "overdue"]
    settled       = invoices[invoices["status"] == "paid"]

A third value is not an error — it simply matches neither mask, so it vanishes from both
sides. Every CSV invoice disappears, outstanding sums to zero, and the failure finally
surfaces much later in `outcome_labeller.py:55` as `InsufficientOutstandingError` with the
message *"Every invoice in this scenario is settled."*

That message encodes an assumption that the only way to have no outstanding balance is for
everything to be paid. It is false here and sends the reader to the payments logic, several
layers from the actual defect.

## Why it was never caught

`tests/test_csv_upload.py` has four tests: valid upload → 201, missing columns → 422, empty
file → 422, malformed → 422. All four assert on the *upload response*. None asks whether the
persisted scenario can then be scored. The CSV feature is verified up to the moment of writing
and not one step past it — so the bug lives entirely in the gap between "it saved" and "it
works", which no test spans.

## Fix approach

Introduce `InvoiceStatus(StrEnum)` with values `"overdue"` and `"paid"` — the values already
on disk, so no data migration is needed — and route all five sites through it. Map CSV rows to
`InvoiceStatus.OVERDUE` (they are unpaid receivables, which is what the open branch means).
Correct the misleading `InsufficientOutstandingError` message so a future third value reports
itself instead of blaming settlement. Add the end-to-end upload → prioritize test that the
existing suite never had.
