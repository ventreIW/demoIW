# Epic Retrospective: E3 — Synthetic Dataset Generator

**Completed:** 2026-07-20
**Duration:** ~40 days (authorized 2026-06-10, closed 2026-07-20)
**Stories:** 4 delivered (s3.1–s3.4)

---

## Summary

E3 delivered the synthetic dataset generator: a seeded procedural layer (NumPy + Faker es_MX)
producing clients, invoices and payments, an OpenRouter-backed LLM enrichment layer for
qualitative attributes, a `POST /api/v1/scenarios/generate` endpoint with persistence, and a
frontend generation form. All four stories are merged, and the backend suite stands at 106
tests green with `ruff`, `ruff format` and `mypy app/` clean.

**E3 closes with one acceptance-gate item explicitly descoped, not fulfilled** — see below.
The qualitative half of the epic's premise has never executed against a real model.

## Acceptance gate — final status

| # | Commitment | Status |
|---|---|---|
| 1 | `seed=42` twice → same `client_count` and total outstanding | ✅ **Fulfilled** — verified by `tests/integration/test_scenario_acceptance_gate.py` (added at close; no test covered this before) |
| 2 | Scenario appears in `/scenarios` and can be activated | ✅ **Fulfilled** — same file, covers list → activate → active-switch |
| 3 | LLM enrichment runs (names are not raw Faker) | ⛔ **DESCOPED — not verified.** No `OPENROUTER_API_KEY` is available to the team. Owned by **s4.8** |
| 4 | All unit and integration tests pass | ✅ 106 backend + 45 frontend, green in CI |
| 5 | `mypy app/` and `npm run typecheck` pass | ✅ Both clean |
| 6 | ADR-003, ADR-004, ADR-005 written | ✅ All three |
| 7 | All 4 story retrospectives written | ✅ All four |

### Scope item corrected at close

The scope line *"'Generar nuevo' frontend form (sector, count, **overdue rate**, seed)"* was
stale. The form correctly sends `sector, client_count, invoice_volume, amount_mean, amount_std,
seed` and has no overdue-rate control, because **ADR-004** deliberately replaced the global
`overdue_rate` knob with per-pattern causal behaviour. The code is right; the scope was never
updated after the ADR. Corrected rather than ticked.

## The descoped item, and why it matters

E3's premise is procedural generation **plus** qualitative AI enrichment. The AI half has only
ever run against `respx` mocks.

The reason this went unnoticed for the whole epic is structural, and it is the most important
finding here:

- `OPENROUTER_API_KEY` defaults to `""` (`app/config.py:11`)
- `LLMEnrichmentService` degrades gracefully when the call fails
- `test_generate_scenario_llm_failure_graceful_degradation` asserts the endpoint still
  returns **201** on LLM failure

So with no key the system returns success and raw Faker company names. Every test passes, the
UI works, and the demo looks fine — until someone reads the company names. **Graceful
degradation with no visible signal is indistinguishable from success.**

This is not only an E3 problem. OpenRouter also backs **RF-04** (E5 assisted communications)
and **RF-06.3-4** (E6 NL query). Three of the six system modules depend on a credential the
team does not yet have, with the demo dated **2026-08-14**.

## What went well

- **Ports and adapters held.** `ILLMPort` / `IDatasetPort` let the entire epic be built and
  tested without a provider credential — the guardrail against vendor coupling worked exactly
  as intended. It is also what allowed the gap to hide.
- **ADR-004 improved the model mid-epic.** s3.1 review replaced global overdue knobs with
  per-pattern `_PatternProfile`, making labelled attributes *causal* rather than decorative —
  which is what makes the data learnable by E4's scoring engine.
- **Determinism was designed in.** Seeded RNG throughout, including UUIDs derived from the
  seeded generator rather than `uuid4()`, plus `reference_date` for cross-day reproducibility.
- **Batching decided deliberately.** ADR-005 (20 clients/batch) with a documented rationale
  rather than an arbitrary constant.

## What could be improved

- **The acceptance gate was never run.** All four stories closed with retrospectives while
  three of the epic's seven gate items sat unverified. Story-level "done" was mistaken for
  epic-level "fulfilled" — precisely the failure mode the epic-close scope re-read exists to
  catch. Two of the three were closeable in under an hour once someone actually looked.
- **CI never ran during the entire epic.** The workflow only triggered on `pull_request` while
  the team committed directly to `main`. E3's code accumulated 110 `ruff` violations, a
  component importing three modules that were never committed (build broken on `main`), and a
  test leaking a real `fetch` past teardown. All were found on 2026-07-20 when the repository's
  first PR triggered the first CI run. Fixed in PRs #1–#3.
- **Tests that do not test what they claim.** Two found during close:
  `test_llm_enrichment_service.py` snapshots `original_clients` "to compare later" and never
  compares it (so non-mutation is unverified); `ScenarioGrid`'s *"calls activateScenario when a
  card button is clicked"* only asserts `buttons.length === 2`. Both flagged for their authors
  rather than silently patched.
- **A dead endpoint shipped in the UI.** `GenerateScenarioForm` renders a "Descargar JSON"
  link to `/api/v1/scenarios/{id}/download`, which does not exist. Its test passes because it
  only checks the `href` string. Not in E3's scope — parked.
- **i18n regressed inside this epic.** s3.4 shipped `GenerateScenarioForm` with 27 hardcoded
  Spanish strings *after* `b15` established the i18n foundation. Tracked as s4.7.

## Patterns discovered

| ID | Pattern | Context |
|----|---------|---------|
| PAT-E3-1 | Seed all identifiers from the seeded RNG, never `uuid4()` | Any reproducible synthetic-data generator; `uuid4()` silently breaks determinism |
| PAT-E3-2 | Labelled attributes in synthetic data must be **causal**, not decorative | ADR-004; otherwise a downstream model learns an artefact of the generator |
| PAT-E3-3 | Graceful degradation needs a **visible signal** | A silent fallback is indistinguishable from success and can hide a dead subsystem for an entire epic |
| PAT-E3-4 | An acceptance gate that is never executed is documentation, not a gate | Verify gate items against observable state at close, not story-by-story |

## Process insights

- **Story-level green does not imply epic-level fulfilled.** Four stories with passing tests
  and written retrospectives coexisted with three unmet gate commitments. The mandatory scope
  re-read at epic close is what surfaced them; without it E3 would have closed claiming an
  AI capability nobody had observed working.
- **A gate that cannot run is not a gate.** CI existed from `d3d01e2` and never executed. Now
  triggered on pushes to `main` as well (PR #3).
- **Work tracked outside `work/epics/` is invisible to epic planning.** `b15-i18n-setup`
  shipped i18n on 2026-07-08; E9 was then written on 2026-07-13 planning the same work, and
  E4 s4.1 had planned it a third time. Reconciled in PR #4.

## Artifacts

- **Scope:** `work/epics/e3-synthetic-dataset-generator/scope.md`
- **Stories:** `work/epics/e3-synthetic-dataset-generator/stories/` (s3.1–s3.4, all with retrospectives)
- **ADRs:** ADR-003 (procedural + LLM hybrid), ADR-004 (pattern-driven behavioural model),
  ADR-005 (batched LLM enrichment)
- **Tests:** 106 backend (3 added at close for the acceptance gate), 45 frontend
- **Follow-ups created:** s4.8 (real-model enrichment verification, blocked on API key),
  s4.7 (i18n completion)

## Carried forward

| Item | Owner |
|---|---|
| Verify LLM enrichment against a real model | **s4.8** — blocked on `OPENROUTER_API_KEY` |
| Make missing-key / degraded enrichment visible instead of silent | s4.8 |
| i18n switcher + `GenerateScenarioForm` retrofit | s4.7 |
| Two tests that do not verify their claim | s3.3 / s2.x authors |
| Dead `/download` endpoint behind a UI button | `dev/parking-lot.md` |
