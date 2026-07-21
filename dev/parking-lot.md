# Parking Lot

Ideas not ready for the backlog. No commitment, no timeline. Review at each epic close.

Items that get scoped move to `governance/backlog.md`.

---

| Date added | Idea | Why parked |
|---|---|---|
| 2026-06-10 | Simulation mode — replay scenario over time (show recovery progression day by day) | High demo value, high complexity. Revisit after core modules ship. |
| 2026-06-10 | Webhook integration to external email/WhatsApp services | Out of demonstrative scope per restrictions. No real sends in demo. |
| 2026-06-10 | Multi-tenant / multi-organization support | Demonstrative scope is single-org. Future product direction only. |
| 2026-06-10 | Custom ML model training UI (upload training data, retrain in-browser) | Complex, not needed for demo conviction. |
| 2026-07-02 | RaiSE framework: `rai session start` should sync/verify backend venv against `requirements.txt` | Found in s3.1 — venv was missing `python-multipart` (committed in s2.5) and had no `pip`; only surfaced on a test import failure. |
| 2026-07-02 | RaiSE framework: fix orphaned-test check diff range in `rai-story-implement` | Uses reversed `git diff HEAD...$base`, producing false positives (flagged s3.1's own new test). Correct form: `git diff --name-only main...HEAD`. |
| 2026-07-20 | Process: make `work/backlog/` items visible to epic planning | i18n got planned three times — as E4 s4.1, as epic E9, and as backlog item `b15-i18n-setup`, which is the one that actually shipped (2026-07-08). E9 was written 5 days *later*, describing already-merged work and naming pages that do not exist. Root cause: backlog items live outside `work/epics/`, so epic planning has no view of them. Options: index delivered backlog items in the epic tracker, or require a codebase check (`rai graph query`) before writing an epic brief. |
| 2026-07-21 | `GenerateDataset` bypasses `IDatasetPort` | The use case imports and instantiates `ProceduralGenerator` directly (`app/application/use_cases/generate_dataset.py`) instead of receiving `IDatasetPort` by injection. The port exists but is unused for the generator, so the application layer depends on a concrete adapter — the coupling the hexagonal structure is meant to prevent. Found during s4.2 gemba; out of scope there. Small fix: inject via `container.py` like the repositories. |
| 2026-07-20 | Intermittent frontend test failure — 1 failure in ~30 runs, not reproduced | Observed once during E3 close: `Test Files 1 failed \| 9 passed`, `Tests 1 failed \| 44 passed`. Then 27 consecutive clean runs; the failing test name was not captured. Same suite already produced one confirmed async leak (`ScenarioGrid` fetch past teardown, fixed in PR #1), so a second unfixed race is plausible — `GenerateScenarioForm`'s async tests are the likeliest candidate. Watch CI; if it recurs, capture with `vitest --run --reporter=verbose` and check for un-awaited promises / missing `await waitFor`. |
| 2026-07-20 | Dead `/api/v1/scenarios/{id}/download` endpoint behind a live UI button | `GenerateScenarioForm` renders a "Descargar JSON" link to an endpoint that does not exist — clicking it 404s. Its test passes because it only asserts the `href` string, never that the route resolves. Found at E3 close; not in E3 scope. Either implement the export or remove the button. |
| 2026-07-20 | Guard against untranslated UI shipping after i18n landed | `GenerateScenarioForm.tsx` (s3.4) shipped 27 hardcoded Spanish strings and a fixed `toLocaleDateString('es-MX')` after `b15` established i18n. Nothing flagged it. Consider an ESLint rule for literal user-facing strings in JSX, or a review-checklist item. Retrofit tracked as E4 s4.7. |
