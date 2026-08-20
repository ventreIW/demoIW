# BUG-04: plan

3 tasks, TDD order.

### T1: Regression test — pinning must persist and must matter (RED)
- Pinned generation returns 201 and stores `reference_date` as an ISO string.
- Omitted `reference_date` still returns 201 and stores null.
- Same seed + same pin → identical ageing; same seed + different pin → different ageing.
  (Criterion 3: a parameter that persists but changes nothing would satisfy criteria 1-2
  while still being useless.)
- Verify: `pytest tests/ -k reference_date` → **FAILS** with the JSON serialization error.
- Commit: `test(BUG-04): add regression test for pinned reference_date`

### T2: Serialize in JSON mode at the storage boundary (GREEN)
- `generate_dataset.py:55` → `params.model_dump(mode="json")`.
- Verify: T1 green; full backend suite green.
- Commit: `fix(BUG-04): dump generation params in JSON mode for the JSON column`

### T3: Full gate verification
- Verify: `pytest tests/` · `ruff check .` · `mypy app/`.
- Commit: `fix(BUG-04): verify gates green`
