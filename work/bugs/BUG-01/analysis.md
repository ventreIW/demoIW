# BUG-01: analysis

## Method: 5 Whys (single causal chain, each answer evidenced)

Chosen over hypothesis-driven because the *location* of the defect was never in doubt —
the compiler prints it. The open question was why a red build survived 13 days, which is a
causal-chain question, not a search question.

## The chain

**1. Why does `npm run build` fail?**
Next.js compiles successfully (31s), then the lint stage reports 10 errors in 7 files and
aborts. Evidence: build output on `bug/BUG-01/eslint-build-blocker`.

**2. Why are those errors in the tree?**
`a717c42` (s6.2, 2026-08-07) introduced 8; `1ff30fe` (s7.2, 2026-08-14) introduced 2.
Evidence: `git log --diff-filter=A` on each offending file.

**3. Why did those stories merge with a failing lint gate?**
Because the gate that should have blocked them was *already* failing. A newly-introduced
failure is indistinguishable from the pre-existing one when both surface as "CI red".
Evidence: `gh run list` — six consecutive `failure` runs on `main` (2026-08-07 → 2026-08-15),
last `success` 2026-08-05, exactly straddling `a717c42`.

**4. Why was a permanently failing CI tolerated?**
s6.2 made an explicit decision to *park* its 8 errors, recorded in the E6 pull-board as
"No barridos: sustituir any implica decisiones de tipado dentro de la implementación de otra
historia." That decision was locally reasonable but had a global effect: it converted a hard
binary gate into a known-red baseline. A baseline that is always red carries zero information,
so every subsequent story lost its lint signal — which is precisely how s7.2 added two more
without noticing.

**5. Why could a known-red baseline persist undetected across two epics?**
Nothing in the workflow distinguishes "red for the accepted reason" from "red for a new
reason", and the tool meant to enforce gates locally cannot fail. Verified this session:
`rai gate check --all --scope backend` printed `FAILED: 5 of 15 gates failed` and then
`[exited with code 0]`. Both the local gate and the remote gate were incapable of stopping a
merge — one by exit code, the other by normalization.

## Root cause

**The project has no enforcing quality gate.** Parking lint errors in s6.2 disabled the only
signal that worked (CI), and `rai gate check` cannot fail by construction. The 10 errors are
the symptom; the absent gate is the cause. Fixing only the errors restores the build but
leaves the mechanism that allowed 13 days of red CI fully intact.

Note this is *not* "the developers should have looked at CI" — human error is not a root cause.
The question is why not-looking was possible, and the answer is that looking would have been
uninformative: red was the expected state.

## Contributing factors

- **`npm run build` is absent from CI entirely.** `.github/workflows/ci.yml` runs `typecheck`,
  `lint`, and `test`, but never builds. Even with lint green, nothing proves a bundle can be
  produced — which is E7's actual done-criterion (NFR-04, installable PWA).
- **`main` is 11 commits ahead of `origin/main`.** Every commit since 2026-08-15 — all of s7.1,
  including the PWA service worker — has had no CI run of any kind.
- **`scripts/lint.sh` masks the backend** (`set -e`, frontend first): while frontend lint is red,
  `ruff` never executes. Already parked; still true.

## Fix approach

Replace all 10 violations with real types and real deletions — no `eslint-disable`, no
`@ts-ignore`, no rule downgrade — then close the gate gap by adding `npm run build` to the
frontend CI job so the E7 done-criterion is enforced rather than assumed.

The five `no-explicit-any` sites are all the same underlying shape: a next-intl message key
being passed to `t()` as a widened `string`. The correct type is the one next-intl already
derives, reachable as `Parameters<typeof t>[0]` — so the fix is a type annotation, not a cast.
