---
allowed-tools:
- Read
- Edit
- Write
- Grep
- Glob
- Bash
description: Execute plan tasks with TDD and validation gates. Use after story plan.
license: MIT
metadata:
  raise.adaptable: 'true'
  raise.aspects: introspection
  raise.fase: '6'
  raise.frequency: per-story
  raise.gate: gate-code
  raise.inputs: '- plan_md: file_path, required, previous_skill

    '
  raise.introspection:
    affected_modules: []
    context_source: plan doc
    max_jit_queries: 3
    max_tier1_queries: 3
    phase: story.implement
    tier1_queries:
    - implementation patterns for {affected_modules}
    - testing patterns for {test_type} in {language}
    - integration patterns for {upstream_dependencies}
  raise.next: story-review
  raise.outputs: '- code_commits: list, git

    '
  raise.prerequisites: story-plan
  raise.version: 2.4.0
  raise.visibility: public
  raise.work_cycle: story
name: rai-story-implement
raise.mastery:
  ha: Adjust plan based on discoveries during implementation
  ri: Parallelize independent tasks, create stack-specific patterns
  shu: Execute tasks strictly in order, verify each before proceeding
---

# Implement: Development Workflow

## Purpose

Execute the implementation plan task by task with TDD, producing verified code that passes all gates.

## Mastery Levels (ShuHaRi)

See `raise.mastery` in frontmatter.

## Context

**When to use:** After `/rai-story-plan` has produced a plan document.

**Prerequisite:** Plan must exist at `work/epics/e{N}-{name}/stories/{story_id}/plan.md`. Run `/rai-story-plan` first if missing.

**Inputs:** Implementation plan, project guardrails (from graph context).

## Steps

### PRIME (mandatory — do not skip)

> **Token marker** — Call `raise_session_topic(kind="implement", topic="prime")` before executing this step.

Before starting Step 1, you MUST execute the PRIME protocol:

1. **Graph query**: Execute tier1 queries from this skill's metadata using the `raise_graph_query` MCP tool. If MCP unavailable, fall back to `rai graph query`. 0 results is valid.
2. **Code orientation**: Load SA-ranked code symbols for the current branch:
   ```bash
   rai session context -s code_context -p .
   ```
   Returns ~20 symbols ranked by structural proximity to active work modules. Empty result is valid — branch name may not match any module. Use these symbols as starting points for code exploration, not as exhaustive scope.
3. **Emit start**:
   ```bash
   rai signal emit-work story "{story_id}" --event start --phase implement 2>/dev/null || true
   ```

### Step 1: Load Plan & Context

> **Token marker** — Call `raise_session_topic(kind="implement", topic="load-plan")` before executing this step.

> **JIT**: Before loading context, query graph for implementation patterns in affected modules
> → `aspects/introspection.md § JIT Protocol`

Load the implementation plan and query relevant patterns using the `raise_graph_query` MCP tool with query "testing coverage type annotations" (limit 5).

If MCP tools are not available, fall back to:
```bash
rai graph query "testing coverage type annotations" --types pattern,guardrail --limit 5
```

If a design document exists, restate the design intent in 2-3 sentences and confirm with the human before proceeding. One unvalidated assumption can waste an entire task cycle.

> **JIT**: For deeper code exploration beyond the orientation map, query the graph directly:
> ```bash
> rai graph query "symbol_name" --types symbol --limit 10
> rai graph query "module_name" --module mod-session
> rai graph query "callers of function_name" --types symbol
> ```
> Use `--file path/to/file.py` to scope results to a specific file.

### Step 2: Execute Task

For the next uncompleted task in plan order:

1. **RED** — Call `raise_session_topic(kind="implement", topic="red")` first, then write a failing test that defines expected behavior
2. **GREEN** — Call `raise_session_topic(kind="implement", topic="green")` first, then write minimal code to make the test pass
3. **REFACTOR** — Call `raise_session_topic(kind="implement", topic="refactor")` first, then clean up while keeping tests green

Follow project rules, guardrails, and established patterns.

### Step 3: Verify Task (Fast Check)

> **Token marker** — Call `raise_session_topic(kind="implement", topic="verify")` before executing this step.

Run a **fast check** — tests scoped to files changed by this task, plus lint and type check. This catches regressions without running the full suite on every commit.

Run gates via the CLI — commands come from `.raise/manifest.yaml`, null keys skip automatically:

```bash
rai gate check gate-tests --scope {test_path}   # scoped fast check (preferred)
rai gate check gate-tests                        # full suite fallback if scope ambiguous
rai gate check gate-lint
rai gate check gate-format
rai gate check gate-types
```

**Scope tests to the task**: use `rai gate check gate-tests --scope <path>` (e.g. `rai gate check gate-tests --scope packages/raise-cli/tests/discovery/`). If the plan specifies the test path, use it. **NEVER run the test command directly** (e.g. `uv run pytest`) — gate check captures output and keeps context clean; direct invocation floods context with raw test output.

**Per-task gates:**
- Tests (scoped to changed module) ✓
- Lint (full project — fast) ✓
- Format check (full project — fast) ✓
- Type check (full project) ✓

If verification fails: fix and re-verify (max 3 attempts before escalating).

### Step 4: Commit & Checkpoint

> **Token marker** — Call `raise_session_topic(kind="implement", topic="commit")` before executing this step.

1. Assert the current branch matches the expected story branch before staging
2. Stage task files
3. **If this task modified `storage/schema.py`** — update `schema.sum` before committing:
   ```bash
   rai schema sum update && git add .raise/schema.sum
   ```
4. Commit the completed task
5. Update progress log (`work/epics/.../stories/{story_id}/progress.md`)
6. Present to the human: what was completed, files changed, verification results
7. Wait for acknowledgment before continuing

```bash
git branch --show-current | grep -qx "story/s{N}.{M}/{story-slug}" && \
git add {task_files} && \
git commit -m "{commit_message}"
```

When committing from a non-CWD worktree, prefix the same chain with `cd /path/to/worktree &&` so the branch assertion and `git add` execute in one shell command.

### Step 5: Iterate or Finalize

| Condition | Action |
|-----------|--------|
| More tasks remain | Return to Step 2 |
| All tasks complete | **Run package-scoped tests + full lint/format/types** (see below) |
| Task blocked | Document blocker, escalate to human |

**End-of-story gates** — scope tests to the changed package, keep lint/format/types full-project:

```bash
# Identify changed package (usually known from plan; verify with git diff if needed)
rai gate check gate-tests --scope packages/<changed_package>/
rai gate check gate-lint
rai gate check gate-format
rai gate check gate-types
```

If the story touches multiple packages, run `rai gate check gate-tests --scope packages/<pkg>/` once per changed package. Only fall back to unscoped `rai gate check gate-tests` when the changed package is genuinely ambiguous.

**Orphaned test check (Jidoka — mandatory, blocking)** — after gates pass, verify no test files that import from changed modules were left untouched. This is a **stop-the-line** gate: if orphaned tests exist, you MUST read each one and either update it or confirm it still passes. Do NOT proceed to emit implement-complete until resolved.

```bash
# List source modules changed in this story (vs epic/dev branch)
orphans=0
changed_modules=$(git diff --name-only HEAD...$(git merge-base HEAD {dev_branch}) -- 'packages/*/src/' | sed 's|.*/src/||; s|/[^/]*$||' | sort -u)
for mod in $changed_modules; do
  mod_dotted=$(echo "$mod" | tr '/' '.')
  grep -rl "from $mod_dotted" packages/*/tests/ 2>/dev/null | while read tf; do
    if ! git diff --name-only HEAD...$(git merge-base HEAD {dev_branch}) -- "$tf" | grep -q .; then
      echo "BLOCKED: $tf imports $mod_dotted but was not touched by this story"
      orphans=$((orphans + 1))
    fi
  done
done
```

| Result | Action |
|--------|--------|
| No orphans | Continue to emit implement-complete |
| Orphans found | **STOP.** Read each flagged test. Run it. If it fails, fix it. If it passes, document why no change was needed. Do NOT skip. |

Zero broken windows. RCA: RAISE-2564 and S2161.1 both left integration tests orphaned because this check did not exist.

After all gates pass, emit the implement-complete signal — commit is auto-resolved from git HEAD and stored in SQLite for story-close to read:

```bash
rai signal emit-work story "{story_id}" --event complete --phase implement 2>/dev/null || true
```

Gate runner reads commands from `.raise/manifest.yaml` for any stack. Configure with `rai init --detect` or set `project.{test,lint,format,type_check}_command` manually.

<verification>
All plan tasks committed. Package-scoped gates pass. Orphaned test check clean. implement-complete signal emitted for current HEAD.
</verification>

## Output

| Item | Destination |
|------|-------------|
| Implemented code | Per project architecture |
| Progress log | `work/epics/.../stories/{story_id}/progress.md` |
| Signal | WorkLifecycle event emitted (start on entry, complete here) |

```bash
rai signal emit-work story "{story_id}" --event complete --phase implement 2>/dev/null || true
```

**STOP HERE.** Return your summary to the orchestrator. Do NOT invoke any further skill.

## Quality Checklist

- [ ] NEVER commit without fast check — CI will catch what you skip
- [ ] NEVER skip a failing test — fix it or escalate
- [ ] NEVER accumulate errors — stop on defect (Jidoka)

## References

- Gate: `gates/gate-code.md`
- Progress template: `references/progress-template.md`
