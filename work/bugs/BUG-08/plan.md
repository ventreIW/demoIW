# BUG-08: plan

4 tasks, TDD order. (Written alongside execution; recorded here for the lifecycle record.)

### T1: NFR-06 regression test (RED)
Four tests: a draft records all four mandated fields; the operator default is a
self-describing placeholder; the send stamps its own `sent_at` and preserves provenance
across the status transition; `model_used` matches the configured model rather than a
hardcoded string.
- Verify: `pytest tests/test_nfr06_auditability.py` → **4 failed**. ✅
- Commit: `test(BUG-08): add NFR-06 auditability regression tests`

### T2: Widen the record (schema + entity + mappers + migration 0005)
Four nullable columns, indexed on `operator_id` and `sent_at`. Nullable is deliberate:
pre-existing rows do not know their provenance.
- Verify: `ruff`, `mypy` clean. ✅
- Commit: folded into the T3 commit.

### T3: Propagate provenance at both seams
Draft service exposes `model` and `prompt_version` (derived from the template filename);
the use case reads them off the service; the router reads `X-Operator-Id`; the send handler
stamps `sent_at`; the API response surfaces all four.
- Verify: `pytest tests/test_nfr06_auditability.py` → **4 passed**. ✅
- Commit: `fix(BUG-08): implement NFR-06 auditability`

### T4: Full gates, both stacks
- Verify: backend 562 passed / 3 skipped / 1 xfailed, ruff check + format + mypy clean;
  frontend typecheck, lint, format, 207 tests, build. ✅
