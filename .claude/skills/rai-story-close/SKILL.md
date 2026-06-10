---
allowed-tools:
- Read
- Edit
- Write
- Grep
- Glob
- Bash(rai:*)
- Bash(git:*)
description: Merge story branch to dev and update tracking. Use after story review.
license: MIT
metadata:
  raise.adaptable: 'true'
  raise.fase: '8'
  raise.frequency: per-story
  raise.gate: ''
  raise.inputs: '- retrospective_md: file_path, required, previous_skill

    - tests_passing: boolean, required, cli

    - dev_branch: string, required, config

    '
  raise.next: ''
  raise.outputs: '- merge_commit: string, git

    '
  raise.prerequisites: story-review
  raise.version: 3.0.0
  raise.visibility: public
  raise.work_cycle: story
name: rai-story-close
raise.mastery:
  ha: Skip epic update for standalone stories
  ri: Integrate with CI/CD pipelines, automate cleanup workflows
  shu: Follow all steps, verify retrospective, merge locally, update epic
---

# Story Close

## Purpose

Complete a story by verifying the retrospective, merging locally to the development branch, and updating epic tracking. Remote push and merge requests happen at epic level (see `/rai-epic-close`).

## Mastery Levels (ShuHaRi)

See `raise.mastery` in frontmatter.

## Context

**When to use:** After `/rai-story-review` retrospective is complete. Story is verified and tests pass.

**When to skip:** Story abandoned (document why, delete branch without merge, update epic as "Abandoned").

**Inputs:** Completed retrospective, passing test suite, story branch ready for merge.

**Branch config:** Read `branches.development` from `.raise/manifest.yaml` for `{dev_branch}`. Default: `main`.

## Steps

### Step 0: Instrument

```bash
rai signal emit-work story "{story_id}" --event start --phase close 2>/dev/null || true
```

### Step 1: Verify Retrospective & All Gates

> **Token marker** — Call `raise_session_topic(kind="close", topic="verify")` before executing this step.

```bash
RETRO="work/epics/e{N}-{name}/stories/{story_id}-retrospective.md"
[ -f "$RETRO" ] && echo "✓ Retrospective" || echo "ERROR: Run /rai-story-review first"
```

**Skip gate if already ran this session on the same commit** (S3008.5 — saves ~1,700 tokens):

```bash
LAST=$(rai signal query story "{story_id}" \
    --event complete --phase implement \
    --session-id "${RAISE_CC_SESSION_ID}" \
    --latest --fields commit,timestamp 2>/dev/null)
LAST_COMMIT=$(echo "$LAST" | grep "^commit=" | cut -d= -f2)
LAST_TS=$(echo "$LAST" | grep "^timestamp=" | cut -d= -f2)
HEAD=$(git rev-parse HEAD)

if [ -n "$LAST_COMMIT" ] && [ "$LAST_COMMIT" = "$HEAD" ] && [ -n "$LAST_TS" ]; then
    ELAPSED=$(python3 -c "
from datetime import datetime, timezone
ts = datetime.fromisoformat('$LAST_TS'.replace('Z','+00:00'))
print(int((datetime.now(timezone.utc) - ts).total_seconds()))
" 2>/dev/null)
    if [ -n "$ELAPSED" ] && [ "$ELAPSED" -lt 7200 ]; then
        MINS=$((ELAPSED / 60))
        echo "✓ Gates skipped — implement/complete ran ${MINS}m ago on commit ${HEAD:0:9} (no changes since)"
        # Skip to Step 1b
    fi
fi
```

If skip condition not met, run all four gates:

```bash
rai gate check --all
```

Commands come from `.raise/manifest.yaml`; null keys skip automatically. Works for any stack.

| Condition | Action |
|-----------|--------|
| Retro exists + gates green (or skipped) | Continue |
| Retro missing | Run `/rai-story-review` first — no exceptions |
| Any gate failing | Fix before push — CI will reject the same errors |

Check for structural drift: if this story added modules or changed directory structure, update module docs in `governance/architecture/modules/` before closing.

<verification>
Retrospective exists. All four gates pass (or skip logged with commit + elapsed). No undocumented structural changes.
</verification>

### Step 1b: Architecture Review Gate

> **Token marker** — Call `raise_session_topic(kind="close", topic="ar-review")` before executing this step.

Run the AR checklist before merging. This gate is mandatory — use the escape hatch only for XS/docs/tooling stories with no production code changes.

1. **P1 — Structural drift**: `rai drift check packages/<changed-module>/`
   Review output: orphaned symbols? dead public APIs?
2. **P2 — Beck-R2**: Does this story add necessary complexity only?
   No speculative abstractions, no unused parameters, no dead branches.
3. **P3 — Convention**: Naming, module placement, public API surface consistent with codebase?

After confirming all three, write the session-scoped marker and run the gate:

```bash
MARKER=".raise/rai/sessions/${RAISE_CC_SESSION_ID}/ar-reviewed"
mkdir -p "$(dirname "$MARKER")" && touch "$MARKER"
rai gate check gate-ar-story
rm -f "$MARKER"
```

Escape hatch (XS/docs/tooling — no production code changed):
```bash
RAISE_AR_SKIP_REASON="<reason>" rai gate check gate-ar-story
```

| Condition | Action |
|-----------|--------|
| Gate passes | Continue to Step 2 |
| Gate fails (no session) | Set `RAISE_CC_SESSION_ID` or use escape hatch |
| Gate fails (no marker) | Complete P1/P2/P3 checklist, then create marker |
| Escape hatch used | Reason logged in gate result — continues |

<verification>
AR gate passed. Reason logged if escape hatch was used.
</verification>

### Step 2: Verify Clean Working Tree

```bash
git status --short
```

| Condition | Action |
|-----------|--------|
| Working tree clean | Continue to merge |
| Uncommitted changes from this story | **Commit them** before merge — artifacts must not be orphaned |
| Unrelated changes | Stash or commit separately with `chore:` prefix |

**NEVER merge with uncommitted story artifacts.** Files created during design, plan, or implementation that aren't committed will be silently lost or orphaned on the target branch.

<verification>
`git status` shows clean working tree (or only unrelated files explicitly acknowledged).
</verification>

### Step 3: Merge Locally to Dev

> **Token marker** — Call `raise_session_topic(kind="close", topic="merge")` before executing this step.

First, detect whether an epic worktree branch exists for this story's epic. Story ID `s{N}.{M}` → epic `e{N}` → branch `worktree-e{N}*`:

```bash
# Detect epic worktree branch from story ID (e.g. s3044.3 → e3044 → worktree-e3044-*)
EPIC_N=$(echo "{story_id}" | grep -oP '(?<=s)\d+(?=\.)')
EPIC_BRANCH=$(git branch --list "worktree-e${EPIC_N}*" | tr -d ' ' | head -1)
MERGE_TARGET=${EPIC_BRANCH:-{dev_branch}}
echo "Merge target: $MERGE_TARGET"
```

Merge the story branch into `$MERGE_TARGET` locally with `--no-ff` to preserve story history:

```bash
git checkout $MERGE_TARGET && \
git branch --show-current | grep -qx "$MERGE_TARGET" && \
git merge story/s{N}.{M}/{slug} --no-ff -m "Merge branch 'story/s{N}.{M}/{slug}' into $MERGE_TARGET

S{N}.{M}: {story-name} — {1-line summary}

Tracker: {JIRA_KEY} / E{N}"
```

If running this merge from a non-CWD worktree, prefix the checkout and guarded merge with `cd /path/to/worktree &&`. The branch assertion must happen in the same command chain before merge or any later staging.

Remote push and merge requests are handled at epic level during `/rai-epic-close`.

| Condition | Action |
|-----------|--------|
| `worktree-e{N}*` branch found | Merge to epic branch — isolates epic work from `{dev_branch}` |
| No `worktree-e{N}*` branch | Fall back to `{dev_branch}` — existing standalone story behaviour |
| Merge succeeds | Continue to Step 4 |
| Merge conflicts | Resolve on story branch first, then retry merge |

<verification>
Story merged to `$MERGE_TARGET` (epic branch or `{dev_branch}`) locally via `--no-ff`.
</verification>

### Step 4: Update Epic Scope

Mark story complete in `work/epics/e{N}-{name}/scope.md`:
- Check the story checkbox: `- [x] S{N}.{M} {name} ✓`
- Update progress tracking table (status, actual time, velocity)

<verification>
Epic scope reflects story completion.
</verification>

### Step 5: Local Cleanup

> **Token marker** — Call `raise_session_topic(kind="close", topic="cleanup")` before executing this step.

Delete the local story branch (already merged to `{dev_branch}`):

```bash
git branch -d story/s{N}.{M}/{slug}
```

**Worktree branch restoration (mandatory if running inside an epic worktree):**

If the merge required a temporary `git checkout {dev_branch}` in the epic worktree, restore the worktree to its dedicated branch immediately after:

```bash
# Confirm current branch
git branch --show-current

# If on release/dev branch instead of worktree-{epic-slug}, restore:
git checkout worktree-{epic-slug}
```

Leaving an epic worktree on `release/3.0.0` blocks every other session from merging to that branch — they get "already used by worktree at .claude/worktrees/...". This restoration is non-optional.

| Condition | Action |
|-----------|--------|
| Worktree on `worktree-{epic-slug}` | ✓ Nothing to do |
| Worktree on `{dev_branch}` | Checkout `worktree-{epic-slug}` now |

<verification>
Local story branch deleted. Epic worktree on its dedicated branch (not on release/dev branch).
</verification>

### Step 6: Update Backlog

Query done statuses for this issue type:
```bash
rai backlog statuses list --issue-type Story
```

Infer close status:
- Look for `category=done` states whose name suggests completion
  (Done, DONE, Closed, Resolved, Complete, Finished…)
- Exclude cancellation states (Cancelled, Rejected, Abandoned, Void)
- Single clear candidate → use it silently
- Ambiguous → ask developer

Transition (non-blocking):
```bash
rai backlog transition {story_key} {done_slug}
```

| Condition | Action |
|-----------|--------|
| Clear done candidate | Transition silently |
| Ambiguous | Ask developer |
| No ticket | Skip |
| Transition fails | Log warning and continue |

<verification>
Backlog updated.
</verification>

<if-blocked>
Adapter not configured or transition fails → log and continue. Backlog sync is best-effort; it must never block story close.
</if-blocked>

## Output

| Item | Destination |
|------|-------------|
| Local merge | `{story_branch}` merged to `{dev_branch}` via `--no-ff` |
| Epic update | `work/epics/e{N}-{name}/scope.md` |
| Branch cleanup | Local story branch deleted |
| Backlog update | via `rai backlog transition` (best-effort) |
| Remote push + MR | Deferred to `/rai-epic-close` |

## Scope Constraints (CRITICAL)

Close is a **merge-only operation**. The following are explicitly forbidden:

- **NEVER edit source code, skill files, config, or governance docs** — close does not "fix" things
- **NEVER create "fix" or "refactor" commits** — if something looks wrong, report it; do not repair it
- **NEVER delete directories, worktrees, or files outside the story branch** — close only deletes the merged story branch
- **NEVER revert or modify commits already on `{dev_branch}`** — prior story work is settled
- **NEVER rationalize unauthorized changes** — "this field looks wrong" is not a close concern

**Conflict resolution:** When merge conflicts occur, resolve ONLY the conflicting hunks using the mechanical merge strategy (accept both sides where possible, prefer story branch for story-owned files). Do NOT use conflicts as an opportunity to audit or "correct" surrounding code.

**Allowed writes during close (exhaustive list):**
1. `work/epics/e{N}-{name}/scope.md` — update progress tracking only
2. Merge commit message
3. Signal/backlog CLI calls (side-effect only)

Anything not on this list is out of scope. If you believe something needs fixing, return it as a finding — do not act on it.

```bash
rai signal emit-work story "{story_id}" --event complete --phase close 2>/dev/null || true
```

## Quality Checklist

- [ ] NEVER merge without retrospective — learnings compound
- [ ] NEVER leave stale local branches — clean as you go
- [ ] NEVER edit source/skill/config files during close — merge only

## References

- Previous: `/rai-story-review`
- Complement: `/rai-story-start`
- Epic scope: `work/epics/e{N}-{name}/scope.md`
