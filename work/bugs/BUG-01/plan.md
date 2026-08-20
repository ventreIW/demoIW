# BUG-01: plan

4 tasks, TDD order. Manifest commands: `scripts/{test,lint,typecheck,format-check}.sh`.

**Note on "regression test":** this bug has no runtime behaviour to assert, so the regression
test is not a new spec file — it is the *gate itself*. `npm run build` already reproduces the
failure deterministically; what does not exist is anything that runs it. T1 therefore installs
the guard, and the RED state is the guard failing against the unfixed tree.

---

### T1: Install the missing build gate (RED)
- Add `- run: npm run build` to the frontend job in `.github/workflows/ci.yml`, after `lint`.
- This is the fix for the *root cause* (no enforcing gate), not for the symptom, so it lands
  first and must be seen failing before anything is repaired.
- Verify: `cd frontend && npm run build` → **exits non-zero**, 10 errors. Guard proven live.
- Commit: `test(BUG-01): add build gate to CI frontend job`

### T2: Replace the 5 `no-explicit-any` type-lies (GREEN, part 1)
- All five are the same shape: a next-intl message key widened to `string` then cast at the
  `t()` call. Use the key type next-intl already derives — `Parameters<typeof t>[0]` — and
  annotate the prop/lookup, deleting the cast rather than relocating it.
  - `src/components/executive/KpiCard.tsx:56` — type the `label` prop.
  - `src/components/executive/SegmentationChart.tsx:50` — type `DIMENSION_KEY`'s value.
  - `src/app/[locale]/executive/__tests__/page.test.tsx:34,36,45` — type the `es.json`
    namespace walk and the `Link` mock's props (`ComponentProps<'a'>`).
- Constraint: no `eslint-disable`, no `@ts-ignore`, no rule downgrade in `eslint.config.mjs`.
- Verify: `cd frontend && npx eslint . --rule '{"@typescript-eslint/no-explicit-any":"error"}'`
  → 0 `no-explicit-any` errors; `npm run typecheck` → clean.
- Commit: `fix(BUG-01): replace any-casts on next-intl keys with derived key types`

### T3: Remove the 5 dead bindings (GREEN, part 2)
- `SegmentationChart.tsx:45` — `number` formatter assigned, never read. Delete the binding, and
  delete `getNumberFormatter` too if it becomes unreferenced (check before removing).
- `KpiCard.test.tsx:2`, `SegmentationChart.test.tsx:2` — drop `vi` from the import list.
- `a11y-scan.test.tsx:5` — drop the unused `caseDetailFixture` import.
- `test-utils/a11y.tsx:25` — stop destructuring `container`; `axe.run` targets `document`, so
  call `renderWithIntl(ui, …)` for its side effect only.
- Constraint: deletions only. If a binding turns out to be *load-bearing* (i.e. removing it
  changes a test's meaning), stop and report rather than deleting the assertion around it.
- Verify: `cd frontend && npm run lint` → **0 problems**; `npm test -- --run` → suite green,
  same test count as before this task.
- Commit: `fix(BUG-01): remove unused bindings flagged by no-unused-vars`

### T4: Full gate verification (GREEN, closing)
- Run every gate the CI job runs, in CI order, plus the build.
- Verify — all four must pass from `frontend/`:
  - `npm run typecheck` → 0 errors
  - `npm run lint` → 0 problems
  - `npm test -- --run` → suite green, no test deleted or weakened
  - `npm run build` → **exits 0**, bundle emitted (the T1 guard now green)
  - and from the repo root: `bash scripts/lint.sh` → backend `ruff` now actually reaches
    execution (it has been masked by the red frontend half since 2026-08-07)
- Commit: `fix(BUG-01): verify all gates green — build restored`

---

## Done when (from scope.md)
1. `npm run build` exits 0 · 2. lint 0 errors · 3. tsc 0 errors ·
4. test suite fully passes, nothing weakened · 5. zero suppressions introduced.
