# BUG-01: scope

**Reported:** 2026-08-20 · **Branch:** `bug/BUG-01/eslint-build-blocker` · **From:** `main`

WHAT:      `npm run build` fails. Next.js compiles successfully (31s), then the
           "Linting and checking validity of types" stage aborts with 10 ESLint
           errors across 7 files. The demo-readiness epic (E7) therefore has no
           working production build.

WHEN:      Every production build, on `main` and on every branch cut from it.
           Confirmed on `main` at `2fc1501` during s7.1 T5, and re-confirmed on
           `main` at `35d956d` (2026-08-20). Independent of s7.1.
           NOT triggered in dev (`next dev`) or in the test suites, which is why
           the frontend test suite passes while the build is red.

WHERE:     10 errors total — 8 from s6.2 (a717c42, 2026-08-07), 2 from s7.2 (1ff30fe, 2026-08-14).
           (E7 scope.md records these as "8 + 3 = 11"; the actual count is 8 + 2 = 10.)
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
           4. Frontend test suite still fully passes (no test weakened or deleted).
           5. No `eslint-disable`, no `@ts-ignore`, and no rule downgraded in
              `eslint.config.mjs` — each `any` is replaced with a real type.

TRIAGE:
  Bug Type:    Regression
  Severity:    S1-High
  Origin:      Code
  Qualifier:   Incorrect

  Rationale:
  - Regression, not latent defect. `git log --diff-filter=A` places 8 of the 11 errors in
    `a717c42` (s6.2, 2026-08-07) and 3 in `1ff30fe` (s7.2, 2026-08-14). The production build
    has been red for 13 days and no story since has been able to produce a bundle.
  - S1 not S0: `next dev` and both test suites are unaffected (151/151 frontend tests pass),
    so the demo is still runnable in dev. It is S1 rather than S2 because E7's entire purpose
    is demo readiness and "no production build" contradicts the epic's done-criteria.
  - Origin=Code: `eslint.config.mjs` is correct and unchanged; the source violates it. Nothing
    is wrong with the environment or the configuration.
  - Qualifier=Incorrect is the dominant half, though the set is mixed: 5 errors are `any`
    type-lies (Incorrect — a declared type that does not describe the data) and 6 are unused
    bindings (Extraneous). The Incorrect subset is the consequential one: it sits in shipped
    components (`KpiCard.tsx`, `SegmentationChart.tsx`), and it is the reason s6.2 parked the
    errors rather than sweeping them — replacing `any` requires real typing decisions.

  Jira fields: not set — no backlog adapter configured (`.raise/backlog.yaml` absent).
                Run rai-backlog-setup and add custom_fields.Bug to enable.
