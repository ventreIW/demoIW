# BUG-05: plan

**Decision (2026-08-20, Rodrigo):** stable ordinal column. Identity stays a random surrogate
key owned by persistence; *ordering* becomes an explicit, persisted, reproducible property
owned by the domain. Recorded as ADR-011.

Rejected alternatives and why:
- **Honour the domain id** — smallest diff and matches the stated intent in three places, but
  two generations with the same seed then produce identical client UUIDs and collide on the
  primary key. Same-seed regeneration is currently legal and exercised by the suite.
- **Order-free labelling** (per-client sub-seeds) — most robust, but changes the labelling
  mathematics and therefore invalidates ADR-006/007's measured ROC-AUC figures (0.732–0.739),
  which would have to be re-measured before the numbers in those ADRs could stand.

5 tasks, TDD order.

### T1: Regression test — same params must produce the same portfolio (RED)
- Generate twice with identical params; compare the per-`client_id` score map and the category
  distribution. Ids differ by design, so compare the *multiset of scores* and the category
  tally, not the ids.
- Assert non-empty first, so an empty portfolio fails rather than passing vacuously (BUG-02).
- Verify: `pytest -k reproducible` → **FAILS** intermittently on today's code. Run it several
  times: the defect is a permutation effect, so a single pass proves nothing.
- Commit: `test(BUG-05): add scoring reproducibility regression test`

### T2: Add the ordinal to the model and a migration
- `ClientORM.generation_index: Mapped[int]` — the client's position in its scenario's
  generation sequence.
- Alembic migration `0004`: add the column, backfill deterministically for existing rows,
  then make it non-nullable.
- Verify: `alembic upgrade head` applies; `alembic downgrade -1` reverses cleanly.
- Commit: `feat(BUG-05): add generation_index to ClientORM with migration 0004`

### T3: Persist the ordinal on both write paths
- `add_many` assigns `generation_index` from list position — the list *is* the generation
  order, produced by `ProceduralGenerator` and preserved by `GenerateDataset`.
- `create_from_csv` assigns it from CSV row order.
- `get_raw_dataset` returns the column so the labeller can use it.
- Verify: full suite green.
- Commit: `fix(BUG-05): persist generation_index on both write paths`

### T4: Order the labeller by the ordinal instead of the surrogate key (GREEN)
- `outcome_labeller.py` → `clients.sort_values("generation_index")`.
- Add a comment stating why: a seeded draw applied along an unseeded axis is not seeded.
- Verify: T1 green, and green on repeated runs (≥5) — one pass is not evidence for a
  permutation bug.
- Commit: `fix(BUG-05): order the outcome draw by generation_index, not the random id`

### T5: ADR + full gates
- `dev/decisions/adr-011-scoring-reproducibility.md` — which layer owns identity vs ordering.
- Verify: `pytest tests/` · `ruff check .` · `mypy app/`.
- Commit: `docs(BUG-05): ADR-011 identity vs ordering ownership`
