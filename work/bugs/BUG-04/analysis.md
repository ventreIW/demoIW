# BUG-04: analysis

## Method: Stack trace analysis

The exception names the type and the operation, so following it back to the producing call was
a two-hop trace.

## The path

1. `StatementError: (builtins.TypeError) Object of type date is not JSON serializable`
   — raised by SQLAlchemy at flush, serializing a bind parameter.
2. The bound column is `ScenarioORM.parameters`, declared `Mapped[dict[str, Any]] =
   mapped_column(JSON, default=dict)` (`models.py:17`).
3. Its value comes from `generate_dataset.py:55`, `parameters=params.model_dump()`.
4. `GenerationParams.reference_date` is typed `date | None`
   (`generation_params.py:26`).

`BaseModel.model_dump()` defaults to `mode="python"`, which preserves field values as their
Python objects — a `date` stays a `date`. `mode="json"` is the overload that coerces to
JSON-compatible primitives, rendering `date` as an ISO-8601 string.

## Root cause

**A Python-mode dump was written into a JSON column.** `model_dump()` and `model_dump(mode=
"json")` differ in exactly the property that matters at a storage boundary, and the defaulting
one is the one that does not satisfy it. The call site reads as obviously correct — it is the
default overload of a standard method — which is why it survived review.

The bug is latent for every field whose Python and JSON representations coincide. `seed` is an
`int`, `sector` a `StrEnum`, and the three amounts are floats; all pass through Python-mode
dump unharmed. `reference_date` is the only field in `GenerationParams` whose representations
differ, so it is the only one that fails — and it is optional and defaults to `None`, so the
failing path is off by default.

That is why a defect on the very first line of the persist call has never been hit: the
codepath requires the caller to opt into the one field that exposes it.

## Contributing factor

`params.model_dump()` is also the only record of how a scenario was generated. Because pinning
crashes, every scenario in the system was necessarily generated with `reference_date: null`,
which resolves to `date.today()` at generation time (`procedural_generator.py:48`). The stored
parameters therefore do not capture the "today" anchor that was actually used, and re-running
a stored parameter set on a different day produces different ageing. The bug has been quietly
guaranteeing the non-reproducibility the field exists to prevent.

## Fix approach

Use `params.model_dump(mode="json")` at the persist call, so `date` serializes to ISO-8601 and
every other field is unchanged. Add a test that pins the date, asserts a 201 and an ISO string
in the persisted parameters, and — because criterion 3 is the point of the field — asserts that
two identical pinned generations age identically while a different pin ages differently.
