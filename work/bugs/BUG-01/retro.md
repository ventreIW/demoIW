# BUG-01: retrospective

## Summary
- **Root cause:** the project has no enforcing quality gate. s6.2's decision to park 8 lint
  errors converted CI from a binary gate into a known-red baseline carrying zero signal, and
  `rai gate check` exits 0 even while printing `FAILED: 5 of 15 gates failed`.
- **Fix approach:** eliminate all 10 violations with real types and real deletions (zero
  suppressions), then add `npm run build` to CI so E7's actual done-criterion is enforced.
- **Classification:** Regression / S1-High / Code / Incorrect

## What the fix actually found

Three things that were not visible from the error list:

1. **Two of the five `any` casts were never necessary.** This project has no `IntlMessages`
   type augmentation, so next-intl's `t()` already accepts `string`. s6.2 cast against a
   constraint that did not exist — and `SegmentationChart`'s `DIMENSION_KEY` was *already*
   correctly typed to the three literal chart keys. The "typing decisions inside another
   story's implementation" that justified parking the errors were not required at all.
   The park was more expensive than the fix.

2. **One "unused import" was a fossil, not dead weight.** `caseDetailFixture` was unused in
   `a11y-scan.test.tsx` because `CaseDetail.tsx` — a primary operator surface — was never
   scanned. s7.2's "9 components, 0 AA violations" had a hole in it. Deleting the import, the
   obvious lint fix, would have destroyed the only remaining evidence of the omission. Added
   the missing scan instead; it passes clean, so the gap was in coverage, not in accessibility.

3. **The backend lint gate was concealing nothing.** Once the frontend half went green,
   `scripts/lint.sh` completed end-to-end for the first time since 2026-08-07 and `ruff`
   reported clean. The `set -e` masking was a real defect, but it happened not to be hiding
   a second one.

## Process Improvement

**Prevention:** a gate that is allowed to stay red stops being a gate. The specific change
is the one made in T1 — `npm run build` now runs in CI — but the general rule is that parking
a gate failure must be paired with a mechanism that distinguishes "red for the known reason"
from "red for a new reason". This project had no such mechanism, so s7.2 added two errors into
an already-red gate without anyone being able to notice. Either fix the failure, or pin it
(baseline file / targeted `eslint-disable` with an issue reference) so the gate returns to
green and can fail again meaningfully. Parking without pinning is what caused this.

**Pattern:** `Bug Type=Regression` + `Origin=Code` + a deliberate parking decision upstream
→ the defect is never in the parked code, it is in the *signal* the parking destroyed. Look
for the second defect that entered while the gate was dark. Here it was s7.2's two errors and
an unscanned component.

**Second finding, not fixed here:** 13 files fail `npm run format:check`, verified pre-existing
at the branch point `35d956d` and untouched by this bug. `format:check` is in the manifest as
`format_command` but is absent from `.github/workflows/ci.yml`, so it is a gate nobody runs —
the same pathology as BUG-01 one layer down. Deliberately not swept into this fix; recorded for
its own bug so the diff stays one logical change.

## Heutagogical Checkpoint

1. **Learned:** CI on this repo gates pushes to `main` as well as PRs (added after PRs #1–#2
   let 112 violations accumulate), which means the six red runs since 2026-08-07 were visible
   the whole time and simply carried no information. Also learned that `main` is 11 commits
   ahead of `origin/main` — all of s7.1, including the PWA service worker, has never had a CI
   run at all, so "CI is red" understates it: recent work is untested rather than failing.

2. **Process change:** reproduce, then check the *gate's own health* before believing any gate
   result. I ran `rai gate check` first and it returned exit 0 while reporting 5 of 15 gates
   failed; treating that as a pass would have ended this bug before it started. Verify the
   verifier.

3. **Framework improvement:** `rai gate check` returning 0 on reported failures is the
   highest-value RaiSE fix visible from this project — it makes a broken gate indistinguishable
   from a passing one, which is precisely the failure class BUG-01 is about. Worth reporting
   upstream; it affects any RaiSE project with a nested structure. Second: `--scope backend`
   from the repo root breaks `gate-tests` (`ERROR: file or directory not found: backend`,
   because pytest's rootdir is already `backend/`), so the invocation recorded in project
   memory as "correct" is itself wrong.

4. **Capability gained:** can now distinguish a lint error that is noise from one that is a
   fossil of missing work — the `caseDetailFixture` case. The tell is asking what the binding
   was *for* before deleting it.

## Patterns

Three patterns were submitted and **none persisted**:

1. A gate allowed to stay red stops being a gate — park without pinning destroys the signal,
   so look for the second defect that entered while the gate was dark. (process)
2. Verify the verifier: `rai gate check` exits 0 while printing `FAILED: N of M`. (process)
3. An unused import can be a fossil, not dead weight — ask what a flagged binding was *for*
   before deleting it. (codebase)

- **Added: none, despite three apparent successes.** `rai pattern add` printed the accepted
  content and context for all three and exited cleanly, but nothing was written: there is no
  `.raise/rai/raise.db`, no `patterns.jsonl`, and no new file anywhere under `.raise/`.
  Verified by `find .raise -name "*.jsonl" -newermt "-1 hour"` → empty.

  This is the same failure shape as the bug being retrospected: **a tool reporting success
  while doing nothing.** Memory has recorded the pattern store as "write-only" for three
  consecutive epics; that description is too generous — it is not writing at all, and the
  silent success is why three epics of `rai pattern add` calls went unnoticed. The three
  insights above are therefore preserved *in this file only*, which is now the actual store.

- **Reinforced: none evaluated** — session start returned zero patterns from PRIME
  (`rai graph query` still fails with `no such column: data_json`, third epic running).
