# BUG-03: plan

4 tasks, TDD order.

### T1: Regression test — upload must be usable, not merely accepted (RED)
- New test in `tests/test_csv_upload.py`: upload a ≥20-client CSV (above `MIN_CLIENTS`), then
  `GET /prioritized` and `GET /kpis` on the returned scenario id.
- Assert 200 on both, a non-empty case list, and that the portfolio's outstanding total equals
  the sum of the uploaded amounts — so the test fails if the invoices are merely *present*
  rather than *counted*.
- Verify: `pytest tests/test_csv_upload.py -k roundtrip` → **FAILS** with
  `InsufficientOutstandingError`.
- Commit: `test(BUG-03): add upload-to-prioritize roundtrip regression test`

### T2: Model invoice status as a domain type (GREEN, root cause)
- Add `InvoiceStatus(StrEnum)` to `app/domain/enums.py` with `OVERDUE = "overdue"` and
  `PAID = "paid"` — values unchanged from what is already persisted, so no migration.
- Route all five sites through it: `procedural_generator.py:129,158`,
  `feature_extractor.py:28-29`, and `sqlalchemy_scenario_repo.py:118`.
- CSV rows map to `InvoiceStatus.OVERDUE` — they are unpaid receivables, which is what the
  extractor's open branch means.
- Verify: `pytest tests/test_csv_upload.py` → T1 green; `pytest tests/` → full suite green.
- Commit: `fix(BUG-03): introduce InvoiceStatus enum as the single source of truth`

### T3: Make the misleading diagnostic tell the truth (REFACTOR)
- `outcome_labeller.py:55` claims "Every invoice in this scenario is settled" whenever
  outstanding is zero. That is one of several causes and was the wrong one here.
- Report what was actually observed — the distinct status values present and their counts — so
  an unrecognised value names itself instead of being misattributed.
- Verify: full suite green; deliberately re-inject a bad status locally and confirm the new
  message identifies it, then revert the injection.
- Commit: `fix(BUG-03): report observed statuses in InsufficientOutstandingError`

### T4: Full gate verification
- Verify: `pytest tests/` green · `ruff check .` clean · `mypy app/` clean.
- Confirm no Alembic migration is required (enum values match persisted data exactly).
- Commit: `fix(BUG-03): verify gates green`

## Done when (from scope.md)
1. upload → `/prioritized` 200, non-empty, outstanding equals uploaded sum · 2. `/kpis` 200
non-zero · 3. single source of truth for status · 4. no migration needed · 5. roundtrip test
exists · 6. suite green, nothing weakened.
