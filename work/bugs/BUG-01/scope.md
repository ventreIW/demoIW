# BUG-01: scope

**Reported:** 2026-08-20 · **Branch:** `bug/BUG-01/eslint-build-blocker` · **From:** `main`

WHAT:      `npm run build` fails. Next.js compiles successfully (31s), then the
           "Linting and checking validity of types" stage aborts with 11 ESLint
           errors across 7 files. The demo-readiness epic (E7) therefore has no
           working production build.

WHEN:      Every production build, on `main` and on every branch cut from it.
           Confirmed on `main` at `2fc1501` during s7.1 T5, and re-confirmed on
           `main` at `35d956d` (2026-08-20). Independent of s7.1.
           NOT triggered in dev (`next dev`) or in the test suites, which is why
           151/151 frontend tests pass while the build is red.

WHERE:     8 errors parked from s6.2 (2026-08-11), 3 added by s7.2:
           - src/app/[locale]/executive/__tests__/page.test.tsx:34,36,45  no-explicit-any
           - src/components/executive/KpiCard.tsx:56                     no-explicit-any
           - src/components/executive/SegmentationChart.tsx:50           no-explicit-any
           - src/components/executive/SegmentationChart.tsx:45           no-unused-vars ('number')
           - src/components/executive/__tests__/KpiCard.test.tsx:2       no-unused-vars ('vi')
           - src/components/executive/__tests__/SegmentationChart.test.tsx:2 no-unused-vars ('vi')
           - src/components/__tests__/a11y-scan.test.tsx:5               no-unused-vars ('caseDetailFixture')
           - src/test-utils/a11y.tsx:25                                  no-unused-vars ('container')

EXPECTED:  `npm run build` exits 0 and emits a production bundle, with no ESLint
           rule suppressions introduced to achieve it.

Done when: 1. `npm run build` exits 0 from `frontend/`.
           2. `npx next lint` reports 0 errors.
           3. `npx tsc --noEmit` reports 0 errors.
           4. 151/151 frontend tests still pass (no test weakened or deleted).
           5. No `eslint-disable`, no `@ts-ignore`, and no rule downgraded in
              `eslint.config.mjs` — each `any` is replaced with a real type.
